# portfolio.py
# "My portfolio": enter what you own, and Krypton shows which live events affect it, and WHY.
#
# Everything shown is either MEASURED from real data or clearly labelled as a research note:
#
#   ✅ MEASURED (real data, nothing estimated)
#      - the holding's actual price move since the event began
#      - how the holding actually moved after past events of the same kind (from the backtest)
#      - how closely the holding has actually moved with the markets the event hits
#        (correlation of daily price moves over the last 12 months)
#   📚 RESEARCH NOTE
#      - a factual background line explaining the connection (e.g. "iPhone chips are made by TSMC")
#
# Two kinds of link:
#   🎯 NAMED     the holding itself appears in the event's researched effects
#   📈 MEASURED  the holding isn't named, but its price has actually moved closely together
#                (correlation ≥ 0.4, after removing general stock-market moves) with a market the event hits
# Each user's portfolio is saved in their own private storage (see storage.py).

import json
import os

import pandas as pd
import yfinance as yf

from markets import ALL_MARKETS, SECTOR_OF
from severity import rank

CODE_TO_NAME = {code.upper(): name for name, code in ALL_MARKETS.items()}
MIN_CORRELATION = 0.4   # how closely prices must have moved together (after removing general
                        # stock-market moves) to count as a measured link
MIN_OVERLAP_DAYS = 120  # need at least this many shared trading days to measure a correlation


def load_portfolio(store):
    """One user's portfolio, from their private storage."""
    return store.read("portfolio", [])


def save_portfolio(store, holdings):
    store.write("portfolio", holdings)


def lookup_holding(ticker):
    """Find a ticker's real name (and sector, if it's one of Krypton's tracked markets)."""
    ticker = ticker.strip().upper()
    if ticker in CODE_TO_NAME:
        name = CODE_TO_NAME[ticker]
        return {"ticker": ticker, "name": name, "sector": SECTOR_OF[name], "known": True}
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}
    name = info.get("shortName") or info.get("longName")
    if not name:
        return None  # not a real ticker
    return {"ticker": ticker, "name": name, "sector": info.get("sector") or info.get("quoteType", "Other"),
            "known": False}


def holding_prices(holdings, period="1y"):
    """Real daily closing prices for every holding (one column per ticker)."""
    tickers = [h["ticker"] for h in holdings]
    if not tickers:
        return pd.DataFrame()
    raw = yf.download(tickers, period=period, progress=False, auto_adjust=True)["Close"]
    if isinstance(raw, pd.Series):  # only one ticker
        raw = raw.to_frame(tickers[0])
    return raw


# ---------------------------------------------------------------------------
# Measurements (all from real prices)
# ---------------------------------------------------------------------------
def move_since(series, since):
    """Real % change from the first trading day on/after `since` to the latest price.
    Returns (percent, actual start date used) or (None, None)."""
    series = series.dropna()
    if series.empty:
        return None, None
    if since is None:
        start = series.index[-1] - pd.Timedelta(days=30)
    else:
        start = pd.Timestamp(since)
    after = series[series.index >= start]
    if after.empty or len(after) < 2:
        return None, None
    return (series.iloc[-1] / after.iloc[0] - 1) * 100, after.index[0].date()


def correlation(a, b, market=None):
    """Correlation of DAILY % moves over the last 12 months (1 = always move together,
    -1 = always opposite, 0 = unrelated).

    Most stocks rise and fall with the overall market, which would make almost everything look
    'linked'. So if `market` (the S&P 500) is given, we first REMOVE each series' normal reaction
    to the overall market, and correlate what's left. Returns (value, days used) or (None, days)."""
    parts = [a.pct_change(), b.pct_change()] + ([market.pct_change()] if market is not None else [])
    joined = pd.concat(parts, axis=1, join="inner").dropna().iloc[-252:]
    if len(joined) < MIN_OVERLAP_DAYS:
        return None, len(joined)
    x, y = joined.iloc[:, 0], joined.iloc[:, 1]
    if market is not None:
        m = joined.iloc[:, 2]
        x = x - (x.cov(m) / m.var()) * m   # x without its normal market-driven moves
        y = y - (y.cov(m) / m.var()) * m
    return float(x.corr(y)), len(joined)


def past_reactions(backtest, market, rule):
    """How this market really moved after past events of the same kind (from the backtest)."""
    if not backtest or not rule:
        return None
    rows = [p for p in backtest["predictions"] if p["market"] == market and p["rule"] == rule]
    if not rows:
        return None
    moves = [p["move"] for p in rows]
    return {"cases": len(rows), "hits": sum(p["hit"] for p in rows), "expected": rows[0]["expected"],
            "average": sum(moves) / len(moves), "best": max(moves), "worst": min(moves),
            "days": backtest["hold_days"]}


# ---------------------------------------------------------------------------
# Exposure
# ---------------------------------------------------------------------------
def exposure(holdings, events, market_prices=None, held_prices=None, backtest=None, min_severity="Moderate"):
    """For each holding: the live events that affect it, with measured facts and research notes.
    Returns {ticker: [link, ...]}, most serious first. Without price data it still finds NAMED links
    (used by alerts and the briefing)."""
    result = {}
    for h in holdings:
        links = []
        own = held_prices[h["ticker"]] if held_prices is not None and h["ticker"] in held_prices else None
        for e in events:
            if rank(e["severity"]) < rank(min_severity):
                continue
            named = next((x for x in e["impacts"] if x[0] == h.get("name")), None)
            if named:
                market, direction, why = named
                link = {"event": e["name"], "category": e["category"], "severity": e["severity"], "id": e["id"],
                        "link": "Named", "direction": direction, "note": why, "facts": [], "since": e.get("since")}
                if own is not None:
                    move, start = move_since(own, e.get("since"))
                    if move is not None:
                        label = f"since the event began ({start:%d %b %Y})" if e.get("since") else \
                            f"over the last 30 days (since {start:%d %b %Y})"
                        link["facts"].append(f"{h['ticker']} has moved **{move:+.1f}%** {label}.")
                history = past_reactions(backtest, h.get("name"), e.get("rule"))
                if history:
                    link["facts"].append(
                        f"After **{history['cases']}** past events of this kind, it moved the expected way "
                        f"(**{history['expected']}**) **{history['hits']}** times; average move "
                        f"**{history['average']:+.1f}%** over {history['days']} days "
                        f"(range {history['worst']:+.1f}% to {history['best']:+.1f}%).")
                elif e.get("rule"):
                    link["facts"].append("No past events of exactly this kind in the track record to compare.")
                links.append(link)
                continue

            # MEASURED link: the holding's price has really moved together with a market this event hits,
            # even after removing normal stock-market swings
            if own is None or market_prices is None:
                continue
            sp500 = market_prices["S&P 500"] if "S&P 500" in market_prices else None
            best = None
            for market, direction, why in e["impacts"]:
                if direction == "◆" or market not in market_prices or market in (h.get("name"), "S&P 500"):
                    continue
                corr, days = correlation(own, market_prices[market], sp500)
                if corr is not None and abs(corr) >= MIN_CORRELATION and (best is None or abs(corr) > abs(best[0])):
                    best = (corr, days, market, direction, why)
            if best:
                corr, days, market, direction, why = best
                implied = direction if corr > 0 else ("▼" if direction == "▲" else "▲")
                driver_move, start = move_since(market_prices[market], e.get("since"))
                own_move, _ = move_since(own, e.get("since"))
                links.append({"event": e["name"], "category": e["category"], "severity": e["severity"],
                              "id": e["id"], "link": "Measured", "direction": implied, "since": e.get("since"),
                              "driver": market, "corr": corr, "days": days, "driver_direction": direction,
                              "note": why, "driver_move": driver_move, "own_move": own_move,
                              "move_start": start, "facts": []})

        links.sort(key=lambda x: (x["link"] != "Named", -rank(x["severity"])))
        result[h["ticker"]] = links
    return result
