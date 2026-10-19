# deep_research.py
# The "Deep research" button: Claude searches the web about ONE specific event and writes
# a sourced analysis: the real, specific causes, what led to it, and which companies it affects.
#
# Needs an Anthropic API key (see the CyprusAI SETUP.md for how a parent can create one).
# Each analysis costs roughly 5–15 US cents. Results are saved in data/research/, so the same
# event is never paid for twice (you can refresh it if you want a newer version).

import datetime as dt
import hashlib
import json
import os

RESEARCH_FOLDER = os.path.join(os.path.dirname(__file__), "data", "research")
MODEL = "claude-opus-5-5"

INSTRUCTIONS = """You are a senior geopolitical and markets analyst writing for a smart 14-year-old investor.
Research the event below using web search. Be SPECIFIC and FACTUAL: name places, dates, numbers,
organisations and companies. Never write generic textbook explanations (e.g. don't explain what a
typhoon is). Explain the actual causes of THIS event.

If sources disagree or something is uncertain, say so. Do not invent facts. Cite sources.

Write in clear, simple English using exactly these markdown sections:

## Bottom line
2–3 sentences: what is happening and why it matters.

## What specifically caused it
Bullet points with the concrete causes and the chain of events that led here (with dates).

## Background
The longer story behind it, in a few short paragraphs.

## Latest developments
Bullet points, newest first, with dates.

## Who and what it affects
Group by sector. For each, name specific companies (with stock tickers) or commodities, say whether
they tend to gain or lose, and WHY, in one line each.

## What to watch next
3–5 bullet points: signals that would show it getting better or worse.

This is for education, not financial advice. Do not tell the reader to buy or sell anything."""


def load_api_key():
    """Make sure ANTHROPIC_API_KEY is available to this program.
    set_api_key.sh saves it in your Windows user settings; programs that were already running
    (or were started from an old terminal) don't see it yet, so read it from there directly."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    try:  # online version: the key lives in Streamlit's secrets
        from storage import get_secret
        secret = get_secret("ANTHROPIC_API_KEY")
        if secret:
            os.environ["ANTHROPIC_API_KEY"] = secret
            return True
    except Exception:
        pass
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as settings:
            key, _ = winreg.QueryValueEx(settings, "ANTHROPIC_API_KEY")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key  # the Anthropic library reads it from here
            return True
    except (ImportError, OSError):
        pass
    return False


def api_key_available():
    return load_api_key()


def _cache_path(event_key):
    digest = hashlib.sha1(event_key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(RESEARCH_FOLDER, f"{digest}.json")


def load_saved(event_key):
    """A previously saved analysis for this event, or None."""
    path = _cache_path(event_key)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    return None


def run_research(event_key, event_description):
    """Ask Claude (with web search) to research the event. Returns {"text", "sources", "date"}."""
    import anthropic
    from billing import cost_of

    load_api_key()  # pick up the key saved by set_api_key.sh
    client = anthropic.Anthropic()
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]
    cost = 0.0
    messages = [{"role": "user", "content": f"Today is {dt.date.today():%d %B %Y}.\n\nEVENT:\n{event_description}"}]

    # Web searches run on Anthropic's servers. If a long search turn pauses ("pause_turn"),
    # we send the conversation back so it can continue (up to 5 times).
    for _ in range(5):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=INSTRUCTIONS,
            messages=messages,
            tools=tools,
            output_config={"effort": "high"},
            # If the main model declines, the API retries on a backup model automatically.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        cost += cost_of(response)
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "refusal":
        raise RuntimeError("The AI declined to research this topic.")

    text_parts, sources = [], {}
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
            for citation in getattr(block, "citations", None) or []:
                url = getattr(citation, "url", None)
                if url:
                    sources[url] = getattr(citation, "title", None) or url

    result = {"text": "".join(text_parts).strip(), "sources": [{"url": u, "title": t} for u, t in sources.items()],
              "date": dt.datetime.now().strftime("%d %b %Y, %H:%M"), "cost": round(cost, 4)}
    os.makedirs(RESEARCH_FOLDER, exist_ok=True)
    with open(_cache_path(event_key), "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return result
