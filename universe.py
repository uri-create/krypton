# universe.py
# The STOCK UNIVERSE: every company listed in the US (thousands), with its sector, industry,
# market capitalisation (company size), price and today's move.
#
# One download from Nasdaq's public stock screener (the same list nasdaq.com uses). Sectors follow the
# professional GICS standard: for the ~1,500 companies in the S&P 500, 400 and 600 we take their official
# GICS sector and sub-industry from Wikipedia's index lists; the rest get the closest match from Nasdaq's
# own sector. Then cleaned:
#   - only ordinary company shares (no warrants, units, rights, preferred shares or notes)
#   - one row per company (Alphabet's two share classes count once)
#   - tidy names ("Apple Inc. Common Stock" -> "Apple Inc.")
#   - sorted from biggest to smallest company in every sector
# Pure calculation, no web-page code (see markets_tab.py for the page).

import io
import re

import pandas as pd
import requests

URL = "https://api.nasdaq.com/api/screener/stocks"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/130 Safari/537.36",
           "Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com",
           "Referer": "https://www.nasdaq.com/"}

# Nasdaq's sector names -> the closest GICS sector (used for companies outside the S&P indexes)
SECTOR_NAMES = {"Technology": "Information Technology", "Finance": "Financials", "Health Care": "Health Care",
                "Consumer Discretionary": "Consumer Discretionary", "Consumer Staples": "Consumer Staples",
                "Industrials": "Industrials", "Energy": "Energy", "Basic Materials": "Materials",
                "Utilities": "Utilities", "Real Estate": "Real Estate",
                "Telecommunications": "Communication Services"}
GICS_PAGES = ["List_of_S%26P_500_companies", "List_of_S%26P_400_companies", "List_of_S%26P_600_companies"]

NOT_COMMON = re.compile(r"warrant|\bunits?\b|\brights?\b|preferred|\bnotes?\b|debenture|subordinated|zones|"
                        r"\bdepositary shares? each representing a \d", re.I)
NAME_TAIL = re.compile(r"\s*(,\s*)?(\(The\)\s*)?(Class [A-Z]\b.*|Series [A-Z]\b.*|Common Stock|Common Shares|"
                       r"Ordinary Shares|Capital Stock|American Depositary Shares|American Depository Shares|ADS|"
                       r"Sponsored ADR|Subordinate Voting Shares|Registered Shares|Shares of Beneficial Interest)"
                       r"\b.*$", re.I)


def _number(text):
    try:
        return float(str(text).replace("$", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def clean_name(name):
    name = NAME_TAIL.sub("", str(name).strip())
    return re.sub(r"\s+", " ", name).strip(" ,") or str(name).strip()


def gics_sectors():
    """{ticker: (GICS sector, GICS sub-industry)} for every S&P 500 / 400 / 600 company (from Wikipedia)."""
    found = {}
    for page in GICS_PAGES:
        try:
            page_html = requests.get(f"https://en.wikipedia.org/wiki/{page}", timeout=30,
                                     headers={"User-Agent": "KryptonApp/1.0 (educational market dashboard)"}).text
            table = next(t for t in pd.read_html(io.StringIO(page_html)) if "GICS Sector" in t.columns)
            for _, row in table.iterrows():
                symbol = str(row["Symbol"]).strip().replace(".", "/")  # Nasdaq writes BRK/B, Wikipedia BRK.B
                found.setdefault(symbol, (row["GICS Sector"], row["GICS Sub-Industry"]))
        except Exception:  # if Wikipedia can't be reached, Nasdaq's sectors are used for everyone
            continue
    return found


def download():
    """All US-listed companies, cleaned, biggest first. Columns: ticker, name, sector, industry, country,
    market_cap, price, change_pct."""
    response = requests.get(URL, params={"tableonly": "true", "limit": 25000, "download": "true"},
                            headers=HEADERS, timeout=60)
    response.raise_for_status()
    rows = response.json()["data"]["rows"]
    gics = gics_sectors()
    records = []
    for r in rows:
        symbol = r["symbol"].strip()
        sector, industry = gics.get(symbol, (SECTOR_NAMES.get(r["sector"], "Other"), r["industry"] or ""))
        records.append({"ticker": symbol, "raw_name": r["name"], "name": clean_name(r["name"]), "sector": sector,
                        "industry": industry, "country": r["country"] or "", "market_cap": _number(r["marketCap"]),
                        "price": _number(r["lastsale"]), "change_pct": _number(r["pctchange"])})
    table = pd.DataFrame(records)
    table = table[~table["ticker"].str.contains(r"[\^ ]", regex=True)]  # "^" marks preferred shares
    table = table[~table["raw_name"].str.contains(NOT_COMMON)]
    table = table[(table["market_cap"] > 0) & table["price"].notna()]
    table["ticker"] = table["ticker"].str.replace("/", ".")  # BRK/B -> BRK.B, as most sites write it
    table = table.sort_values("market_cap", ascending=False)
    table = table.drop_duplicates(subset=["name"], keep="first")  # one row per company
    return table.drop(columns="raw_name").reset_index(drop=True)


def by_sector(table):
    """{sector: its companies, biggest first}, sectors ordered by their total size (Other last)."""
    sizes = table.groupby("sector")["market_cap"].sum().sort_values(ascending=False)
    order = [s for s in sizes.index if s != "Other"] + (["Other"] if "Other" in sizes.index else [])
    return {s: table[table["sector"] == s].reset_index(drop=True) for s in order}


def money(value):
    """$3.41T / $812.5B / $45.2M."""
    if value is None or pd.isna(value):
        return "n/a"
    for size, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if value >= size:
            return f"${value / size:,.2f}{unit}" if unit == "T" else f"${value / size:,.1f}{unit}"
    return f"${value:,.0f}"


LIVE_COUNT = 1000  # live prices for this many of the largest companies (covers every tile and big mover)


def live_prices(table, count=LIVE_COUNT):
    """Live prices from Yahoo Finance for the largest companies: {ticker: (price, previous close, as-of date)}.
    (Nasdaq's full list only has the previous trading day's prices.)"""
    import yfinance as yf
    # the largest companies overall, plus the 9 largest of every sector (they're the tiles on the Markets tab)
    tickers = list(dict.fromkeys(list(table["ticker"].head(count))
                                 + list(table.groupby("sector", sort=False).head(9)["ticker"])))
    data = yf.download([t.replace(".", "-") for t in tickers], period="5d", interval="1d", progress=False,
                       auto_adjust=False, threads=True)["Close"]
    found = {}
    for ticker in tickers:
        column = ticker.replace(".", "-")
        if column not in data:
            continue
        series = data[column].dropna()
        if len(series) >= 2:
            found[ticker] = (float(series.iloc[-1]), float(series.iloc[-2]), series.index[-1].date())
    return found


def apply_live(table, live):
    """The company list with live prices, today's moves and market caps for every company we have a live price
    for (column 'live' says which). Re-sorted biggest first."""
    if not live:
        return table.assign(live=False)
    table = table.copy()
    table["live"] = table["ticker"].isin(live)
    for i in table.index[table["live"]]:
        price, previous, _ = live[table.at[i, "ticker"]]
        old_price = table.at[i, "price"]
        if old_price:
            table.at[i, "market_cap"] = table.at[i, "market_cap"] * price / old_price
        table.at[i, "price"] = price
        table.at[i, "change_pct"] = (price / previous - 1) * 100 if previous else None
    return table.sort_values("market_cap", ascending=False).reset_index(drop=True)
