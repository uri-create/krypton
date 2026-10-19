# analyst.py
# "🤖 Ask the analyst": chat with an AI that can see everything Krypton sees right now
# (events, severities, affected markets, your portfolio, the track record) and can also
# search the web for the latest news. Needs an Anthropic API key.

import datetime as dt

from deep_research import MODEL, api_key_available, load_api_key  # noqa: F401  (re-exported for the app)
from portfolio import exposure, holding_prices, load_portfolio
from severity import rank

SYSTEM = """You are Krypton's analyst: an expert in geopolitics, shipping, weather and markets,
talking to a smart 14-year-old investor. You can see Krypton's live dashboard data (below) and you
can search the web for the latest news.

Rules:
- Be specific: name places, dates, numbers, companies and tickers.
- Use the live data below first; search the web for anything newer or deeper, and cite sources.
- Be honest about uncertainty. Krypton's own track record shows its general event→stock rules have
  NOT beaten chance over 30 days, so never present a market effect as a sure thing.
- Explain clearly with headings and bullet points. Keep answers focused.
- This is education, not financial advice: never tell the user to buy or sell.

LIVE KRYPTON DATA ({time}):
{data}"""


def live_summary(state, store, backtest_overall=None, limit=30):
    """A compact text version of the dashboard for the AI to read."""
    lines = []
    events = sorted(state["events"], key=lambda e: -rank(e["severity"]))[:limit]
    for e in events:
        markets = "; ".join(f"{d}{m}" for m, d, _ in e["impacts"][:5])
        lines.append(f"- [{e['severity']}] {e['category']}: {e['name']} | {e['tooltip']} | markets: {markets}")
    holdings = load_portfolio(store)
    if holdings:
        lines.append("\nUSER'S PORTFOLIO EXPOSURE (Named = in Krypton research; Measured = real price correlation "
                     "with a market the event hits, after removing general stock-market moves):")
        try:
            held = holding_prices(holdings)
        except Exception:
            held = None
        for ticker, links in exposure(holdings, state["events"], state["prices"], held).items():
            parts = []
            for l in links[:6]:
                if l["link"] == "Measured":
                    parts.append(f"Measured: moves with {l['driver']} (corr {l['corr']:+.2f}) -> {l['event']} "
                                 f"({l['severity']})")
                else:
                    parts.append(f"Named {l['direction']} {l['event']} ({l['severity']})")
            lines.append(f"- {ticker}: " + ("; ".join(parts) or "no named or measured exposure"))
    if backtest_overall:
        lines.append(f"\nTRACK RECORD: {backtest_overall['hit_rate']:.0%} hit rate vs {backtest_overall['base_rate']:.0%} "
                     f"base rate over {backtest_overall['predictions']} past predictions (no proven edge).")
    return "\n".join(lines)


def ask(question, history, state, store, backtest_overall=None):
    """Send the conversation to Claude (with web search). Returns (answer_text, sources)."""
    import anthropic

    load_api_key()  # pick up the key saved by set_api_key.sh
    client = anthropic.Anthropic()
    system = SYSTEM.format(time=dt.datetime.now().strftime("%d %b %Y %H:%M"),
                           data=live_summary(state, store, backtest_overall))
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": question})
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]

    for _ in range(5):  # continue if a long web-search turn pauses
        response = client.beta.messages.create(
            model=MODEL, max_tokens=8000, system=system, messages=messages, tools=tools,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "refusal":
        return "Sorry, I can't help with that one. Try asking it a different way.", []
    text, sources = [], {}
    for block in response.content:
        if block.type == "text":
            text.append(block.text)
            for citation in getattr(block, "citations", None) or []:
                if getattr(citation, "url", None):
                    sources[citation.url] = getattr(citation, "title", None) or citation.url
    return "".join(text).strip(), [{"url": u, "title": t} for u, t in sources.items()]
