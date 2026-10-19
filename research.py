# research.py
# Universal search: the facts about any stock, by ticker.
#   - company_info:  name, sector, market cap, float shares, total shares, official description (Yahoo Finance)
#   - price_history: daily (or weekly, for long periods) closing prices for a chosen period
#   - short_description: the first two sentences of the official description, minus the legal wording
#   - plain_summary: an AI rewrite of the description in plain, simple words (Krypton Pro). It's saved for
#     everyone (shared storage, not anyone's private data), so each company is only paid for once.
# Pure calculation, no web-page code (see research_tab.py for the page).

import datetime as dt
import re

import pandas as pd
import yfinance as yf

from deep_research import MODEL, load_api_key
from storage import UserStore

SHARED = UserStore(0)            # storage that belongs to no user: plain-English descriptions for everyone
REFRESH_DAYS = 180               # rewrite a company's description at most twice a year
PERIODS = {"1 month": ("1mo", "1d"), "6 months": ("6mo", "1d"), "1 year": ("1y", "1d"),
           "5 years": ("5y", "1wk"), "All time": ("max", "1mo")}

PLAIN_INSTRUCTIONS = """You explain what a company does to someone who knows nothing about business.

Rules:
- 2 or 3 short sentences. Simple everyday words. No jargon, no buzzwords, no marketing language.
- Say what it actually makes or does, who pays it, and how it makes most of its money.
- If you must use a business word, explain it in a few words.
- Only use facts from the description given. Don't add numbers, opinions, predictions or advice.
- No headings, no bullet points, no emojis. Start directly with the company name."""


def yahoo_symbol(ticker):
    """Yahoo Finance writes share classes with a dash: BRK.B -> BRK-B."""
    return ticker.strip().upper().replace(".", "-").replace("/", "-")


def company_info(ticker):
    """The key facts about one company (or None if Yahoo doesn't know the ticker)."""
    info = yf.Ticker(yahoo_symbol(ticker)).info or {}
    name = info.get("longName") or info.get("shortName")
    if not name:
        return None
    return {"ticker": ticker.strip().upper(), "name": name, "sector": info.get("sector"),
            "industry": info.get("industry"), "country": info.get("country"),
            "employees": info.get("fullTimeEmployees"), "website": info.get("website"),
            "market_cap": info.get("marketCap"), "float_shares": info.get("floatShares"),
            "total_shares": info.get("sharesOutstanding") or info.get("impliedSharesOutstanding"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "change_pct": info.get("regularMarketChangePercent"), "currency": info.get("currency") or "USD",
            "summary": info.get("longBusinessSummary") or ""}


def price_history(ticker, period="1 year"):
    yahoo_period, interval = PERIODS[period]
    data = yf.download(yahoo_symbol(ticker), period=yahoo_period, interval=interval, progress=False,
                       auto_adjust=True)
    if data is None or data.empty:
        return pd.Series(dtype=float)
    close = data["Close"]
    return close.squeeze("columns") if isinstance(close, pd.DataFrame) else close


def short_description(summary, sentences=2):
    """The first sentences of the official description, without legal filler like 'together with its subsidiaries'."""
    text = re.sub(r",? together with its subsidiaries,?", "", summary)
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[a-z0-9\)])\.\s+(?=[A-Z])", text)
    short = ". ".join(parts[:sentences]).strip()
    return short + ("" if short.endswith(".") else ".") if short else ""


def saved_plain_summary(ticker):
    saved = SHARED.read(f"about:{ticker.upper()}")
    if saved and dt.date.fromisoformat(saved["date"]) >= dt.date.today() - dt.timedelta(days=REFRESH_DAYS):
        return saved["text"]
    return None


def plain_summary(ticker, name, official):
    """Ask the AI to rewrite the official description in plain words, save it for everyone.
    Returns (text, cost in US dollars)."""
    import anthropic
    from billing import cost_of

    load_api_key()
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL, max_tokens=1500, system=PLAIN_INSTRUCTIONS,
        messages=[{"role": "user", "content": f"Company: {name} ({ticker})\n\nOfficial description:\n{official}"}],
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    cost = cost_of(response)
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if response.stop_reason == "refusal" or not text:
        return None, cost
    SHARED.write(f"about:{ticker.upper()}", {"text": text, "date": dt.date.today().isoformat()})
    return text, cost
