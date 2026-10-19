# analysis.py
# Turns raw numbers into statuses and a plain-English briefing.
# All simple, transparent rules, so you can always see WHY it says something.

from data_sources import CHOKEPOINTS

# How far traffic must move from normal before we flag it (in %)
DISRUPTED_BELOW = -25
LOW_BELOW = -10
BUSY_ABOVE = 25

STATUS_STYLE = {
    "Disrupted":      {"emoji": "🔴", "colour": "#ff3b3b",
                       "meaning": "25%+ fewer ships than 3 months or a year ago"},
    "Below normal":   {"emoji": "🟠", "colour": "#ffb000",
                       "meaning": "10–25% fewer ships than 3 months or a year ago"},
    "Normal":         {"emoji": "🟢", "colour": "#2ee59d", "meaning": "traffic close to usual levels"},
    "Unusually busy": {"emoji": "🔵", "colour": "#3fa9ff",
                       "meaning": "25%+ more ships than the last 3 months (often rerouting)"},
}


def chokepoint_status(traffic):
    """For each chokepoint, compare the last 7 days with two baselines:
      - the last 3 months  -> catches NEW problems
      - the same week a year ago -> catches LONG-RUNNING problems
        (if a strait has been blocked for months, the 3-month 'normal' is already low,
         so only the year-ago comparison shows how bad it really is)
    The status uses whichever comparison is worse."""
    results = []
    for name in CHOKEPOINTS:
        daily = traffic[traffic["chokepoint"] == name].set_index("date")["ships"].sort_index()
        if len(daily) < 100:
            continue
        last_week = float(daily.iloc[-7:].mean())
        three_months = float(daily.iloc[-97:-7].mean())
        year_ago = float(daily.iloc[-372:-365].mean()) if len(daily) >= 372 else None

        change_recent = (last_week / three_months - 1) * 100
        change_year = (last_week / year_ago - 1) * 100 if year_ago else None
        worst = min(change_recent, change_year) if change_year is not None else change_recent

        if worst <= DISRUPTED_BELOW:
            status = "Disrupted"
        elif worst <= LOW_BELOW:
            status = "Below normal"
        elif change_recent >= BUSY_ABOVE:
            status = "Unusually busy"
        else:
            status = "Normal"

        results.append({
            "Chokepoint": name,
            "Status": status,
            "Ships/day (last 7 days)": round(last_week, 1),
            "Ships/day (last 3 months)": round(three_months, 1),
            "Ships/day (a year ago)": round(year_ago, 1) if year_ago else None,
            "Change vs 3 months (%)": round(change_recent),
            "Change vs a year ago (%)": round(change_year) if change_year is not None else None,
            "Data up to": daily.index[-1].date(),
        })
    return results


def price_changes(prices):
    """% change of each market over 1 week, 1 month and 1 year."""
    changes = {}
    for market in prices.columns:
        series = prices[market].dropna()
        if series.empty:
            continue
        latest = series.iloc[-1]

        def change_since(days_back):
            if len(series) <= days_back:
                return None
            return (latest / series.iloc[-1 - days_back] - 1) * 100

        changes[market] = {
            "Price": latest,
            "1 week (%)": change_since(5),     # 5 trading days
            "1 month (%)": change_since(21),   # ~21 trading days
            "1 year (%)": change_since(len(series) - 1),
        }
    return changes


def describe_move(value):
    """'up 12%' / 'down 3%' / 'flat'."""
    if value is None:
        return "no data"
    if abs(value) < 1:
        return "flat"
    return f"{'up' if value > 0 else 'down'} {abs(value):.0f}%"


def build_briefing(statuses, changes, disasters):
    """The plain-English summary at the top of the dashboard: what's happening and what to watch."""
    lines = []

    # 1. Shipping problems first (the most important signals)
    problems = [s for s in statuses if s["Status"] in ("Disrupted", "Below normal")]
    problems.sort(key=lambda s: min(s["Change vs 3 months (%)"], s["Change vs a year ago (%)"] or 0))
    for s in problems:
        info = CHOKEPOINTS[s["Chokepoint"]]
        style = STATUS_STYLE[s["Status"]]
        traffic_text = f"{s['Ships/day (last 7 days)']:.0f} ships/day this week"
        if s["Ships/day (a year ago)"]:
            traffic_text += (f" vs {s['Ships/day (a year ago)']:.0f} a year ago "
                             f"({s['Change vs a year ago (%)']:+d}%)")
        traffic_text += (f" and {s['Ships/day (last 3 months)']:.0f} over the last 3 months "
                         f"({s['Change vs 3 months (%)']:+d}%)")
        # Long-running = it was already low before this week
        if (s["Change vs a year ago (%)"] or 0) <= DISRUPTED_BELOW and s["Change vs 3 months (%)"] > DISRUPTED_BELOW:
            traffic_text += ". This is a long-running disruption, not a new one"
        market_bits = [f"{m} is {describe_move(changes[m]['1 month (%)'])} this month "
                       f"and {describe_move(changes[m]['1 year (%)'])} over the year"
                       for m in info["markets"] if m in changes]
        lines.append(
            f"{style['emoji']} **{s['Chokepoint']}: {s['Status'].lower()}.** {traffic_text}. {info['why']} "
            + (f"Related markets: {'; '.join(market_bits)}." if market_bits else "")
        )

    # 2. Rerouting signal: Cape of Good Hope busy while Red Sea is quiet
    by_name = {s["Chokepoint"]: s for s in statuses}
    cape, bab = by_name.get("Cape of Good Hope"), by_name.get("Bab el-Mandeb Strait")
    if cape and bab and cape["Change vs 3 months (%)"] > 10 and bab["Change vs 3 months (%)"] < -10:
        lines.append(
            "🔄 **Ships appear to be rerouting around Africa.** Traffic at the Cape of Good Hope is "
            f"{cape['Change vs 3 months (%)']:+d}% while the Red Sea entrance is {bab['Change vs 3 months (%)']:+d}%. "
            "The trip around Africa adds roughly 10–14 days, which tends to raise shipping costs."
        )

    busy = [s for s in statuses if s["Status"] == "Unusually busy" and s["Chokepoint"] != "Cape of Good Hope"]
    for s in busy:
        lines.append(f"🔵 **{s['Chokepoint']} is unusually busy** ({s['Change vs 3 months (%)']:+d}% vs 3 months). "
                     "This can mean ships are diverting here from another route.")

    if not problems and not busy:
        lines.append("🟢 **All watched shipping chokepoints are running normally.**")

    # 3. Biggest market moves this month
    moves = [(m, c["1 month (%)"]) for m, c in changes.items() if c["1 month (%)"] is not None]
    moves.sort(key=lambda m: abs(m[1]), reverse=True)
    if moves:
        top = ", ".join(f"**{m}** {describe_move(v)}" for m, v in moves[:3])
        lines.append(f"📈 **Biggest market moves this month:** {top}.")

    # 4. Serious disasters
    red = [d for d in disasters if d["alert"] == "Red"]
    if red:
        names = "; ".join(f"{d['name']} ({d['country'][:60]})" for d in red[:3])
        lines.append(f"🌪️ **Red disaster alerts:** {names}.")

    return lines
