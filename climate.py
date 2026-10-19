# climate.py
# MEASURED causes for weather events, from real climate records (Open-Meteo, free, no key).
#
# For any spot on Earth we download daily rainfall and temperature back to 1991, then ask:
#   - How much rain fell recently compared with the SAME time of year in every past year?
#   - Is it hotter than normal?
#   - Is this the driest / wettest period in 35 years of records?
# That turns "a drought is a lack of rain" into "this area had 58% less rain than normal
# over the last 3 months, the driest Jul–Oct since records began in 1991".

import datetime as dt

import pandas as pd
import requests

HEADERS = {"User-Agent": "Krypton/0.1 (student learning project)"}
RECORDS_START = "1991-01-01"


def get_climate_history(lat, lon):
    """Daily rainfall (mm) and mean temperature (°C) for one spot, 1991 to ~6 days ago
    (the archive runs a few days behind)."""
    end = (dt.date.today() - dt.timedelta(days=6)).isoformat()
    response = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
        "latitude": round(lat, 2), "longitude": round(lon, 2),
        "start_date": RECORDS_START, "end_date": end,
        "daily": "precipitation_sum,temperature_2m_mean",
    }, headers=HEADERS, timeout=90)
    response.raise_for_status()
    daily = response.json()["daily"]
    table = pd.DataFrame({"date": pd.to_datetime(daily["time"]),
                          "rain": daily["precipitation_sum"],
                          "temp": daily["temperature_2m_mean"]}).set_index("date")
    return table.dropna()


def window_compare(history, days, end=None):
    """Compare the `days` days up to `end` (default: latest data) with the same calendar window
    in every earlier year. Returns this period's rain/temperature, the normal, the % difference, and rank."""
    end = history.index[-1] if end is None else min(pd.Timestamp(end), history.index[-1])
    start = end - pd.Timedelta(days=days - 1)
    this_period = history.loc[start:end]

    past = []
    for year in range(history.index[0].year, end.year):
        shift = pd.DateOffset(years=end.year - year)
        chunk = history.loc[start - shift:end - shift]
        if len(chunk) >= days * 0.9:  # only full windows
            past.append({"year": year, "rain": chunk["rain"].sum(), "temp": chunk["temp"].mean()})
    if not past:
        return None
    past = pd.DataFrame(past)

    rain_now, temp_now = this_period["rain"].sum(), this_period["temp"].mean()
    rain_normal, temp_normal = past["rain"].mean(), past["temp"].mean()
    all_rain = pd.concat([past["rain"], pd.Series([rain_now])])
    all_temp = pd.concat([past["temp"], pd.Series([temp_now])])
    return {
        "days": days,
        "period": f"{start:%d %b %Y} – {end:%d %b %Y}",
        "rain": rain_now, "rain_normal": rain_normal,
        "rain_pct": (rain_now / rain_normal - 1) * 100 if rain_normal > 0 else None,
        "temp": temp_now, "temp_normal": temp_normal, "temp_diff": temp_now - temp_normal,
        # rank 1 = driest / hottest of all years on record (including this one)
        "dry_rank": int((all_rain < rain_now).sum()) + 1,
        "wet_rank": int((all_rain > rain_now).sum()) + 1,
        "hot_rank": int((all_temp > temp_now).sum()) + 1,
        "years": len(all_rain),
        "first_year": int(past["year"].min()),
        "max_day_rain": this_period["rain"].max(),
        "max_day_date": this_period["rain"].idxmax(),
    }


def monthly_rain_vs_normal(history, months=12):
    """Rain each of the last `months` months as % of that month's normal (100% = normal).
    Used for the single-line/bar chart in the Weather report."""
    monthly = history["rain"].resample("MS").sum()
    normals = monthly.groupby(monthly.index.month).mean()
    recent = monthly.iloc[-months - 1:-1]  # skip the current, unfinished month
    return pd.Series({month: (value / normals[month.month] * 100) if normals[month.month] > 0 else None
                      for month, value in recent.items()}, name="% of normal rain")


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def rank_text(rank, years, word):
    """'the driest in 36 years of records' / 'the 3rd driest in 36 years'."""
    if rank == 1:
        return f"the **{word} on record** ({years} years of data)"
    if rank <= 5:
        return f"the **{ordinal(rank)} {word}** in {years} years of records"
    return None


def get_sea_temperature(lat, lon):
    """Current sea-surface temperature (°C), or None on land / no data."""
    try:
        response = requests.get("https://marine-api.open-meteo.com/v1/marine", params={
            "latitude": lat, "longitude": lon, "current": "sea_surface_temperature"}, timeout=30)
        return response.json().get("current", {}).get("sea_surface_temperature")
    except (requests.RequestException, ValueError):
        return None


# ---------------------------------------------------------------------------
# Measured cause write-ups for each disaster type
# ---------------------------------------------------------------------------
def describe_window(w, label):
    """Bullet lines describing one comparison window."""
    lines = []
    if w["rain_pct"] is not None:
        direction = "less" if w["rain_pct"] < 0 else "more"
        lines.append(f"- **Rain, {label}** ({w['period']}): {w['rain']:.0f} mm vs a normal "
                     f"{w['rain_normal']:.0f} mm → **{abs(w['rain_pct']):.0f}% {direction} than normal**.")
        for rank_key, word in (("dry_rank", "driest"), ("wet_rank", "wettest")):
            text = rank_text(w[rank_key], w["years"], word)
            if text:
                lines.append(f"  - That makes it {text} for this time of year.")
    lines.append(f"- **Temperature, {label}:** averaged {w['temp']:.1f}°C vs a normal {w['temp_normal']:.1f}°C "
                 f"→ **{w['temp_diff']:+.1f}°C**.")
    text = rank_text(w["hot_rank"], w["years"], "hottest")
    if text:
        lines.append(f"  - That makes it {text} for this time of year.")
    return lines


def measured_causes(disaster):
    """Returns (bullet lines explaining the measured cause, chart series or None)."""
    lat, lon, kind = disaster["lat"], disaster["lon"], disaster["type"]
    lines, chart = [], None

    if kind == "Cyclone":
        sst = get_sea_temperature(lat, lon)
        if sst is not None:
            margin = sst - 26.5
            lines.append(f"- **Sea surface temperature at the storm's position: {sst:.1f}°C.** Tropical cyclones "
                         f"need at least ~26.5°C water to form and strengthen; this is **{margin:+.1f}°C** "
                         f"{'above' if margin >= 0 else 'below'} that threshold"
                         + (", so the ocean is feeding the storm with heat and moisture." if margin >= 1.5 else
                            ", so the storm has little extra fuel and should weaken." if margin < 0 else "."))
        if disaster.get("severity"):
            lines.append(f"- **Measured strength:** {disaster['severity']}.")
        lines.append("- Warm water evaporates and rises; as the vapour condenses it releases heat that powers the "
                     "storm's spin. Low wind shear (winds similar at all heights) lets it organise.")
        return lines, chart

    if kind in ("Earthquake", "Volcano"):
        return lines, chart  # handled by the tectonics table in impact.py

    try:
        history = get_climate_history(lat, lon)
    except (requests.RequestException, ValueError, KeyError):
        return ["- Climate records couldn't be loaded right now."], None

    if kind == "Drought":
        for days, label in ((90, "last 3 months"), (365, "last 12 months")):
            w = window_compare(history, days)
            if w:
                lines += describe_window(w, label)
        chart = monthly_rain_vs_normal(history)
        w90 = window_compare(history, 90)
        if w90 and w90["rain_pct"] is not None:
            if w90["rain_pct"] < -25 and w90["temp_diff"] > 0.5:
                lines.append("- **Measured cause:** a combination of **much less rain than normal AND higher "
                             "temperatures**. Heat speeds up evaporation from soil, rivers and reservoirs, so the "
                             "water that does fall disappears faster.")
            elif w90["rain_pct"] < -25:
                lines.append("- **Measured cause:** mainly a **rainfall shortage**: weather systems that normally "
                             "bring rain have been missing or blocked.")
            elif w90["temp_diff"] > 1:
                lines.append("- **Measured cause:** rainfall is near normal, but **unusual heat** is drying the "
                             "land through evaporation.")
            else:
                lines.append("- Recent rain and temperature at the centre of the area look close to normal, so "
                             "this drought is driven by **longer-term deficits** (see the 12-month numbers) or "
                             "conditions elsewhere in the alert area.")
        lines.append("- Note: GDACS gives one centre point for a drought that can cover several countries, "
                     "so these numbers describe that centre point.")

    elif kind == "Flood":
        # Measure the rain that fell in the run-up to the day the flood started
        flood_start = pd.Timestamp(disaster["started"]) + pd.Timedelta(days=1)
        lines.append(f"- Flood alert began on **{disaster['started']}**; rain measured in the days before it:")
        for days, label in ((7, "7 days before the flood"), (30, "30 days before the flood")):
            w = window_compare(history, days, end=flood_start)
            if w:
                lines += describe_window(w, label)
        w7 = window_compare(history, 7, end=flood_start)
        if w7:
            lines.append(f"- **Wettest single day:** {w7['max_day_rain']:.0f} mm on {w7['max_day_date']:%d %b %Y}.")
            if w7["rain_pct"] is not None and w7["rain_pct"] < 0:
                lines.append("- **Rain at the centre point was NOT above normal**, so the water most likely came "
                             "from **heavy rain upstream** in the river basin, from snow/glacier melt, or from a "
                             "storm surge on the coast, rather than local rainfall.")
            elif w7["rain_pct"] is not None and w7["rain_pct"] > 100:
                lines.append("- **Measured cause:** an **extreme local downpour**, more than double the normal "
                             "rainfall for this time of year, more than the ground and rivers could absorb.")
        chart = monthly_rain_vs_normal(history)

    elif kind == "Wildfire":
        for days, label in ((60, "last 2 months"),):
            w = window_compare(history, days)
            if w:
                lines += describe_window(w, label)
        lines.append("- Fires spread fastest when vegetation has dried out (low rain), temperatures are high and "
                     "winds are strong. The numbers above show how dry and hot the area has been.")
        chart = monthly_rain_vs_normal(history)

    return lines, chart
