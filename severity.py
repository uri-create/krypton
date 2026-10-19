# severity.py
# One severity scale for every event in Krypton (map icon colours, alerts, briefings).

from explain_layers import air_hub_status, weather_flags

SEVERITY = {
    "Critical": {"colour": "#ff1744", "rank": 4, "meaning": "Major disruption with global knock-on effects"},
    "High":     {"colour": "#ff7a00", "rank": 3, "meaning": "Serious; clear regional or market effects"},
    "Moderate": {"colour": "#ffd600", "rank": 2, "meaning": "Worth watching; limited effects so far"},
    "Low":      {"colour": "#00e676", "rank": 1, "meaning": "Normal / minor"},
    "Info":     {"colour": "#607d8b", "rank": 0, "meaning": "Not enough data to judge"},
}


def rank(severity):
    return SEVERITY[severity]["rank"]


def chokepoint_severity(s):
    year = s["Change vs a year ago (%)"] or 0
    if s["Status"] == "Disrupted":
        return "Critical" if year <= -50 or s["Change vs 3 months (%)"] <= -50 else "High"
    if s["Status"] in ("Below normal", "Unusually busy"):
        return "Moderate"
    return "Low"


def hub_severity(name, air, air_history, weather):
    status, _ = air_hub_status(name, air, air_history)
    flags = [f[0] for f in weather_flags(weather)]
    if status == "Unusually quiet" or "Storm-force winds" in flags:
        return "High"
    if flags or status == "Unusually busy":
        return "Moderate"
    if status in ("No coverage", "No data"):
        return "Info"
    return "Low"


def conflict_severity(level):
    return {"High": "Critical", "Elevated": "High", "Low": "Moderate"}.get(level, "Info")


def disaster_severity(d):
    return "Critical" if d["alert"] == "Red" else "High"


def rough_severity(weather):
    flags = [f[0] for f in weather_flags(weather)]
    return "High" if ("Storm-force winds" in flags or "Very rough seas" in flags) else "Moderate"
