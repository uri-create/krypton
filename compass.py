# compass.py
# 🧭 The Market Compass: today's "market weather" for the US stock market (S&P 500).
#
# It is NOT advice and NOT a promise. It combines six well-known, measurable market signals into
# one score from -100 (stormy) to +100 (calm uptrend), then looks up, on ~18 years of real history,
# what happened over the next month after readings like today's: how often the market rose, the
# typical range, and how often it fell 5% or 10% along the way.
#
# What 18 years of data showed (honestly):
#   - It does NOT reliably predict up vs down. Markets often bounce after stormy readings.
#   - It DOES predict how rough the next month will be: big drops were about 7x more common
#     after stormy readings than after calm ones, and daily swings were twice as large.
#
# The six signals (each scored from -1 to +1, using only data available on that day):
#   1. Trend        S&P 500 vs its 200-day average (above = healthy uptrend)
#   2. Momentum     S&P 500 change over the last 3 months
#   3. Breadth      how many of the 9 big sector funds are above their 50-day average
#                   (a rise led by many sectors is sturdier than one led by a few)
#   4. Fear         the VIX "fear index" vs its 3-month version: when short-term fear is higher than
#                   longer-term fear, investors are panicking
#   5. Credit       risky company bonds (HYG) vs safe government bonds (IEF): rising = investors brave
#   6. Growth       copper vs gold: copper is used to build things, gold is a safe haven;
#                   copper winning = the world economy looks stronger
#
# Pure calculation, no web-page code (see compass_tab.py for the page).

import numpy as np
import pandas as pd
import yfinance as yf

SECTOR_FUNDS = {"XLK": "Technology", "XLF": "Financials", "XLE": "Energy", "XLV": "Healthcare",
                "XLY": "Shopping & leisure", "XLP": "Everyday goods", "XLI": "Industry",
                "XLB": "Materials", "XLU": "Utilities"}
CODES = {"S&P 500": "^GSPC", "VIX": "^VIX", "VIX 3-month": "^VIX3M", "Risky bonds (HYG)": "HYG",
         "Safe bonds (IEF)": "IEF", "Copper": "HG=F", "Gold": "GC=F", **{code: code for code in SECTOR_FUNDS}}

HORIZON = 21          # trading days ahead we check (about one month)
LEAN = 25             # above +25 = "Calm uptrend", below -25 = "Stormy", in between = "Choppy"

SIGNALS = {
    "Trend": {"icon": "📈", "what": "Is the S&P 500 above its 200-day average price?",
              "up": "The market is above its long-term average: the big trend is up.",
              "down": "The market is below its long-term average: the big trend is down."},
    "Momentum": {"icon": "🚀", "what": "How much the S&P 500 moved over the last 3 months.",
                 "up": "Prices have been rising over the last 3 months.",
                 "down": "Prices have been falling over the last 3 months."},
    "Breadth": {"icon": "🌐", "what": "How many of the 9 big sector funds are above their 50-day average.",
                "up": "Most sectors are rising together: a broad, sturdy move.",
                "down": "Most sectors are below their recent average: weakness is widespread."},
    "Fear": {"icon": "😨", "what": "Short-term fear (VIX) compared with 3-month fear (VIX 3-month).",
             "up": "Investors are calm: short-term fear is lower than longer-term fear.",
             "down": "Investors are nervous: short-term fear is close to or above longer-term fear."},
    "Credit": {"icon": "💳", "what": "Risky company bonds vs safe government bonds, compared with 50 days ago.",
               "up": "Investors are happy to lend to risky companies: a sign of confidence.",
               "down": "Investors are moving to safe bonds: a sign of worry."},
    "Growth": {"icon": "🏗️", "what": "Copper (used to build things) vs gold (a safe haven).",
               "up": "Copper is beating gold: the world economy looks stronger.",
               "down": "Gold is beating copper: investors are worried about the economy."},
}


def download_history():
    """~18 years of daily closing prices for everything the Compass needs."""
    raw = yf.download(list(CODES.values()), start="2008-01-01", progress=False, auto_adjust=True)["Close"]
    raw = raw.rename(columns={code: name for name, code in CODES.items()})
    return raw.dropna(subset=["S&P 500"]).ffill()


def _clip(series, scale):
    return (series / scale).clip(-1, 1)


def signals(history):
    """Each signal for every day, from -1 (leaning down) to +1 (leaning up)."""
    sp = history["S&P 500"]
    out = pd.DataFrame(index=history.index)
    out["Trend"] = _clip(sp / sp.rolling(200).mean() - 1, 0.05)
    out["Momentum"] = _clip(sp / sp.shift(63) - 1, 0.08)
    above = pd.DataFrame({c: history[c] > history[c].rolling(50).mean() for c in SECTOR_FUNDS})
    out["Breadth"] = (above.mean(axis=1) - 0.5) * 2
    out["Fear"] = _clip(1 - history["VIX"] / history["VIX 3-month"], 0.10)
    credit = history["Risky bonds (HYG)"] / history["Safe bonds (IEF)"]
    out["Credit"] = _clip(credit / credit.shift(50) - 1, 0.02)
    growth = history["Copper"] / history["Gold"]
    out["Growth"] = _clip(growth / growth.shift(50) - 1, 0.06)
    out = out.iloc[200:].dropna()  # the first 200 days don't have a 200-day average yet
    out["Score"] = out[list(SIGNALS)].mean(axis=1) * 100
    return out


READINGS = {
    "Calm uptrend": {"icon": "☀️", "colour": "#3ddc84",
                     "meaning": "Most signals are positive: the market is rising steadily and investors are calm."},
    "Choppy": {"icon": "⛅", "colour": "#ffb000",
               "meaning": "Signals disagree: expect a bumpier ride than usual, without a clear direction."},
    "Stormy": {"icon": "⛈️", "colour": "#ff2a3d",
               "meaning": "Most signals are negative: the market is falling or nervous, and big swings are likely."},
}


def reading(score):
    if score >= LEAN:
        return "Calm uptrend"
    if score <= -LEAN:
        return "Stormy"
    return "Choppy"


def backtest(history, scores):
    """What happened over the next ~month after each reading: how often the S&P 500 rose, the typical
    range, how often it dipped 5% / 10% at some point, and how bumpy it was.
    Checked once a week (so the same month isn't counted 5 times), using only past data each day."""
    sp = history["S&P 500"]
    ahead = (sp.shift(-HORIZON) / sp - 1) * 100
    deepest = pd.concat([sp.shift(-k) / sp - 1 for k in range(1, HORIZON + 1)], axis=1).min(axis=1) * 100
    swings = sp.pct_change().rolling(HORIZON).std().shift(-HORIZON) * np.sqrt(252) * 100
    table = pd.DataFrame({"score": scores["Score"], "ahead": ahead.reindex(scores.index),
                          "deepest": deepest.reindex(scores.index), "swings": swings.reindex(scores.index)})
    table = table.dropna().iloc[::5]
    table["reading"] = table["score"].apply(reading)

    def stats(part):
        return {"weeks": len(part), "up": (part["ahead"] > 0).mean() * 100, "avg": part["ahead"].mean(),
                "low": part["ahead"].quantile(0.1), "high": part["ahead"].quantile(0.9),
                "dip5": (part["deepest"] < -5).mean() * 100, "dip10": (part["deepest"] < -10).mean() * 100,
                "swings": part["swings"].mean()}

    return {"start": table.index[0], "end": table.index[-1], "all": stats(table),
            "by_reading": {name: stats(table[table["reading"] == name]) for name in READINGS
                           if (table["reading"] == name).any()}}


def expected_range(history):
    """The move the options market itself expects over the next month (about 2 in 3 chance of staying
    inside it): VIX is the expected yearly swing in %, so one month is VIX / sqrt(12)."""
    vix = history["VIX"].dropna().iloc[-1]
    return vix, vix / np.sqrt(12)


def build():
    """Everything the Compass page needs, in one go (downloaded and calculated once, then reused)."""
    history = download_history()
    scores = signals(history)
    vix, month_move = expected_range(history)
    sectors = {}
    for code, name in SECTOR_FUNDS.items():
        series = history[code].dropna()
        sectors[name] = {"month": (series.iloc[-1] / series.iloc[-22] - 1) * 100,
                         "above_avg": bool(series.iloc[-1] > series.iloc[-50:].mean())}
    sp = history["S&P 500"]
    return {"today": scores.iloc[-1].to_dict(), "date": scores.index[-1], "scores": scores,
            "sp500": sp, "test": backtest(history, scores), "vix": vix, "month_move": month_move,
            "sp_level": sp.iloc[-1], "sectors": sectors,
            "score_week_ago": scores["Score"].iloc[-6] if len(scores) > 6 else None}


def summary_line(compass):
    """One plain-English sentence about today's market weather (for the daily briefing and the AI analyst)."""
    if not compass:
        return None
    name = reading(compass["today"]["Score"])
    odds, normal = compass["test"]["by_reading"][name], compass["test"]["all"]
    return (f"Market weather (S&P 500): {READINGS[name]['icon']} {name} (score {compass['today']['Score']:+.0f} of ±100). "
            f"After readings like this, the market was higher a month later {odds['up']:.0f}% of the time "
            f"(normal {normal['up']:.0f}%), and fell 10%+ during the month {odds['dip10']:.0f}% of the time "
            f"(normal {normal['dip10']:.0f}%). Good at warning about rough months, not at calling up or down.")
