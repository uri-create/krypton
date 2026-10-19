# engine.py
# The "brain" of Krypton, shared by the web app and the
# daily briefing. It downloads every feed and turns it into one list of EVENTS, each with a
# category, position, severity and the markets it affects. No web-page code in here.

import html

from analysis import chokepoint_status, price_changes
from data_sources import (CHOKEPOINTS, get_air_history, get_air_traffic, get_chokepoint_traffic, get_disasters,
                          get_many_headlines, get_prices, get_weather)
from explain_layers import air_hub_status, military_intensity, weather_flags
from impact import CHOKEPOINT_IMPACTS, CONFLICT_IMPACTS, HUB_IMPACTS, disaster_impacts
from layers import AIR_HUBS, CONFLICT_ZONES
from severity import (SEVERITY, chokepoint_severity, conflict_severity, disaster_severity, hub_severity,
                      rough_severity)

WEATHER_ICONS = {"Cyclone": "fa-cloud-bolt", "Flood": "fa-cloud-showers-heavy", "Drought": "fa-cloud-sun",
                 "Wildfire": "fa-cloud"}


def safe(text):
    """Make outside text safe to put on the map (backticks break the map's code)."""
    return html.escape(str(text).replace("`", "'"))


def fetch_all():
    """Download every live feed. (The web app uses its own cached versions of these instead.)"""
    def attempt(function, fallback):
        try:
            return function()
        except Exception:
            return fallback
    return {
        "traffic": get_chokepoint_traffic(),
        "disasters": attempt(get_disasters, []),
        "prices": get_prices(),
        "air": attempt(lambda: get_air_traffic(AIR_HUBS, CONFLICT_ZONES), None),
        "sea_weather": attempt(lambda: get_weather(CHOKEPOINTS, marine=True), {}),
        "hub_weather": attempt(lambda: get_weather(AIR_HUBS), {}),
        "conflict_news": attempt(lambda: get_many_headlines({n: z["news"] for n, z in CONFLICT_ZONES.items()}), {}),
    }


def build_state(raw):
    """Turn raw feeds into everything the app and briefing need."""
    state = dict(raw)
    state["air_history"] = get_air_history()
    state["statuses"] = chokepoint_status(raw["traffic"])
    state["status_by_name"] = {s["Chokepoint"]: s for s in state["statuses"]}
    state["changes"] = price_changes(raw["prices"])
    state["conflict_info"] = {name: military_intensity(news) for name, news in raw["conflict_news"].items()}
    state["conflict_levels"] = {name: info[0] for name, info in state["conflict_info"].items()}
    state["events"] = build_events(state)
    return state


def build_events(state):
    """Every icon on the map. Shape = what it is (icon); colour = how severe (severity).
    Each event also lists the markets it affects (used for portfolio exposure)."""
    events = []
    air, air_history = state["air"], state["air_history"]

    def add(event_id, category, name, lat, lon, icon, severity, tooltip, impacts, since=None, rule=None):
        # since = the date the event began (if known); rule = its name in the track record (backtest)
        events.append({"id": event_id, "category": category, "name": name, "lat": lat, "lon": lon, "icon": icon,
                       "severity": severity, "colour": SEVERITY[severity]["colour"],
                       "pulse": severity == "Critical", "tooltip": f"{tooltip} · severity: {severity}",
                       "impacts": impacts, "since": since, "rule": rule})

    from explain import find_drop_start
    for s in state["statuses"]:
        cp = CHOKEPOINTS[s["Chokepoint"]]
        drop = None
        if s["Status"] in ("Disrupted", "Below normal"):
            daily = state["traffic"][state["traffic"]["chokepoint"] == s["Chokepoint"]].set_index("date")["ships"]
            smooth = daily.sort_index().rolling(7).mean().dropna()
            start = find_drop_start(smooth, smooth.iloc[:60].mean())
            drop = start.date().isoformat() if start is not None else None
        add(("chokepoint", s["Chokepoint"]), "Shipping", s["Chokepoint"], cp["lat"], cp["lon"], "fa-ship",
            chokepoint_severity(s),
            f"{s['Chokepoint'].upper()} · {s['Status']} · {s['Ships/day (last 7 days)']:.0f} ships/day",
            CHOKEPOINT_IMPACTS.get(s["Chokepoint"], []), since=drop, rule=f"Disruption at {s['Chokepoint']}")

    for name, hub in AIR_HUBS.items():
        status, count = air_hub_status(name, air, air_history)
        add(("hub", name), "Air cargo", name, hub["lat"], hub["lon"], "fa-plane",
            hub_severity(name, air, air_history, state["hub_weather"].get(name)),
            f"{name.upper()} · {count if count is not None else '?'} aircraft nearby · {status}",
            HUB_IMPACTS.get(name, []))

    for i, d in enumerate(state["disasters"]):
        region, impacts, _ = disaster_impacts(d)
        name = " ".join(d["name"].split())  # tidy double spaces from GDACS
        if len(name) > 60:  # e.g. droughts that list 29 countries
            name = f"{d['type']}: {region or 'multiple countries'}"
        if d["type"] in WEATHER_ICONS:
            add(("disaster", i), "Weather", name, d["lat"], d["lon"], WEATHER_ICONS[d["type"]],
                disaster_severity(d), f"{d['type'].upper()} · {safe(d['name'])} · {d['alert']} alert", impacts,
                since=d["started"], rule=f"{d['type']} in {region}")
        elif d["type"] in ("Earthquake", "Volcano"):
            add(("disaster", i), "Quakes & volcanoes", name, d["lat"], d["lon"],
                "fa-house-crack" if d["type"] == "Earthquake" else "fa-volcano", disaster_severity(d),
                f"{d['type'].upper()} · {safe(d['name'])} · {d['alert']} alert", impacts,
                since=d["started"], rule=f"{d['type']} in {region}")

    for kind, places, weather in (("chokepoint", CHOKEPOINTS, state["sea_weather"]),
                                  ("hub", AIR_HUBS, state["hub_weather"])):
        for name, place in places.items():
            flags = weather_flags(weather.get(name))
            if flags:
                add(("rough", (kind, name)), "Weather", f"Severe weather at {name}", place["lat"] + 2.2, place["lon"],
                    "fa-cloud-rain", rough_severity(weather.get(name)),
                    f"SEVERE WEATHER · {name.upper()} · {flags[0][0]} ({flags[0][1]})", [])

    for name, (level, count, fresh) in state["conflict_info"].items():
        if level != "Quiet":
            zone = CONFLICT_ZONES[name]
            add(("conflict", name), "Military", name, zone["lat"], zone["lon"], "fa-shield-halved",
                conflict_severity(level),
                f"{name.upper()} · {level} activity · {count} military headlines ({fresh} in 48h)",
                CONFLICT_IMPACTS.get(name, []))
    return events


def event_key(event):
    """A stable text ID for an event (used to spot NEW events and severity changes)."""
    kind, which = event["id"]
    if kind == "disaster":
        return f"disaster|{event['name']}"
    return f"{kind}|{which}"
