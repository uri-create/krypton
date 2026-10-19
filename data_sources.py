# data_sources.py
# Downloads everything Krypton needs. All sources are free and need no account or key:
#   - IMF PortWatch   -> how many ships pass through the world's key chokepoints each day
#   - GDACS           -> global disaster alerts (cyclones, floods, droughts, earthquakes)
#   - Google News RSS -> latest headlines (an official public feed, not scraping)
#   - Yahoo Finance   -> prices for oil, gas, gold, wheat, shipping and stocks

import datetime as dt
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import pandas as pd
import requests
import yfinance as yf

HEADERS = {"User-Agent": "Krypton/0.1 (student learning project)"}

# The chokepoints we watch: where they are, why they matter, and which markets they can move.
# (portid is the IMF PortWatch code for each one.)
CHOKEPOINTS = {
    "Strait of Hormuz": {
        "portid": "chokepoint6", "lat": 26.6, "lon": 56.3,
        "why": "About a fifth of the world's oil passes through here, from the Persian Gulf to the world.",
        "markets": ["Brent oil", "WTI oil", "Natural gas (US)"],
        "news": "Strait of Hormuz shipping",
    },
    "Bab el-Mandeb Strait": {
        "portid": "chokepoint4", "lat": 12.6, "lon": 43.4,
        "why": "The southern gate of the Red Sea. Ships between Asia and Europe via Suez must pass it.",
        "markets": ["Brent oil", "Dry bulk shipping rates"],
        "news": "Red Sea Bab el-Mandeb shipping",
    },
    "Suez Canal": {
        "portid": "chokepoint1", "lat": 30.6, "lon": 32.3,
        "why": "The main shortcut between Asia and Europe. If it's avoided, ships sail around Africa.",
        "markets": ["Brent oil", "Dry bulk shipping rates"],
        "news": "Suez Canal shipping",
    },
    "Cape of Good Hope": {
        "portid": "chokepoint7", "lat": -34.4, "lon": 18.5,
        "why": "The long way around Africa. MORE traffic here usually means ships are avoiding the Red Sea.",
        "markets": ["Dry bulk shipping rates", "Brent oil"],
        "news": "Cape of Good Hope shipping rerouting",
    },
    "Panama Canal": {
        "portid": "chokepoint2", "lat": 9.1, "lon": -79.7,
        "why": "Links the Atlantic and Pacific. Runs on lake water, so droughts can cut traffic.",
        "markets": ["Natural gas (US)", "Wheat"],
        "news": "Panama Canal shipping",
    },
    "Malacca Strait": {
        "portid": "chokepoint5", "lat": 2.5, "lon": 101.5,
        "why": "One of the busiest sea lanes on Earth: the main oil route to China, Japan and South Korea.",
        "markets": ["Brent oil", "S&P 500"],
        "news": "Malacca Strait shipping",
    },
    "Taiwan Strait": {
        "portid": "chokepoint11", "lat": 24.5, "lon": 119.5,
        "why": "A major East Asian trade route, next to Taiwan, which makes most of the world's advanced chips.",
        "markets": ["S&P 500", "Gold"],
        "news": "Taiwan Strait shipping",
    },
    "Bosporus Strait": {
        "portid": "chokepoint3", "lat": 41.1, "lon": 29.05,
        "why": "The only sea exit from the Black Sea: Russian oil and Ukrainian/Russian grain pass here.",
        "markets": ["Wheat", "Brent oil"],
        "news": "Bosporus Black Sea shipping",
    },
    "Gibraltar Strait": {
        "portid": "chokepoint8", "lat": 35.95, "lon": -5.6,
        "why": "The gateway between the Mediterranean and the Atlantic.",
        "markets": ["Brent oil"],
        "news": "Strait of Gibraltar shipping",
    },
    "Dover Strait": {
        "portid": "chokepoint9", "lat": 51.0, "lon": 1.45,
        "why": "One of the busiest shipping lanes in the world, feeding northern Europe's ports.",
        "markets": ["S&P 500"],
        "news": "English Channel Dover shipping",
    },
}

# Markets we track (name -> Yahoo Finance code)
MARKETS = {
    "Brent oil": "BZ=F",
    "WTI oil": "CL=F",
    "Natural gas (US)": "NG=F",
    "Gold": "GC=F",
    "Wheat": "ZW=F",
    "Dry bulk shipping rates": "BDRY",   # a fund that tracks the cost of shipping raw materials
    "S&P 500": "^GSPC",           # the 500 biggest US companies
    "Defence stocks fund": "ITA",      # a fund of US defence companies
    "FedEx": "FDX",
    "UPS": "UPS",
    "Airlines": "JETS",           # a fund of airline stocks
}

PORTWATCH_URL = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
                 "Daily_Chokepoints_Data/FeatureServer/0/query")


def get_chokepoint_traffic(days=400):
    """Daily ship counts for our chokepoints over the last `days` days.
    The server sends at most 1,000 rows at a time, so we ask page by page."""
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    port_ids = ", ".join(f"'{info['portid']}'" for info in CHOKEPOINTS.values())
    rows = []
    offset = 0
    while True:
        response = requests.get(PORTWATCH_URL, params={
            "where": f"date >= '{since}' AND portid IN ({port_ids})",
            "outFields": "date,portname,n_total,n_tanker,n_container,n_dry_bulk",
            "orderByFields": "ObjectId",
            "resultOffset": offset,
            "resultRecordCount": 1000,
            "f": "json",
        }, headers=HEADERS, timeout=60)
        response.raise_for_status()
        page = [feature["attributes"] for feature in response.json().get("features", [])]
        rows.extend(page)
        if len(page) < 1000:  # last page
            break
        offset += 1000

    table = pd.DataFrame(rows).rename(columns={
        "portname": "chokepoint", "n_total": "ships", "n_tanker": "tankers",
        "n_container": "container ships", "n_dry_bulk": "bulk carriers",
    })
    table["date"] = pd.to_datetime(table["date"])
    return table.sort_values("date")


def get_disasters(days=30):
    """Orange and red disaster alerts from GDACS over the last `days` days."""
    today = dt.date.today()
    response = requests.get(
        "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH",
        params={
            "eventlist": "TC;EQ;FL;DR;VO;WF",  # cyclones, earthquakes, floods, droughts, volcanoes, wildfires
            "alertlevel": "Orange;Red",
            "fromDate": (today - dt.timedelta(days=days)).isoformat(),
            "toDate": today.isoformat(),
        },
        headers=HEADERS, timeout=60,
    )
    response.raise_for_status()
    type_names = {"TC": "Cyclone", "EQ": "Earthquake", "FL": "Flood", "DR": "Drought",
                  "VO": "Volcano", "WF": "Wildfire"}
    disasters = []
    for feature in response.json().get("features", []):
        info = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"][:2]
        disasters.append({
            "type": type_names.get(info["eventtype"], info["eventtype"]),
            "alert": info["alertlevel"],
            "name": info["name"],
            "country": (info.get("country") or "").strip(),
            "started": info["fromdate"][:10],
            "until": (info.get("todate") or "")[:10],
            "ongoing": str(info.get("iscurrent")).lower() == "true",
            "severity": (info.get("severitydata") or {}).get("severitytext", ""),
            "lat": lat, "lon": lon,
            "link": info.get("url", {}).get("report", ""),
        })
    return disasters


def get_headlines(topic, how_many=15):
    """Latest headlines about a topic from the past week, via Google News' public RSS feed."""
    response = requests.get(
        "https://news.google.com/rss/search",
        params={"q": f"{topic} when:7d", "hl": "en-US", "gl": "US", "ceid": "US:en"},
        headers=HEADERS, timeout=30,
    )
    response.raise_for_status()
    headlines = []
    for item in ET.fromstring(response.content).findall(".//item")[:how_many]:
        published = item.findtext("pubDate", "")
        try:
            when = parsedate_to_datetime(published)  # exact time, used to see how fresh news is
        except (TypeError, ValueError):
            when = None
        headlines.append({
            "title": item.findtext("title"),
            "link": item.findtext("link"),
            "date": published[:16],  # e.g. "Wed, 14 Oct 2026"
            "published": when,
        })
    return headlines


def get_prices(period="1y"):
    """Daily closing prices for every market we track (one column per market, ~105 markets
    grouped by sector in markets.py)."""
    from markets import ALL_MARKETS
    codes = list(ALL_MARKETS.values())
    prices = yf.download(codes, period=period, progress=False, auto_adjust=True)["Close"]
    prices = prices.rename(columns={code: name for name, code in ALL_MARKETS.items()})
    return prices[[name for name in ALL_MARKETS if name in prices.columns]]  # keep our order


# ---------------------------------------------------------------------------
# LIVE AIRCRAFT (OpenSky Network, free, no key)
# ---------------------------------------------------------------------------
import math
import os
from concurrent.futures import ThreadPoolExecutor as _Pool

AIR_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "air_history.csv")
HUB_RADIUS_KM = 150  # planes within this distance count as "at or near" a hub


def _distance_km(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(a))


def get_air_traffic(hubs, zones):
    """Download every aircraft in the sky right now (one request, ~12,000 planes), then count:
      - planes within 150 km of each cargo hub
      - planes over each conflict zone
    Each count is also saved to data/air_history.csv, so over time we learn what 'normal' is."""
    response = requests.get("https://opensky-network.org/api/states/all", headers=HEADERS, timeout=90)
    response.raise_for_status()
    planes = [(p[6], p[5], p[8]) for p in response.json().get("states") or []
              if p[5] is not None and p[6] is not None]  # (lat, lon, on_ground)

    counts = {}
    for name, hub in hubs.items():
        near = [p for p in planes
                if abs(p[0] - hub["lat"]) < 2 and _distance_km(hub["lat"], hub["lon"], p[0], p[1]) <= HUB_RADIUS_KM]
        counts[name] = {"airborne": sum(1 for p in near if not p[2]), "on_ground": sum(1 for p in near if p[2])}
    for name, zone in zones.items():
        s, w, n, e = zone["box"]
        counts[name] = {"airborne": sum(1 for p in planes if s <= p[0] <= n and w <= p[1] <= e and not p[2]),
                        "on_ground": 0}

    # Save this snapshot to the history file
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    os.makedirs(os.path.dirname(AIR_HISTORY_FILE), exist_ok=True)
    new_rows = pd.DataFrame([{"time": now, "place": k, "airborne": v["airborne"]} for k, v in counts.items()])
    new_rows.to_csv(AIR_HISTORY_FILE, mode="a", index=False, header=not os.path.exists(AIR_HISTORY_FILE))

    return {"total_planes": len(planes), "counts": counts, "time": now}


def get_air_history(hour=None):
    """Average aircraft count per place from earlier snapshots (empty if none saved yet).
    Air traffic has a strong daily rhythm (busy by day, quiet at night), so by default we only
    compare with snapshots taken within 2 hours of the CURRENT time of day (UTC)."""
    if not os.path.exists(AIR_HISTORY_FILE):
        return {}
    history = pd.read_csv(AIR_HISTORY_FILE)
    hour = dt.datetime.now(dt.timezone.utc).hour if hour is None else hour
    snapshot_hour = pd.to_datetime(history["time"]).dt.hour
    gap = (snapshot_hour - hour).abs()
    history = history[gap.where(gap <= 12, 24 - gap) <= 2]  # within 2 hours, wrapping round midnight
    history = history.assign(day=pd.to_datetime(history["time"]).dt.date)
    summary = history.groupby("place").agg(mean=("airborne", "mean"), count=("airborne", "size"),
                                           days=("day", "nunique"))
    # "days" = on how many DIFFERENT days we have a snapshot at this time of day. A "normal" level
    # is only trusted once it covers at least 3 different days (see MIN_BASELINE_DAYS).
    return {place: {"average": row["mean"], "snapshots": int(row["count"]), "days": int(row["days"])}
            for place, row in summary.iterrows()}


MIN_BASELINE_DAYS = 3  # need this many different days of history before calling traffic "unusual"


def baseline_ready(past):
    """True once we have enough history (3+ different days at this time of day) to judge 'normal'."""
    return bool(past and past.get("days", 0) >= MIN_BASELINE_DAYS and past["average"])


# ---------------------------------------------------------------------------
# WEATHER & SEA STATE (Open-Meteo, free, no key)
# ---------------------------------------------------------------------------
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Freezing fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Rain showers",
    81: "Heavy showers", 82: "Violent showers", 85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}


def get_weather(places, marine=False):
    """Current weather for many places in ONE request. `places` = {name: {"lat":..., "lon":...}}.
    With marine=True, also gets wave height (for sea locations)."""
    names = list(places)
    lats = ",".join(str(places[n]["lat"]) for n in names)
    lons = ",".join(str(places[n]["lon"]) for n in names)
    # The free server is sometimes briefly busy (error 503), so try up to 3 times
    for attempt in range(3):
        response = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lats, "longitude": lons,
            "current": "temperature_2m,wind_speed_10m,wind_gusts_10m,weather_code,visibility,precipitation",
        }, timeout=60)
        if response.status_code < 500:
            break
        time.sleep(2 + attempt * 3)
    response.raise_for_status()
    results = response.json()
    results = results if isinstance(results, list) else [results]

    weather = {}
    for name, result in zip(names, results):
        now = result.get("current", {})
        weather[name] = {
            "temperature": now.get("temperature_2m"),
            "wind": now.get("wind_speed_10m"),
            "gusts": now.get("wind_gusts_10m"),
            "visibility_km": (now.get("visibility") or 0) / 1000 if now.get("visibility") is not None else None,
            "rain_mm": now.get("precipitation"),
            "conditions": WEATHER_CODES.get(now.get("weather_code"), "Unknown"),
            "code": now.get("weather_code"),
            "waves_m": None,
        }

    if marine:
        try:
            response = requests.get("https://marine-api.open-meteo.com/v1/marine", params={
                "latitude": lats, "longitude": lons, "current": "wave_height",
            }, timeout=60)
            sea = response.json()
            sea = sea if isinstance(sea, list) else [sea]
            for name, result in zip(names, sea):
                weather[name]["waves_m"] = result.get("current", {}).get("wave_height")
        except (requests.RequestException, ValueError):
            pass  # wave data is a bonus; carry on without it
    return weather


# ---------------------------------------------------------------------------
# NEWS FOR MANY TOPICS AT ONCE
# ---------------------------------------------------------------------------
def get_many_headlines(topics):
    """Headlines for several topics in parallel. `topics` = {name: search text}."""
    def fetch(item):
        name, query = item
        try:
            return name, get_headlines(query)
        except (requests.RequestException, ET.ParseError):
            return name, []
    with _Pool(max_workers=5) as pool:
        return dict(pool.map(fetch, topics.items()))


def get_air_series(place):
    """Every saved aircraft-count snapshot for one place, as a time series (for charts)."""
    if not os.path.exists(AIR_HISTORY_FILE):
        return pd.Series(dtype=float)
    history = pd.read_csv(AIR_HISTORY_FILE)
    rows = history[history["place"] == place]
    return pd.Series(rows["airborne"].values, index=pd.to_datetime(rows["time"]), name=place)
