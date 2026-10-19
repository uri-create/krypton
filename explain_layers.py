# explain_layers.py
# Full click-reports for the newer map layers: weather, air cargo hubs and conflicts,
# plus a "Conclusion" for chokepoints. Same idea as explain.py: transparent rules,
# with the evidence always shown.

import datetime as dt

from analysis import STATUS_STYLE, describe_move
from data_sources import CHOKEPOINTS, baseline_ready
from explain import CAUSE_KEYWORDS, classify_causes, distance_km
from layers import AIR_HUBS, CONFLICT_ZONES, SEA_ROUTES

MILITARY_WORDS = CAUSE_KEYWORDS["Military action / attacks"]


def news_list(headlines, limit=6):
    """Headlines as markdown bullet links."""
    return "\n".join(
        f"- [{h['title'].replace('[', '(').replace(']', ')')}]({h['link']}) ({h['date']})"
        for h in headlines[:limit])


def market_lines(markets, changes):
    """'- Brent oil: 109.86, up 5% this month, up 80% over the year' for each market."""
    lines = []
    for market in markets:
        if market in changes:
            c = changes[market]
            lines.append(f"- **{market}**: {c['Price']:,.2f}, {describe_move(c['1 month (%)'])} this month, "
                         f"{describe_move(c['1 year (%)'])} over the year")
    return "\n".join(lines)


# ===========================================================================
# WEATHER
# ===========================================================================
def weather_flags(w):
    """Turn raw weather numbers into warnings. Thresholds are rough rules of thumb:
    ships slow down or wait in waves over ~3 m, and ports/airports struggle in gusts over ~60 km/h."""
    flags = []
    if not w:
        return flags
    gusts, waves = w.get("gusts") or 0, w.get("waves_m") or 0
    if gusts >= 90:
        flags.append(("Storm-force winds", f"gusts of {gusts:.0f} km/h"))
    elif gusts >= 60:
        flags.append(("Strong winds", f"gusts of {gusts:.0f} km/h"))
    if waves >= 5:
        flags.append(("Very rough seas", f"{waves:.1f} m waves"))
    elif waves >= 3:
        flags.append(("Rough seas", f"{waves:.1f} m waves"))
    if w.get("visibility_km") is not None and w["visibility_km"] < 1:
        flags.append(("Fog / very low visibility", f"{w['visibility_km'] * 1000:.0f} m visibility"))
    if (w.get("code") or 0) >= 95:
        flags.append(("Thunderstorms", w["conditions"].lower()))
    elif w.get("code") in (65, 67, 75, 82, 86):
        flags.append(("Heavy rain or snow", w["conditions"].lower()))
    return flags


def describe_weather(w):
    """One-paragraph description of current weather."""
    if not w or w.get("temperature") is None:
        return "No weather data available."
    text = (f"**{w['conditions']}**, {w['temperature']:.0f}°C, wind {w['wind']:.0f} km/h "
            f"(gusts {w['gusts']:.0f} km/h)")
    if w.get("visibility_km") is not None:
        text += f", visibility {w['visibility_km']:.0f} km"
    if w.get("waves_m") is not None:
        text += f", waves {w['waves_m']:.1f} m"
    text += "."
    flags = weather_flags(w)
    if flags:
        text += " ⚠️ " + "; ".join(f"**{name}** ({detail})" for name, detail in flags) + "."
    else:
        text += " Nothing here should slow ships or flights."
    return text


WEATHER_REASONS = {
    "wind": "Strong winds come from deep low-pressure systems (storms). The bigger the pressure difference "
            "between two areas, the stronger the wind.",
    "seas": "Big waves are built by strong wind blowing over long stretches of open water, or by swell "
            "travelling from distant storms.",
    "fog": "Fog forms when moist air cools to its dew point, often over cold water or on calm, clear nights.",
    "thunder": "Thunderstorms grow when warm, moist air rises fast into much colder air above.",
    "rain": "Heavy rain or snow comes from moist air being lifted by a weather front or storm system.",
}


def explain_rough_weather(place, kind, w):
    """Report for a 'severe weather right now' icon at a chokepoint or air hub."""
    sections = [("📊 What's happening", describe_weather(w))]
    reasons = []
    for name, _ in weather_flags(w):
        lowered = name.lower()
        key = next((k for k in WEATHER_REASONS if k in lowered), "rain")
        reasons.append(WEATHER_REASONS[key])
    sections.append(("❓ Why it happens", " ".join(dict.fromkeys(reasons))))
    if kind == "chokepoint":
        effect = ("Ships may slow down, wait at anchor, or be held by port and canal authorities until "
                  "conditions improve. Short delays here can ripple into later arrivals at ports.")
    else:
        effect = ("Flights may be delayed, diverted or cancelled. Strong crosswinds and low visibility are "
                  "the main problems. A backlog at a hub can delay parcels for days.")
    sections.append(("🌍 What it could affect", effect))
    sections.append(("🧭 Conclusion",
                     f"Weather at **{place}** is a **short-term** risk. It usually clears within hours to a "
                     "couple of days and rarely moves markets on its own, unless it's part of a big named storm."))
    return sections


# ===========================================================================
# MILITARY
# ===========================================================================
INTENSITY_COLOUR = {"High": "#ff2d55", "Elevated": "#ff7a45", "Low": "#9b6b78", "Quiet": "#4a4a4a"}


def military_intensity(headlines):
    """How active is a conflict right now? Counts recent headlines that mention military action,
    and how many of those are from the last 48 hours. Returns (level, military_count, last_48h_count)."""
    military = [h for h in headlines if any(word in h["title"].lower() for word in MILITARY_WORDS)]
    now = dt.datetime.now(dt.timezone.utc)
    fresh = [h for h in military if h.get("published") and (now - h["published"]).total_seconds() < 48 * 3600]
    if len(military) >= 8 and len(fresh) >= 3:
        level = "High"
    elif len(military) >= 4:
        level = "Elevated"
    elif len(military) >= 2:
        level = "Low"
    else:
        level = "Quiet"
    return level, len(military), len(fresh)


def explain_conflict(name, headlines, air, air_history, statuses, changes):
    zone = CONFLICT_ZONES[name]
    level, military, fresh = military_intensity(headlines)
    sections = [("📜 Background: what led to this", zone["background"])]

    text = (f"**Activity level: {level}.** {military} of the {len(headlines)} most recent headlines about "
            f"this area mention military action, {fresh} of them in the last 48 hours.")
    dated = [h["published"] for h in headlines if h.get("published")]
    if dated:
        text += f" Latest report: **{max(dated):%d %b %Y, %H:%M} UTC**."
    sections.append(("📊 What's happening now", text + "\n\n" + news_list(headlines)))

    causes = classify_causes(headlines)
    text = ("Themes in the latest news (number of headlines):\n" + "\n".join(
        f"- **{cause}**: {len(evidence)}" for cause, evidence in causes[:4])) if causes \
        else "No clear theme in the latest headlines."
    sections.append(("❓ Why (themes in the news)", text))

    count = (air or {}).get("counts", {}).get(name, {}).get("airborne")
    if count is not None:
        text = f"**{count} aircraft** are flying over this area right now."
        past = air_history.get(name)
        if baseline_ready(past):
            text += (f" That's {describe_move((count / past['average'] - 1) * 100)} vs the average of "
                     f"{past['snapshots']} earlier snapshots ({past['average']:.0f}).")
        else:
            text += (" (Krypton needs snapshots from at least 3 different days at this time of day before it can say "
                     "what's normal here. It saves one every time it loads.)")
        text += (" Airlines avoid active war zones, so an empty sky over a normally busy region is a strong "
                 "sign of danger or closed airspace.")
        sections.append(("✈️ Airspace", text))

    effects = []
    for s in statuses:
        cp = CHOKEPOINTS[s["Chokepoint"]]
        km = distance_km(zone["lat"], zone["lon"], cp["lat"], cp["lon"])
        if km < 2000:
            effects.append(f"- 🚢 **{s['Chokepoint']}** ({km:,.0f} km away) is "
                           f"{STATUS_STYLE[s['Status']]['emoji']} {s['Status'].lower()}.")
    for hub_name, hub in AIR_HUBS.items():
        km = distance_km(zone["lat"], zone["lon"], hub["lat"], hub["lon"])
        if km < 1500:
            effects.append(f"- ✈️ **{hub_name}** cargo hub is {km:,.0f} km away.")
    text = "\n".join(effects) if effects else "No major shipping chokepoints or cargo hubs nearby."
    lines = market_lines(zone["markets"], changes)
    if lines:
        text += "\n\n**Markets to watch:**\n" + lines
    sections.append(("🌍 What it could affect", text))

    if level == "High":
        verdict = ("This conflict is **very active right now**, with frequent fresh reports of military action. "
                   "Expect continued risk to nearby trade routes and the markets listed above.")
    elif level == "Elevated":
        verdict = ("Military activity is **ongoing but not at peak intensity** in the news. Watch for "
                   "escalation, and watch nearby shipping and air traffic for early signs.")
    else:
        verdict = "The area is **relatively quiet** in recent news, but the underlying tensions remain."
    sections.append(("🧭 Conclusion", verdict))
    return sections


# ===========================================================================
# AIR CARGO HUBS
# ===========================================================================
HUB_COLOUR = {"Normal": "#00e0ff", "Building baseline": "#00e0ff", "Unusually busy": "#3fa9ff",
              "Unusually quiet": "#ffb000", "No coverage": "#4f6475", "No data": "#4f6475"}


def air_hub_status(name, air, air_history):
    """Returns (status, aircraft count)."""
    count = (air or {}).get("counts", {}).get(name, {}).get("airborne")
    if count is None:
        return "No data", None
    if count == 0:
        return "No coverage", count
    past = air_history.get(name)
    if not baseline_ready(past):
        return "Building baseline", count
    ratio = count / past["average"]
    if ratio < 0.6:
        return "Unusually quiet", count
    if ratio > 1.4:
        return "Unusually busy", count
    return "Normal", count


def explain_air_hub(name, air, air_history, weather, headlines, changes, conflict_levels):
    hub = AIR_HUBS[name]
    status, count = air_hub_status(name, air, air_history)
    sections = [("🌍 What this hub is", hub["role"])]

    ground = (air or {}).get("counts", {}).get(name, {}).get("on_ground")
    if count is None:
        text = "Live aircraft data isn't available right now."
    elif count == 0:
        text = ("**No aircraft detected.** OpenSky relies on volunteer radio receivers. Parts of China, Russia, "
                "Africa and the Middle East have very few, so this most likely means **no tracking coverage**, "
                "not an empty sky.")
    else:
        text = (f"**{count} aircraft** in the air within 150 km right now, plus {ground} tracked on the ground "
                f"(snapshot {air['time']} UTC).")
        past = air_history.get(name)
        if baseline_ready(past):
            text += f" Average of {past['snapshots']} earlier snapshots: {past['average']:.0f}."
        else:
            text += (" Krypton needs snapshots from at least 3 different days at this time of day before it can say "
                     "what's normal here.")
        text += f" **Status: {status}.** This counts all planes, passenger and cargo."
    sections.append(("📊 Live air traffic", text))

    sections.append(("🌦️ Weather now", describe_weather(weather)))

    causes = classify_causes(headlines)
    nearby = [c for c, info in CONFLICT_ZONES.items()
              if distance_km(hub["lat"], hub["lon"], info["lat"], info["lon"]) < 1500
              and conflict_levels.get(c) in ("High", "Elevated")]
    items = []
    if weather_flags(weather):
        items.append("- ⚠️ **Bad weather** right now could delay flights.")
    for c in nearby:
        items.append(f"- 🛡️ Active conflict nearby: **{c}** ({conflict_levels[c].lower()} activity). "
                     "Airlines may reroute or avoid airspace.")
    if causes:
        items.append(f"- 📰 Main theme in recent news: **{causes[0][0].lower()}** ({len(causes[0][1])} headlines).")
    sections.append(("❓ What could be affecting it", "\n".join(items) if items else
                     "Nothing unusual found: no bad weather, no nearby active conflicts, no clear problem in the news."))

    if headlines:
        sections.append(("📰 Latest news", news_list(headlines, 5)))
    lines = market_lines(hub["markets"], changes)
    if lines:
        sections.append(("📈 Markets linked to this hub", lines))

    if status == "Unusually quiet":
        verdict = "Traffic is **well below normal**. Check the weather and news above for the reason."
    elif status == "Unusually busy":
        verdict = "Traffic is **unusually high**. This could be rerouted flights or a seasonal rush."
    elif nearby or weather_flags(weather):
        verdict = "Traffic looks normal, but **nearby risks** (listed above) are worth watching."
    elif status == "No coverage":
        verdict = "Can't judge live traffic here because of tracking gaps. Use the news and weather instead."
    else:
        verdict = "Operating **normally** as far as live data shows."
    sections.append(("🧭 Conclusion", verdict))
    return sections


# ===========================================================================
# CHOKEPOINT CONCLUSION (added to the existing chokepoint report)
# ===========================================================================
def chokepoint_extras(name, status, headlines, weather):
    """Extra sections for a chokepoint: weather now, routes through it, and a conclusion."""
    sections = [("🌦️ Weather & sea now", describe_weather(weather))]
    routes = [r for r, info in SEA_ROUTES.items() if name in info["chokepoints"]]
    if routes:
        sections.append(("🛳️ Shipping routes through here", "\n".join(
            f"- **{r}**: {SEA_ROUTES[r]['carries']}" for r in routes)))

    causes = classify_causes(headlines)
    cause = causes[0][0].lower() if causes else "no clear cause in the news"
    if status["Status"] == "Disrupted":
        verdict = (f"**{name} is seriously disrupted** (likely cause: {cause}). Expect longer journeys, higher "
                   "shipping costs and pressure on the linked markets until traffic recovers.")
    elif status["Status"] == "Below normal":
        verdict = (f"**{name} is running below normal** (likely cause: {cause}). Not a crisis yet, but worth "
                   "watching for further drops.")
    elif status["Status"] == "Unusually busy":
        verdict = f"**{name} is unusually busy.** Ships may be diverting here from another route."
    else:
        verdict = f"**{name} is operating normally.**"
    if weather_flags(weather):
        verdict += " Current bad weather may add short delays."
    sections.append(("🧭 Conclusion", verdict))
    return sections
