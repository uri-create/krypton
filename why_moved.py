# why_moved.py
# "🧠 Why did it move?" for each stock in your portfolio.
#
# The price move itself is MEASURED from real prices. The REASON comes from the AI searching the
# web for that stock's actual news from the last week, written in plain English with sources.
# If there was no real news, it must say so (e.g. "it just moved with the whole market"),
# never make a reason up. Answers are saved for the day in each user's private storage, so each
# stock costs about 3–6 US cents once per day per user.

import datetime as dt

from deep_research import MODEL, load_api_key


INSTRUCTIONS = """You explain stock moves to a 12-year-old. Use web search to find the REAL reason.

Rules:
- Only state facts you found in news from the last 10 days. Give the date of the news.
- Write 2 or 3 short, simple sentences. No jargon. If you must use a word like "earnings",
  explain it in a few words (e.g. "earnings (how much money the company made)").
- Start with the move, e.g. "TSMC fell 2% this week because ..."
- If there's no clear company news, say so honestly, e.g. "There was no big news about TSMC.
  It mostly moved with the whole stock market, which also fell this week."
- Never guess or invent a reason. Never say what will happen next. Never give buy/sell advice.
- End with the sources as markdown links on one line, like: Sources: [Reuters](url), [CNBC](url)"""


def _name(ticker):
    return f"why:{ticker}:{dt.date.today():%Y-%m-%d}"


def load_today(store, ticker):
    """Today's saved explanation for this ticker (for this user), or None."""
    return store.read(_name(ticker))


def week_move(series):
    """Real % change over the last 5 trading days (one week)."""
    series = series.dropna()
    if len(series) < 6:
        return None
    return (series.iloc[-1] / series.iloc[-6] - 1) * 100


def explain(store, ticker, name, move, market_move):
    """Ask the AI (with web search) why this stock moved. Saves and returns {"text", "move", "time"}."""
    import anthropic
    from billing import cost_of

    load_api_key()
    client = anthropic.Anthropic()
    cost = 0.0
    question = (f"Today is {dt.date.today():%d %B %Y}. {name} (ticker {ticker}) moved {move:+.1f}% over the last "
                f"5 trading days. For comparison, the whole US stock market (S&P 500) moved {market_move:+.1f}%. "
                "Why did it move?")
    messages = [{"role": "user", "content": question}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 4}]
    for _ in range(4):  # continue if a web-search turn pauses
        response = client.beta.messages.create(
            model=MODEL, max_tokens=4000, system=INSTRUCTIONS, messages=messages, tools=tools,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        cost += cost_of(response)
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if response.stop_reason == "refusal" or not text:
        text = "Couldn't find an explanation right now. Try again later."
    result = {"text": text, "move": move, "time": dt.datetime.now().strftime("%H:%M"), "cost": round(cost, 4)}
    store.write(_name(ticker), result)
    return result
