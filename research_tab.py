# research_tab.py
# The Universal search page: type any stock (e.g. NVDA) and see, in plain language:
#   market cap, float shares, total shares, what the company does, and a simple price chart.
# The data work lives in research.py; this file only draws the page.

import html
import re

import streamlit as st

from billing import add_cost, ai_access
from deep_research import api_key_available
from panels import how_to_read, line_chart, stat_cards, subtitle
from research import PERIODS, company_info, plain_summary, price_history, saved_plain_summary, short_description
from universe import money


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _info(ticker):
    return company_info(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def _history(ticker, period):
    return price_history(ticker, period)


def _shares(value):
    """2,140,709,794 -> '2.14 billion'."""
    if not value:
        return "n/a"
    for size, word in ((1e9, "billion"), (1e6, "million"), (1e3, "thousand")):
        if value >= size:
            return f"{value / size:,.2f} {word}"
    return f"{value:,.0f}"


def _ticker_from(choice):
    """'NVIDIA Corporation (NVDA)' -> 'NVDA'; a typed ticker like 'nvda' -> 'NVDA'."""
    found = re.search(r"\(([A-Za-z0-9.\-]{1,10})\)\s*$", choice or "")
    return (found.group(1) if found else (choice or "")).strip().upper()


def _what_it_does(user, company):
    subtitle("What the company does")
    saved = saved_plain_summary(company["ticker"])
    if saved:
        st.markdown(f"<div class='lead'>{html.escape(saved)}</div>", unsafe_allow_html=True)
        return
    if ai_access(user)[0] and api_key_available() and company["summary"]:
        with st.spinner("Writing a plain-English explanation..."):
            try:
                text, cost = plain_summary(company["ticker"], company["name"], company["summary"])
                add_cost(user, cost)
            except Exception:
                text = None
        if text:
            st.markdown(f"<div class='lead'>{html.escape(text)}</div>", unsafe_allow_html=True)
            return
    official = short_description(company["summary"])
    st.markdown(f"<div class='lead'>{html.escape(official) or 'No description available.'}</div>",
                unsafe_allow_html=True)
    if not ai_access(user)[0]:
        st.caption("This is the company's official description. A plain-English version is part of Krypton Pro.")


def research_tab(state, user):
    st.markdown("### Universal search")
    st.markdown("<div class='lead'>Search any stock to see how big it is, how many shares it has, what it does in "
                "plain words, and its price history.</div>", unsafe_allow_html=True)
    universe = state.get("universe")
    options = [f"{r.name} ({r.ticker})" for r in universe.itertuples()] if universe is not None else []
    choice = st.selectbox("Search", options, index=None, accept_new_options=True, label_visibility="collapsed",
                          placeholder="Type a company name or ticker, e.g. NVDA, Apple, Coca-Cola")
    if not choice:
        st.caption(f"{len(options):,} US-listed companies to search, or type any other ticker.")
        return
    ticker = _ticker_from(choice)
    with st.spinner(f"Looking up {ticker}..."):
        try:
            company = _info(ticker)
        except Exception:
            company = None
    if not company and universe is not None and ticker in set(universe["ticker"]):
        # Yahoo Finance didn't answer: fall back to the basics from the company list
        row = universe[universe["ticker"] == ticker].iloc[0]
        company = {"ticker": ticker, "name": row["name"], "sector": row["sector"], "industry": row["industry"],
                   "country": row["country"], "market_cap": row["market_cap"], "float_shares": None,
                   "total_shares": None, "price": row["price"], "change_pct": row["change_pct"], "currency": "USD",
                   "summary": ""}
    if not company:
        st.warning(f"Couldn't find a stock with the ticker **{html.escape(ticker)}**. Check the spelling, or try "
                   "the company's name.")
        return

    details = " · ".join(x for x in (company["sector"], company["industry"], company["country"]) if x)
    price = f"{company['price']:,.2f} {company['currency']}" if company["price"] else ""
    change = company["change_pct"]
    move = (f" <span class='stat-delta {'good' if change >= 0 else 'bad'}'>{change:+.2f}% today</span>"
            if change is not None else "")
    st.markdown(f"<div class='research-head'><div class='research-name'>{html.escape(company['name'])} "
                f"<span class='research-ticker'>{html.escape(company['ticker'])}</span></div>"
                f"<div class='muted'>{html.escape(details)}</div>"
                f"<div class='research-price'>{price}{move}</div></div>", unsafe_allow_html=True)

    subtitle("Size and shares")
    float_share = (company["float_shares"] / company["total_shares"] * 100
                   if company["float_shares"] and company["total_shares"] else None)
    float_note = ""
    if float_share is not None and float_share < 2:  # almost certainly a data error at the source
        company["float_shares"], float_share = None, None
        float_note = " Yahoo Finance's figure for this company looks wrong, so it's hidden."
    stat_cards([
        {"label": "Market cap", "value": money(company["market_cap"]),
         "explain": "What the whole company is worth on the stock market: share price × total shares."},
        {"label": "Float shares", "value": _shares(company["float_shares"]),
         "explain": "Shares anyone can buy and sell"
                    + (f" ({float_share:.0f}% of all shares)." if float_share else ".")
                    + " The rest are held by insiders, founders or big long-term owners." + float_note},
        {"label": "Total shares", "value": _shares(company["total_shares"]),
         "explain": "All the shares the company has issued, including ones that rarely trade."},
    ], per_row=3)

    _what_it_does(user, company)

    subtitle("Price history")
    period = st.segmented_control("Period", list(PERIODS), default="1 year", label_visibility="collapsed",
                                  key="research_period") or "1 year"
    try:
        series = _history(ticker, period)
    except Exception:
        series = None
    if series is None or series.empty:
        st.caption("No price history available for this stock right now.")
    else:
        change_period = (series.iloc[-1] / series.iloc[0] - 1) * 100
        span = "since it started trading" if period == "All time" else f"over the last {period.lower()}"
        line_chart(series, f"{company['name']}: share price, {period.lower()}", f"Price ({company['currency']})",
                   colour="#ff4d5e", height=360,
                   explain=f"The share price {span}: {'up' if change_period >= 0 else 'down'} "
                           f"{abs(change_period):,.1f}% in that time.")
    how_to_read("Facts and prices: Yahoo Finance. For learning only, not financial advice.")
