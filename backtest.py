# backtest.py
# The TRACK RECORD: did Krypton's researched market effects actually happen in the past?
#
# 1. Find every past event:
#    - chokepoint disruptions since 2019 (ship traffic fell 25%+ below its previous 3 months)
#    - orange/red disaster alerts since 2018 (from GDACS)
# 2. For each event, look at every market the research says it affects (▲ or ▼).
# 3. Measure what that market really did over the next 30 days.
# 4. Compare with the "base rate": how often the market moves that way in ANY random 30 days.
#    A rule is only useful if it beats the base rate.
#
# Run it with:  python backtest.py      (takes ~1–2 minutes; results saved to data/backtest.json)

import datetime as dt
import json
import os
import time

import pandas as pd
import requests
import yfinance as yf

from data_sources import CHOKEPOINTS, HEADERS, PORTWATCH_URL
from impact import CHOKEPOINT_IMPACTS, DOWN, UP, disaster_impacts
from markets import ALL_MARKETS

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "data", "backtest.json")
HOLD_DAYS = 30        # how long after the event we measure the market move
DROP_TRIGGER = 0.75   # traffic below 75% of its previous 3-month average = disruption
COOLDOWN_DAYS = 90    # ignore repeat triggers at the same chokepoint within 90 days


# ---------------------------------------------------------------------------
# 1. HISTORY
# ---------------------------------------------------------------------------
def full_traffic_history():
    """Every daily ship count since 2019 for our chokepoints (paged, 1,000 rows at a time)."""
    port_ids = ", ".join(f"'{c['portid']}'" for c in CHOKEPOINTS.values())
    rows, offset = [], 0
    while True:
        for attempt in range(4):  # the server sometimes drops long downloads, so retry each page
            try:
                response = requests.get(PORTWATCH_URL, params={
                    "where": f"portid IN ({port_ids})", "outFields": "date,portname,n_total",
                    "orderByFields": "ObjectId", "resultOffset": offset, "resultRecordCount": 1000, "f": "json",
                }, headers=HEADERS, timeout=90)
                break
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(3 * (attempt + 1))
        page = [f["attributes"] for f in response.json().get("features", [])]
        rows += page
        if len(page) < 1000:
            break
        offset += 1000
    table = pd.DataFrame(rows).rename(columns={"portname": "chokepoint", "n_total": "ships"})
    table["date"] = pd.to_datetime(table["date"])
    return table.sort_values("date")


def past_disasters(first_year=2018):
    """Every orange/red GDACS alert since `first_year`, one request per year."""
    events = []
    for year in range(first_year, dt.date.today().year + 1):
        response = requests.get("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH", params={
            "eventlist": "TC;EQ;FL;DR;VO;WF", "alertlevel": "Orange;Red",
            "fromDate": f"{year}-01-01", "toDate": f"{year}-12-31"}, headers=HEADERS, timeout=90)
        type_names = {"TC": "Cyclone", "EQ": "Earthquake", "FL": "Flood", "DR": "Drought",
                      "VO": "Volcano", "WF": "Wildfire"}
        for feature in response.json().get("features", []):
            p = feature["properties"]
            lon, lat = feature["geometry"]["coordinates"][:2]
            events.append({"type": type_names.get(p["eventtype"], p["eventtype"]), "name": p["name"],
                           "alert": p["alertlevel"], "started": p["fromdate"][:10], "lat": lat, "lon": lon,
                           "country": (p.get("country") or "").strip()})
    # GDACS can list the same event more than once (episodes); keep one per name + start date
    unique = {(e["name"], e["started"]): e for e in events}
    return list(unique.values())


def price_history(market_names):
    codes = {name: ALL_MARKETS[name] for name in market_names}
    raw = yf.download(list(codes.values()), start="2018-01-01", progress=False, auto_adjust=True)["Close"]
    return raw.rename(columns={code: name for name, code in codes.items()})


# ---------------------------------------------------------------------------
# 2. EVENT DETECTION + MEASUREMENT
# ---------------------------------------------------------------------------
def detect_chokepoint_disruptions(traffic):
    events = []
    for name in CHOKEPOINTS:
        daily = traffic[traffic["chokepoint"] == name].set_index("date")["ships"].sort_index()
        smooth = daily.rolling(7).mean()
        baseline = daily.rolling(90).mean().shift(7)  # average of the 90 days before last week
        last_trigger = None
        for day in smooth.index[100:]:
            if smooth[day] < DROP_TRIGGER * baseline[day]:
                if last_trigger is None or (day - last_trigger).days > COOLDOWN_DAYS:
                    events.append({"kind": "Shipping", "name": name, "date": day.date().isoformat(),
                                   "detail": f"{(smooth[day] / baseline[day] - 1) * 100:.0f}% vs previous 3 months"})
                last_trigger = day
    return events


def forward_move(series, start_date, days=HOLD_DAYS):
    """% change of a market from the first trading day on/after start_date to `days` later."""
    series = series.dropna()
    start_date = pd.Timestamp(start_date)
    after = series[series.index >= start_date]
    if after.empty:
        return None
    start_day, start_price = after.index[0], after.iloc[0]
    later = series[series.index >= start_day + pd.Timedelta(days=days)]
    if later.empty or (start_day - start_date).days > 5:
        return None  # event too recent, or no prices around the event date
    return (later.iloc[0] / start_price - 1) * 100


def base_rate_up(series, days=HOLD_DAYS):
    """In what share of ALL 30-day periods since 2018 did this market rise?"""
    series = series.dropna()
    if len(series) < 300:
        return None
    future = series.reindex(series.index + pd.Timedelta(days=days), method="bfill")
    moves = (future.values / series.values - 1)
    valid = moves[~pd.isna(moves)][:-21]  # drop the last month (no full future yet)
    return float((valid > 0).mean()) if len(valid) else None


# ---------------------------------------------------------------------------
# 3. RUN
# ---------------------------------------------------------------------------
def run_backtest(progress=print):
    progress("Downloading ship traffic since 2019...")
    traffic = full_traffic_history()
    shipping_events = detect_chokepoint_disruptions(traffic)
    progress(f"Found {len(shipping_events)} past chokepoint disruptions.")

    progress("Downloading disaster alerts since 2018...")
    disasters = past_disasters()
    disaster_events = []
    for d in disasters:
        region, impacts, specific = disaster_impacts(d)
        if specific:  # only test region-specific research (that's the claim worth checking)
            disaster_events.append({"kind": d["type"], "name": d["name"], "date": d["started"],
                                    "detail": f"{d['alert']} alert · {region}", "impacts": impacts,
                                    "rule": f"{d['type']} in {region}"})
    progress(f"Found {len(disasters)} past disasters, {len(disaster_events)} in regions we have research for.")

    for e in shipping_events:
        e["impacts"] = CHOKEPOINT_IMPACTS.get(e["name"], [])
        e["rule"] = f"Disruption at {e['name']}"
    all_events = shipping_events + disaster_events

    markets = sorted({m for e in all_events for m, direction, _ in e["impacts"] if direction in (UP, DOWN)})
    progress(f"Downloading price history for {len(markets)} markets since 2018...")
    prices = price_history(markets)
    base_rates = {m: base_rate_up(prices[m]) for m in markets if m in prices}

    predictions = []
    for e in all_events:
        for market, direction, why in e["impacts"]:
            if direction not in (UP, DOWN) or market not in prices:
                continue
            move = forward_move(prices[market], e["date"])
            if move is None:
                continue
            up_rate = base_rates.get(market)
            predictions.append({
                "event": e["name"], "kind": e["kind"], "rule": e["rule"], "date": e["date"], "detail": e["detail"],
                "market": market, "expected": direction, "move": round(float(move), 2),
                "hit": bool(move > 0) if direction == UP else bool(move < 0),
                "base_rate": (up_rate if direction == UP else 1 - up_rate) if up_rate is not None else None,
            })

    results = {"run": dt.datetime.now().strftime("%d %b %Y %H:%M"), "hold_days": HOLD_DAYS,
               "events": [{k: v for k, v in e.items() if k != "impacts"} for e in all_events],
               "predictions": predictions}
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=1)
    progress(f"Done: {len(predictions)} predictions checked.")
    return results


def load_results():
    if not os.path.exists(RESULTS_FILE):
        return None
    with open(RESULTS_FILE, encoding="utf-8") as file:
        return json.load(file)


def summarise(results):
    """Hit rates overall, per rule and per market, compared with base rates."""
    table = pd.DataFrame(results["predictions"])
    if table.empty:
        return None, None, None
    overall = {"predictions": len(table), "hit_rate": table["hit"].mean(),
               "base_rate": table["base_rate"].mean(),
               # count name + date: GDACS reuses names like "Flood in China" for separate floods
               "events": table[["event", "date"]].drop_duplicates().shape[0]}

    def group(by):
        g = table.groupby(by).agg(predictions=("hit", "size"), hit_rate=("hit", "mean"),
                                  base_rate=("base_rate", "mean"), avg_move=("move", "mean"))
        g["edge"] = g["hit_rate"] - g["base_rate"]
        return g.sort_values("predictions", ascending=False)
    return overall, group("rule"), group(["market", "expected"])


if __name__ == "__main__":
    output = run_backtest()
    overall, by_rule, by_market = summarise(output)
    print(overall)
    print(by_rule.head(15).round(2).to_string())
