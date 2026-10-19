# explain.py
# Builds the full "why is this happening?" report shown when you click something on the map.
#
# How it works out the CAUSE (no paid AI, just transparent rules):
#   1. The data: when did traffic start falling, how far, and which ship types?
#   2. The news: scan recent headlines for cause keywords (attacks, drought, sanctions...)
#      and pick the cause mentioned most. The matching headlines are shown as evidence.
#   3. Nearby disasters: any cyclone/flood/drought alerts close to the chokepoint.
# It always shows its evidence, so you can judge for yourself.

import math

import pandas as pd

from analysis import STATUS_STYLE, describe_move
from data_sources import CHOKEPOINTS

# Cause -> words that point to it in a headline (all lowercase)
CAUSE_KEYWORDS = {
    "Military action / attacks": [
        "attack", "missile", "drone", "militant", "houthi", "seiz", "navy", "naval", "military",
        "warship", "blockade", "naval mine", " mines", "hijack", "sank", "sink", "explosion", "escort", "war ",
        "hostil", "strike on", "airstrike", "strikes", "fired on", "conflict", "shelling", "offensive",
        "fighting", "killed", "troops", "clash", "bomb", "raid", "ambush", "drills", "soldiers",
        "rebels", "insurgen", "jihadist", "frontline", "front line", "artillery", "invasion",
    ],
    "Sanctions / politics": [
        "sanction", "embargo", "ban on", "tariff", "price cap", "shadow fleet", "export curb",
        "diplomat", "talks", "ceasefire", "treaty",
    ],
    "Drought / low water levels": [
        "drought", "water level", "low water", "rainfall", "draft restriction", "draught", "reservoir",
    ],
    "Storms / severe weather": [
        "storm", "typhoon", "cyclone", "hurricane", "fog", "severe weather", "gale", "flood",
    ],
    "Accident / blockage": [
        "aground", "grounded", "collision", "stuck", "accident", "blocked", "fire on", "oil spill",
    ],
    "Strikes / labour action": [
        "dockworker", "walkout", "trade union", "unions", "industrial action", "port strike", "labour", "labor",
    ],
    "Shipping costs / insurance": [
        "insurance", "war risk", "premium", "freight rate", "shipping cost", "reroute", "rerouting",
        "divert", "avoid",
    ],
}

# What each type of disaster is, and what it tends to affect
DISASTER_EFFECTS = {
    "Cyclone": ("A tropical cyclone (also called a hurricane or typhoon) is a huge rotating storm that forms "
                "over warm ocean water. Its winds, rain and storm surge can close ports, stop ships, flood "
                "factories and shut oil rigs and refineries."),
    "Drought": ("A drought is a long period with much less rain than normal. It shrinks harvests (wheat, corn, "
                "coffee), lowers rivers and canals that ships rely on, and cuts hydro-electric power."),
    "Flood": ("Heavy rain or overflowing rivers. Floods damage farmland, roads, railways and factories, "
              "and can disrupt local supply chains for weeks."),
    "Earthquake": ("A sudden shift in the Earth's crust. Strong quakes can damage factories, ports and power "
                   "plants. In places like Taiwan or Japan that can disrupt chip and car production."),
    "Volcano": ("An eruption can ground flights with ash clouds and damage nearby farmland and towns."),
    "Wildfire": ("Large fires driven by heat, dry conditions and wind. They threaten towns, forests, "
                 "farms and power lines."),
}


def distance_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two points on Earth (haversine formula)."""
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(a))


def classify_causes(headlines):
    """Count how many headlines mention each cause. Returns [(cause, [matching headlines]), ...],
    most-mentioned first."""
    found = {}
    for h in headlines:
        title = h["title"].lower()
        for cause, words in CAUSE_KEYWORDS.items():
            if any(word in title for word in words):
                found.setdefault(cause, []).append(h)
    return sorted(found.items(), key=lambda item: len(item[1]), reverse=True)


def find_drop_start(smooth, normal_level):
    """Find when the CURRENT low period began: walk backwards from today while traffic is
    25%+ below normal, allowing short blips (up to 7 days) back above it.
    Returns a date, or None if traffic isn't low right now."""
    low = (smooth < normal_level * 0.75).tolist()
    if not low[-1]:
        return None
    start = len(low) - 1
    days_not_low = 0
    for i in range(len(low) - 1, -1, -1):
        if low[i]:
            start = i
            days_not_low = 0
        else:
            days_not_low += 1
            if days_not_low > 7:
                break
    return smooth.index[start]


def price_change_since(prices, market, date):
    """% change of a market from a past date until now."""
    series = prices[market].dropna()
    before = series[series.index <= pd.Timestamp(date)]
    if before.empty:
        return None
    return (series.iloc[-1] / before.iloc[-1] - 1) * 100


def explain_chokepoint(name, status, traffic, prices, changes, headlines, disasters):
    """Full report for one chokepoint, as a list of (section title, markdown text)."""
    info = CHOKEPOINTS[name]
    style = STATUS_STYLE[status["Status"]]
    daily = traffic[traffic["chokepoint"] == name].set_index("date").sort_index()
    smooth = daily["ships"].rolling(7).mean().dropna()
    sections = []

    # --- What's happening (from the data) ---
    year_ago = status["Ships/day (a year ago)"]
    text = (f"**{status['Ships/day (last 7 days)']:.0f} ships/day** passed through in the last week "
            f"(data up to {status['Data up to']}).")
    if year_ago:
        text += f" A year ago it was **{year_ago:.0f}/day** ({status['Change vs a year ago (%)']:+d}%)."
    text += (f" Over the last 3 months it averaged **{status['Ships/day (last 3 months)']:.0f}/day** "
             f"({status['Change vs 3 months (%)']:+d}%).")

    drop_start = None
    normal_level = smooth.iloc[:60].mean()  # roughly a year ago, before any recent problem
    if status["Status"] in ("Disrupted", "Below normal"):
        drop_start = find_drop_start(smooth, normal_level)
        if drop_start is not None:
            text += (f"\n\n📉 Traffic started falling sharply around **{drop_start:%d %B %Y}** "
                     "and has stayed low since.")

    # Which kinds of ships disappeared? That's a clue to the cause.
    kinds = ["tankers", "container ships", "bulk carriers"]
    if len(daily) >= 372:
        then, now = daily[kinds].iloc[-372:-365].mean(), daily[kinds].iloc[-7:].mean()
        moves = {k: (now[k] / then[k] - 1) * 100 for k in kinds if then[k] > 0}
        if moves:
            text += "\n\n**By ship type (vs a year ago):** " + ", ".join(
                f"{k} {describe_move(v)} ({now[k]:.0f}/day)" for k, v in moves.items())
            if all(v < -50 for v in moves.values()):
                text += ("\n\n*Every type of ship has fallen sharply at once. That usually points to a "
                         "safety or security problem (ships avoiding the area), not a drop in demand for "
                         "one product.*")
            elif (moves.get("tankers", 0) < -30 and moves.get("container ships", 0) > -10
                  and moves.get("bulk carriers", 0) > -15):
                text += ("\n\n*Mainly oil and gas tankers have fallen. That points to an energy-specific "
                         "cause such as sanctions, export cuts or attacks on tankers.*")
            elif moves.get("bulk carriers", 0) < -30 and moves.get("tankers", 0) > -10:
                text += ("\n\n*Mainly bulk carriers (grain, coal, ore) have fallen. That points to crop, "
                         "commodity or export problems.*")
    sections.append(("📊 What's happening", text))

    # --- Why (likely cause) ---
    causes = classify_causes(headlines)
    nearby = [d for d in disasters
              if distance_km(info["lat"], info["lon"], d["lat"], d["lon"]) < 1500]
    if status["Status"] == "Normal":
        text = "Traffic is close to its usual level, so there's no disruption to explain right now."
        if causes:
            text += f" Recent news still mentions **{causes[0][0].lower()}**, so it's worth watching."
    elif causes:
        top_cause, evidence = causes[0]
        text = (f"**Most likely cause: {top_cause}.** It appears in {len(evidence)} of the "
                f"{len(headlines)} most recent headlines about this area.")
        if len(causes) > 1:
            others = ", ".join(f"{c.lower()} ({len(e)})" for c, e in causes[1:3])
            text += f" Also mentioned: {others}."
        text += "\n\n**Evidence (recent headlines):**\n" + "\n".join(
            f"- [{h['title'].replace('[', '(').replace(']', ')')}]({h['link']}) ({h['date']})"
            for h in evidence[:5])
    else:
        text = ("**No clear cause in recent news.** The drop could be seasonal, a fall in trade demand, "
                "ships choosing other routes, or gaps in the tracking data.")
    if nearby and status["Status"] != "Normal":
        text += "\n\n**Nearby disaster alerts (within 1,500 km):** " + "; ".join(
            f"{d['name']} ({d['alert']} alert)" for d in nearby[:3])
    sections.append(("❓ Why (likely cause)", text))

    # --- Why it matters ---
    sections.append(("🌍 Why it matters", info["why"]))

    # --- Market impact ---
    lines = []
    for market in info["markets"]:
        if market not in changes:
            continue
        c = changes[market]
        line = (f"- **{market}**: {c['Price']:,.2f}, {describe_move(c['1 month (%)'])} this month, "
                f"{describe_move(c['1 year (%)'])} over the year")
        if drop_start is not None:
            since = price_change_since(prices, market, drop_start)
            if since is not None:
                line += f", **{describe_move(since)} since traffic started falling**"
        lines.append(line)
    if lines:
        sections.append(("📈 Market impact", "\n".join(lines) + (
            "\n\n*Markets move for many reasons at once. A move at the same time as a shipping "
            "disruption is a clue, not proof.*")))
    return sections


def explain_disaster(disaster, statuses, headlines):
    """Full report for one disaster alert, as a list of (section title, markdown text)."""
    sections = []
    d = disaster
    timing = f"since {d['started']}" + (f" (latest update {d['until']})" if d["until"] else "")
    text = (f"**{d['alert']} alert**, {timing}.\n\n**Where:** {d['country'][:300]}")
    if d["severity"]:
        text += f"\n\n**Severity:** {d['severity']}"
    sections.append(("📊 What's happening", text))

    sections.append(("❓ Why it happens", DISASTER_EFFECTS.get(d["type"], "A natural hazard event.")))

    # What it could affect: nearby chokepoints + type-specific markets
    effects = []
    for s in statuses:
        info = CHOKEPOINTS[s["Chokepoint"]]
        km = distance_km(d["lat"], d["lon"], info["lat"], info["lon"])
        if km < 1500:
            effects.append(f"- **{s['Chokepoint']}** is about {km:,.0f} km away "
                           f"(currently {STATUS_STYLE[s['Status']]['emoji']} {s['Status'].lower()}).")
    in_gulf_of_mexico = 18 <= d["lat"] <= 31 and -98 <= d["lon"] <= -80
    if d["type"] == "Cyclone" and in_gulf_of_mexico:
        effects.append("- It's in the **Gulf of Mexico**, home to many US oil rigs and refineries: "
                       "watch **oil** and **natural gas** prices.")
    elif d["type"] == "Cyclone" and 100 <= d["lon"] <= 150 and d["lat"] > 0:
        effects.append("- It's near **East Asia's** major ports and factories: watch shipping delays "
                       "and electronics/chip supply.")
    elif d["type"] == "Drought":
        effects.append("- Droughts hit **crops** (watch **wheat**) and can lower rivers and canals "
                       "that ships depend on.")
    elif d["type"] == "Earthquake":
        effects.append("- Watch for damage to factories, ports and power in the affected area.")
    if not effects:
        effects.append("- No major shipping chokepoints nearby. The impact is mostly local.")
    sections.append(("🌍 What it could affect", "\n".join(effects)))

    if headlines:
        sections.append(("📰 Latest news", "\n".join(
            f"- [{h['title'].replace('[', '(').replace(']', ')')}]({h['link']}) ({h['date']})"
            for h in headlines[:5])))
    return sections
