# panels.py
# The click-panel: a tidy, tabbed report for whatever icon you clicked on the map.
#
#   📊 Overview      bottom line, key numbers, a single-line chart and pie charts, what to watch
#   ❓ Why           measured causes, what the news says, background, chain of events, confidence
#   📈 Markets       researched winners/losers grouped by SECTOR, checked against real price moves
#   📰 News          the latest headlines
#   🔬 Deep research AI web research on this exact event (needs an API key)
#
# Also defines the SEVERITY scale that colours every icon on the map.

import datetime as dt
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import STATUS_STYLE, describe_move
from climate import measured_causes
from data_sources import CHOKEPOINTS, get_air_series
from deep_research import api_key_available, load_saved, run_research
from explain import classify_causes, explain_chokepoint
from explain_layers import (air_hub_status, describe_weather, military_intensity, weather_flags)
from impact import (CHOKEPOINT_IMPACTS, CONFLICT_IMPACTS, HUB_IMPACTS, TECTONICS, check_direction,
                    disaster_impacts, find_region)
from layers import AIR_HUBS, CONFLICT_ZONES, SEA_ROUTES
from markets import SECTOR_OF, SECTORS

from severity import (SEVERITY, chokepoint_severity, conflict_severity, disaster_severity,  # noqa: F401
                      hub_severity, rough_severity)

GRID, CYAN = "#2a1216", "#ff4d5e"   # Krypton palette (red accent)


# ===========================================================================
# SHARED BUILDING BLOCKS
# ===========================================================================
def header(title, kind_label, severity):
    colour = SEVERITY[severity]["colour"]
    st.markdown(
        f"<div class='panel-title'>{html.escape(str(title))}</div>"  # titles can come from outside data
        f"<span class='badge' style='color:{colour};border-color:{colour};box-shadow:0 0 8px {colour}55'>"
        f"{kind_label} · severity: {severity}</span>", unsafe_allow_html=True)


def subtitle(text):
    st.markdown(f"<div class='section'>{text}</div>", unsafe_allow_html=True)


def bottom_line(text, severity):
    box = {"Critical": st.error, "High": st.warning, "Moderate": st.warning, "Low": st.success, "Info": st.info}
    box[severity](f"**Bottom line:** {text}")


def bullets(items):
    st.markdown("\n".join(f"- {item}" for item in items) if items else "_Nothing to report._")


def chart_key(prefix):
    """Streamlit needs every chart to have its own ID. A counter (reset at the top of app.py on
    every run) gives each chart a unique, stable one."""
    st.session_state["_chart_n"] = st.session_state.get("_chart_n", 0) + 1
    return f"{prefix}_{st.session_state['_chart_n']}"


def line_chart(series, title, y_label, colour=CYAN, marker=None, marker_label=None, bars=False, height=230):
    """A clean single-line (or single-bar) chart with a clear title."""
    series = series.dropna()
    if series.empty:
        st.caption(f"{title}: no data yet.")
        return
    figure = go.Figure()
    if bars:
        figure.add_trace(go.Bar(x=series.index, y=series.values, marker_color=colour))
    else:
        figure.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", line=dict(color=colour, width=2.5)))
    if marker is not None:
        figure.add_vline(x=pd.Timestamp(marker).timestamp() * 1000, line_dash="dash", line_color="#ff1744",
                         annotation_text=marker_label or "", annotation_font_color="#ff8a80")
    figure.update_layout(
        title=dict(text=title, font=dict(size=13, color="#c9c9d1")), template="plotly_dark", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#050203", showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10), font=dict(family="Inter, sans-serif", color="#8a8a96"),
        xaxis=dict(gridcolor=GRID), yaxis=dict(title=y_label, gridcolor=GRID),
    )
    st.plotly_chart(figure, width="stretch", key=chart_key("line"))


PIE_COLOURS = ["#ff2a3d", "#ffb000", "#4da3ff", "#3ddc84", "#c77dff", "#ff7aa2", "#00d1c1", "#d4a017", "#9a9aa4"]


def pie_chart(labels, values, title, height=330, colours=None, note=None):
    pairs = [(label, value) for label, value in zip(labels, values) if value and value > 0]
    if not pairs:
        st.caption(f"{title}: no data.")
        return
    keep = [i for i, (l, v) in enumerate(zip(labels, values)) if v and v > 0]
    palette = [colours[i] for i in keep] if colours else PIE_COLOURS[:len(pairs)]
    labels, values = zip(*pairs)
    figure = go.Figure(go.Pie(labels=labels, values=values, hole=0.55, sort=False,
                              marker=dict(colors=palette, line=dict(color="#020203", width=2)),
                              # whole-number percentages on the slices (e.g. "62%"), no long decimals
                              texttemplate="%{percent:.0%}", textfont=dict(size=13, color="#020203"),
                              hovertemplate="%{label}: %{percent:.0%}<extra></extra>"))
    figure.update_layout(title=dict(text=title, font=dict(size=13, color="#c9c9d1")), template="plotly_dark",
                         height=height, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10),
                         legend=dict(font=dict(size=11), orientation="h", x=0, y=-0.05, yanchor="top"),
                         font=dict(family="Inter, sans-serif"))
    st.plotly_chart(figure, width="stretch", key=chart_key("pie"))
    if note:
        st.caption(note)


def news_bullets(headlines, limit=10):
    if not headlines:
        st.caption("No recent headlines found.")
        return
    st.markdown("\n".join(
        f"- [{h['title'].replace('[', '(').replace(']', ')')}]({h['link']}) · *{h['date']}*"
        for h in headlines[:limit]))


def news_themes(headlines):
    """Cause themes in the news, as a pie plus evidence headlines."""
    causes = classify_causes(headlines)
    if not causes:
        st.caption("No clear theme in the latest headlines.")
        return causes
    pie_chart([c for c, _ in causes], [len(e) for _, e in causes], "What the latest headlines are about")
    for cause, evidence in causes[:3]:
        st.markdown(f"**{cause}** ({len(evidence)} of {len(headlines)} headlines), for example:")
        news_bullets(evidence, 3)
    return causes


def confidence_note(causes, headlines, measured=True):
    if not causes:
        level, why = "Low", "the news doesn't point clearly to one cause"
    else:
        share = len(causes[0][1]) / max(len(headlines), 1)
        level = "High" if share >= 0.6 else "Medium" if share >= 0.3 else "Low"
        why = f"{len(causes[0][1])} of {len(headlines)} recent headlines point to the same cause"
    st.markdown(f"- **Measured numbers** (ships, aircraft, weather, prices): reliable, straight from the data sources."
                if measured else "")
    st.markdown(f"- **Cause:** confidence **{level}**, because {why}. For a fully researched, sourced explanation, "
                "use the 🔬 Deep research tab.")


def price_move_since(prices, market, since):
    series = prices[market].dropna() if market in prices else pd.Series(dtype=float)
    if series.empty:
        return None
    before = series[series.index <= pd.Timestamp(since)] if since is not None else series.iloc[-22:-21]
    if before.empty:
        return None
    return (series.iloc[-1] / before.iloc[-1] - 1) * 100


IMPACT_SIZES = [  # (how many times bigger than normal, label, colour, plain meaning)
    (2.0, "BIG", "#ff2a3d", "more than 2× its normal swing"),
    (1.0, "MEDIUM", "#ffb000", "bigger than its normal swing"),
    (0.0, "SMALL", "#9a9aa4", "within its normal ups and downs"),
]


def impact_size(prices, market, since, move):
    """How unusual a move is. We compare it with how much this market NORMALLY moved over the
    same number of days BEFORE the event (its typical daily swing × √days).
    Returns (label, colour, times-normal) or (None, None, None)."""
    if move is None or market not in prices:
        return None, None, None
    series = prices[market].dropna()
    if len(series) < 60:
        return None, None, None
    days = int((series.index >= pd.Timestamp(since)).sum()) if since is not None else 21
    # "Normal" must be measured BEFORE the event, otherwise the event's own swings make itself look normal
    before = series[series.index < pd.Timestamp(since)] if since is not None else series.iloc[:-days]
    daily = before.pct_change().dropna().iloc[-252:]
    if len(daily) < 40:  # not enough history before the event to judge
        return None, None, None
    normal = daily.std() * max(days, 1) ** 0.5 * 100
    ratio = abs(move) / normal if normal > 0 else 0.0
    for limit, label, colour, _ in IMPACT_SIZES:
        if ratio >= limit:
            return label, colour, ratio
    return None, None, None


def render_impacts(impacts, prices, changes, since=None, since_label="this month", note=None):
    """The Markets tab: STOCKS AFFECTED (measured), two clear pie charts, then the research notes."""
    if note:
        st.info(note)
    if not impacts:
        st.caption("No specific market links researched for this event.")
        return

    # ---------- STOCKS AFFECTED ----------
    subtitle("📉 Stocks affected")
    rows = []
    for market, direction, why in impacts:
        move = price_move_since(prices, market, since) if since is not None else \
            (changes.get(market) or {}).get("1 month (%)")
        size, colour, ratio = impact_size(prices, market, since, move)
        rows.append((market, direction, move, size, colour, ratio or 0))
    rows.sort(key=lambda r: -r[5])

    period = f"since the event began on {pd.Timestamp(since):%d %b %Y}" if since is not None else "over the last month"
    st.caption(f"Real price moves {period}, biggest impact first.")
    table = ["<table style='width:100%;border-collapse:collapse;font-size:0.82rem'>",
             "<tr style='color:#77777f;text-align:left;border-bottom:1px solid #2a1216'>"
             "<th>Stock</th><th>Moved</th><th>Impact</th><th>Expected</th></tr>"]
    for market, direction, move, size, colour, ratio in rows:
        move_html = (f"<span style='color:{'#3ddc84' if move >= 0 else '#ff2a3d'};font-weight:800'>"
                     f"{'▲' if move >= 0 else '▼'} {abs(move):.1f}%</span>") if move is not None else "n/a"
        size_html = (f"<span style='color:{colour};border:1px solid {colour};padding:0 6px;font-size:0.72rem'>"
                     f"{size}</span>") if size else "—"
        expected = {"▲": "to rise", "▼": "to fall", "◆": "either way"}[direction]
        match = check_direction(direction, move)
        match_html = {"✔": " <span style='color:#3ddc84'>✔ matched</span>",
                      "✖": " <span style='color:#ff2a3d'>✖ opposite</span>"}.get(match, "")
        table.append(f"<tr style='border-bottom:1px solid #160a0c'><td style='padding:5px 0'><b>{market}</b></td>"
                     f"<td>{move_html}</td><td>{size_html}</td><td>{direction} {expected}{match_html}</td></tr>")
    table.append("</table>")
    st.markdown("".join(table), unsafe_allow_html=True)
    st.caption("**Impact** = how big the move is compared with that stock's NORMAL ups and downs (measured before "
               "the event) over the same number of days. BIG = more than 2× normal, MEDIUM = more than normal, "
               "SMALL = a normal-sized move. "
               "These are real price moves; they show what happened, not proof this event caused it.")

    # ---------- TWO CLEAR PIE CHARTS ----------
    by_sector = {}
    for market, direction, why in impacts:
        by_sector.setdefault(SECTOR_OF.get(market, "Other"), []).append((market, direction, why))
    # Stacked (not side by side), so each chart and its key stay readable in the narrow panel
    labels = [f"{s.split(' ', 1)[-1]} ({len(v)})" for s, v in by_sector.items()]
    pie_chart(labels, [len(v) for v in by_sector.values()], "Which industries it touches",
              note="Each colour is an industry. The number = how many of its stocks are listed above.")
    counts = {"Expected to rise": sum(1 for _, d, _ in impacts if d == "▲"),
              "Expected to fall": sum(1 for _, d, _ in impacts if d == "▼"),
              "Could go either way": sum(1 for _, d, _ in impacts if d == "◆")}
    pie_chart([f"{k} ({v})" for k, v in counts.items()], list(counts.values()), "What the research expects",
              colours=["#3ddc84", "#ff2a3d", "#9a9aa4"],
              note="Green = stocks expected to go up, red = down, grey = could go either way.")

    # ---------- WHY EACH ONE IS LINKED (folded away) ----------
    with st.expander("📚 Why each stock is linked (research notes)"):
        for sector in [s for s in SECTORS if s in by_sector] + [s for s in by_sector if s not in SECTORS]:
            st.markdown(f"**{sector}**")
            st.markdown("\n".join(f"- {d} **{m}**: {why}" for m, d, why in by_sector[sector]))

    subtitle("📈 Price chart")
    choice = st.selectbox("Show a stock's price over the last 12 months", [m for m, _, _ in impacts],
                          key=f"impact_chart_{since}_{impacts[0][0]}")
    if choice in prices:
        line_chart(prices[choice], f"{choice}: daily price, last 12 months", "Price",
                   marker=since, marker_label="event start" if since is not None else None)


def track_record_note(rule):
    """Show how this exact rule performed historically (from the backtest), honestly."""
    from backtest import load_results, summarise
    results = load_results()
    if not results:
        st.caption("📊 Track record: not calculated yet (see the 📊 Track record tab).")
        return
    _, by_rule, _ = summarise(results)
    if by_rule is None or rule not in by_rule.index:
        st.caption("ℹ️ There are no past events like this one to check these arrows against.")
        return
    row = by_rule.loc[rule]
    n, hit, base = int(row["predictions"]), row["hit_rate"], row["base_rate"]
    past_events = len({(p["event"], p["date"]) for p in results["predictions"] if p["rule"] == rule})
    luck = 1.96 * (base * (1 - base) / n) ** 0.5 if n else 1
    right, coin = round(hit * 100), round(base * 100)
    if past_events < 5:
        st.info(f"ℹ️ Only {past_events} past event{'s' if past_events != 1 else ''} like this, too few to know "
                "if these arrows work.")
    elif hit - base > luck:
        st.success(f"✅ In past events like this, these arrows were right **{right} times out of 100** "
                   f"(guessing: {coin}). Better than guessing, but still not a sure thing.")
    else:
        st.warning(f"⚠️ **Heads-up:** in past events like this, these arrows were right **{right} times out of 100**. "
                   f"Just guessing gets about {coin}. Don't use them to predict prices.")


def render_deep_research(event_key, description):
    st.markdown("**AI deep research** searches the web about this exact event and writes a specific, "
                "sourced analysis: real causes, what led to it, and named companies it affects.")
    saved = load_saved(event_key)  # saved research isn't personal, so everyone can read it
    user = st.session_state.get("user") or {}
    from billing import add_cost, ai_access, locked_message
    allowed, reason = ai_access(user) if user else (False, "locked")
    if not allowed:
        locked_message(user, reason, f"research_{event_key}",
                       "🔄 Refresh research" if saved else "🔬 Run deep research")
    elif not api_key_available():
        st.caption("AI research is unavailable right now. Please try again later.")
    else:
        label = "🔄 Refresh research" if saved else "🔬 Run deep research"
        if st.button(label, key=f"research_{event_key}"):
            with st.spinner("Researching (searching the web, usually 30–90 seconds)..."):
                try:
                    saved = run_research(event_key, description)
                    add_cost(user, saved.get("cost"))
                except Exception as error:
                    st.error(f"Research failed: {error}")
    if saved:
        st.caption(f"Researched {saved['date']}")
        st.markdown(saved["text"])
        if saved["sources"]:
            subtitle("Sources")
            st.markdown("\n".join(f"- [{s['title']}]({s['url']})" for s in saved["sources"][:15]))


# ===========================================================================
# 🚢 SHIPPING CHOKEPOINT
# ===========================================================================
def render_chokepoint(name, s, traffic, prices, changes, headlines, disasters, weather):
    info = CHOKEPOINTS[name]
    severity = chokepoint_severity(s)
    header(name, "🚢 Shipping chokepoint", severity)
    sections = dict(explain_chokepoint(name, s, traffic, prices, changes, headlines, disasters))
    daily = traffic[traffic["chokepoint"] == name].set_index("date").sort_index()
    smooth = daily["ships"].rolling(7).mean().dropna()

    from explain import find_drop_start
    drop = find_drop_start(smooth, smooth.iloc[:60].mean()) if s["Status"] in ("Disrupted", "Below normal") else None
    causes = classify_causes(headlines)
    cause = causes[0][0].lower() if causes else "no single clear cause in the news"
    routes = [r for r, r_info in SEA_ROUTES.items() if name in r_info["chokepoints"]]

    tabs = st.tabs(["📊 Overview", "❓ Why", "📈 Markets", "📰 News", "🔬 Deep research"])

    with tabs[0]:
        if s["Status"] == "Disrupted":
            text = (f"traffic is **{abs(s['Change vs a year ago (%)'] or s['Change vs 3 months (%)'])}% below** normal"
                    + (f" since **{drop:%d %b %Y}**" if drop is not None else "") + f". Likely cause: {cause}.")
        elif s["Status"] == "Below normal":
            text = f"traffic is running below normal. Likely cause: {cause}. Not a crisis yet."
        elif s["Status"] == "Unusually busy":
            text = "traffic is unusually high; ships may be diverting here from a riskier route."
        else:
            text = "ships are passing normally."
        bottom_line(f"{name}: {text}", severity)

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        c1.metric("Ships/day (this week)", f"{s['Ships/day (last 7 days)']:.0f}",
                  f"{s['Change vs a year ago (%)']:+d}% vs year ago" if s["Change vs a year ago (%)"] is not None else None)
        c2.metric("Last 3 months avg", f"{s['Ships/day (last 3 months)']:.0f}")
        c3.metric("A year ago", f"{s['Ships/day (a year ago)']:.0f}" if s["Ships/day (a year ago)"] else "n/a")
        c4.metric("Drop began", f"{drop:%d %b %Y}" if drop is not None else "No drop")

        line_chart(smooth, f"Ships passing through {name} per day (7-day average)", "Ships per day",
                   marker=drop, marker_label="drop began")

        kinds = ["tankers", "container ships", "bulk carriers"]
        p1, p2 = st.columns(2)
        with p1:
            pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-7:].mean().values), "Ship types: this week")
        with p2:
            if len(daily) >= 372:
                pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-372:-365].mean().values),
                          "Ship types: a year ago")

        subtitle("🌦️ Weather & sea right now")
        st.markdown(describe_weather(weather))

        subtitle("👀 What to watch next")
        watch = []
        if s["Status"] in ("Disrupted", "Below normal"):
            watch.append(f"Whether ships/day climbs back toward the year-ago level of {s['Ships/day (a year ago)'] or 0:.0f}.")
            watch.append("Insurance 'war-risk' premiums and naval escort announcements (signs of recovery or escalation).")
        for r in routes:
            watch.append(f"Traffic on the **{r}** route.")
        if "Cape of Good Hope" != name and routes:
            watch.append("Cape of Good Hope traffic: a rise there means ships are taking the long way around Africa.")
        bullets(watch)

    with tabs[1]:
        subtitle("📏 Measured: what the data shows")
        st.markdown(sections.get("📊 What's happening", ""))
        subtitle("📰 What the news says")
        causes = news_themes(headlines)
        subtitle("🔗 Chain of events")
        if s["Status"] in ("Disrupted", "Below normal"):
            chain = [f"**Trigger:** {cause}" + (f", with traffic falling from {drop:%d %b %Y}" if drop is not None else "") + ".",
                     f"**Ships react:** daily transits fall to {s['Ships/day (last 7 days)']:.0f}/day "
                     f"(from {s['Ships/day (a year ago)'] or s['Ships/day (last 3 months)']:.0f} a year ago).",
                     "**Trade reroutes:** cargo waits, takes longer routes, or stops.",
                     "**Costs rise:** longer voyages, higher insurance and fewer available ships push freight rates up.",
                     "**Markets react:** see the 📈 Markets tab for the specific winners and losers."]
            st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(chain, 1)))
        else:
            st.markdown("No disruption to explain: traffic is close to normal.")
        subtitle("🌍 Why this place matters")
        st.markdown(info["why"])
        if routes:
            st.markdown("\n".join(f"- **{r}:** {SEA_ROUTES[r]['carries']}" for r in routes))
        subtitle("🎯 How sure is this?")
        confidence_note(causes, headlines)

    with tabs[2]:
        track_record_note(f"Disruption at {name}")
        render_impacts(CHOKEPOINT_IMPACTS.get(name, []), prices, changes, since=drop,
                       since_label=f"since the drop began ({drop:%d %b %Y})" if drop is not None else "over the last month")
    with tabs[3]:
        news_bullets(headlines, 15)
    with tabs[4]:
        render_deep_research(f"chokepoint|{name}|{dt.date.today():%Y-%m}",
                             f"Shipping disruption at the {name}. Ship traffic this week: {s['Ships/day (last 7 days)']:.0f} "
                             f"per day vs {s['Ships/day (a year ago)']} a year ago. "
                             + (f"Traffic began falling around {drop:%d %B %Y}. " if drop is not None else "")
                             + f"Headlines suggest: {cause}. Explain the specific causes, background and market effects.")


# ===========================================================================
# ✈️ AIR CARGO HUB
# ===========================================================================
def render_hub(name, air, air_history, weather, headlines, prices, changes, conflict_levels):
    hub = AIR_HUBS[name]
    severity = hub_severity(name, air, air_history, weather)
    status, count = air_hub_status(name, air, air_history)
    header(name, "✈️ Air cargo hub", severity)
    flags = weather_flags(weather)
    from explain import distance_km
    nearby = [c for c, z in CONFLICT_ZONES.items()
              if distance_km(hub["lat"], hub["lon"], z["lat"], z["lon"]) < 1500
              and conflict_levels.get(c) in ("High", "Elevated")]
    causes = classify_causes(headlines)

    tabs = st.tabs(["📊 Overview", "❓ Why", "📈 Markets", "📰 News", "🔬 Deep research"])
    with tabs[0]:
        if status == "No coverage":
            text = "live tracking can't see this airport (receiver gaps), so judge it from news and weather."
        elif status == "Unusually quiet":
            text = "air traffic is well below its usual level."
        elif flags:
            text = f"operating, but **{flags[0][0].lower()}** ({flags[0][1]}) could cause delays."
        elif nearby:
            text = f"operating normally, but close to an active conflict ({', '.join(nearby)})."
        else:
            text = "operating normally."
        bottom_line(f"{name}: {text}", severity)

        past = air_history.get(name)
        ground = (air or {}).get("counts", {}).get(name, {}).get("on_ground")
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        c1.metric("Aircraft nearby now", count if count is not None else "n/a")
        c2.metric("Usual (avg of snapshots)", f"{past['average']:.0f}" if past else "learning")
        c3.metric("On the ground", ground if ground is not None else "n/a")
        c4.metric("Wind gusts", f"{weather['gusts']:.0f} km/h" if weather and weather.get("gusts") is not None else "n/a")

        line_chart(get_air_series(name), f"Aircraft within 150 km of {name} (each saved snapshot)", "Aircraft",
                   height=210)
        st.caption("A new snapshot is saved each time Krypton refreshes (about every 15 minutes while open).")

        subtitle("🌍 What this hub is")
        st.markdown(hub["role"])
        subtitle("👀 What to watch next")
        watch = ["Whether aircraft counts stay near their usual level."]
        if flags:
            watch.append("When the bad weather clears (check the weather in the Why tab).")
        for c in nearby:
            watch.append(f"Airspace closures linked to **{c}**.")
        bullets(watch)

    with tabs[1]:
        subtitle("🌦️ Weather right now")
        st.markdown(describe_weather(weather))
        subtitle("🛡️ Nearby conflicts")
        bullets([f"**{c}**: {conflict_levels[c].lower()} activity, within 1,500 km. Airlines may reroute around "
                 "closed airspace, adding flight time and fuel cost." for c in nearby] or
                ["No active conflicts within 1,500 km."])
        subtitle("📰 What the news says")
        causes = news_themes(headlines)
        subtitle("🎯 How sure is this?")
        confidence_note(causes, headlines)
        st.caption("Aircraft counts include passenger planes; live data can't always separate cargo flights.")

    with tabs[2]:
        render_impacts(HUB_IMPACTS.get(name, []) +
                       [(m, "◆", "Linked market for this hub.") for m in hub["markets"]
                        if m not in [x[0] for x in HUB_IMPACTS.get(name, [])]],
                       prices, changes, since_label="over the last month")
    with tabs[3]:
        news_bullets(headlines, 15)
    with tabs[4]:
        render_deep_research(f"hub|{name}|{dt.date.today():%Y-%m-%d}",
                             f"The air cargo hub {name}. Role: {hub['role']} Current aircraft nearby: {count}. "
                             f"Weather: {describe_weather(weather)}. Explain current operations, any disruptions, and "
                             "what affects cargo volumes here right now, with market effects.")


# ===========================================================================
# 🛡️ CONFLICT ZONE
# ===========================================================================
def render_conflict(name, headlines, air, air_history, statuses, prices, changes):
    zone = CONFLICT_ZONES[name]
    level, military, fresh = military_intensity(headlines)
    severity = conflict_severity(level)
    header(name, "🛡️ Military activity", severity)
    causes = classify_causes(headlines)

    tabs = st.tabs(["📊 Overview", "❓ Why", "📈 Markets", "📰 News", "🔬 Deep research"])
    with tabs[0]:
        text = {"High": "very active right now, with frequent fresh reports of military action.",
                "Elevated": "ongoing military activity in the news, below peak intensity.",
                "Low": "only occasional military news recently."}.get(level, "quiet in recent news.")
        bottom_line(f"{name}: {text}", severity)

        count = (air or {}).get("counts", {}).get(name, {}).get("airborne")
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        c1.metric("Activity level", level)
        c2.metric("Military headlines", f"{military} of {len(headlines)}")
        c3.metric("In last 48 hours", fresh)
        c4.metric("Aircraft overhead now", count if count is not None else "n/a")

        dated = pd.Series([h["published"] for h in headlines if h.get("published")])
        if not dated.empty:
            per_day = dated.dt.tz_convert(None).dt.floor("D").value_counts().sort_index()
            line_chart(per_day, "Headlines about this conflict per day (latest 15)", "Headlines", bars=True,
                       colour="#ff1744", height=210)
        line_chart(get_air_series(name), "Aircraft flying over the area (each saved snapshot)", "Aircraft",
                   height=200)

        subtitle("👀 What to watch next")
        bullets([
            "Whether the number of fresh (48-hour) military headlines rises or falls.",
            "Aircraft over the area: a sharp drop can mean closed airspace or a new escalation.",
            "Nearby shipping chokepoints and cargo hubs (Markets and Why tabs).",
        ])

    with tabs[1]:
        subtitle("📜 Background: what led to this")
        st.markdown(zone["background"])
        subtitle("🗞️ Latest developments (newest first)")
        ordered = sorted([h for h in headlines if h.get("published")], key=lambda h: h["published"], reverse=True)
        news_bullets(ordered, 6)
        subtitle("📰 Themes in the news")
        causes = news_themes(headlines)
        subtitle("🌍 What's nearby")
        from explain import distance_km
        near = []
        for s in statuses:
            cp = CHOKEPOINTS[s["Chokepoint"]]
            km = distance_km(zone["lat"], zone["lon"], cp["lat"], cp["lon"])
            if km < 2000:
                near.append(f"🚢 **{s['Chokepoint']}**, {km:,.0f} km away: "
                            f"{STATUS_STYLE[s['Status']]['emoji']} {s['Status'].lower()}")
        for hub_name, hub in AIR_HUBS.items():
            km = distance_km(zone["lat"], zone["lon"], hub["lat"], hub["lon"])
            if km < 1500:
                near.append(f"✈️ **{hub_name}** cargo hub, {km:,.0f} km away")
        bullets(near or ["No major chokepoints or cargo hubs nearby."])
        subtitle("🎯 How sure is this?")
        confidence_note(causes, headlines)

    with tabs[2]:
        render_impacts(CONFLICT_IMPACTS.get(name, []), prices, changes, since_label="over the last month")
    with tabs[3]:
        news_bullets(headlines, 15)
    with tabs[4]:
        render_deep_research(f"conflict|{name}|{dt.date.today():%Y-%m-%d}",
                             f"The conflict: {name}. Background: {zone['background']} Recent activity level from news: "
                             f"{level}. Explain the specific latest developments, what led to them, and the market effects.")


# ===========================================================================
# ☁️🌋 DISASTERS (GDACS)
# ===========================================================================
HAZARD_BASICS = {
    "Cyclone": "Tropical cyclones (hurricanes/typhoons) draw energy from warm ocean water.",
    "Drought": "A drought is a long shortage of water compared with what an area normally gets.",
    "Flood": "Floods happen when more water arrives than rivers, drains and soil can carry away.",
    "Wildfire": "Wildfires need dry fuel, heat and wind.",
    "Earthquake": "Earthquakes release stress built up where tectonic plates push, pull or grind past each other.",
    "Volcano": "Volcanoes erupt where molten rock (magma) reaches the surface, usually above sinking plates or hotspots.",
}


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_causes(d):
    """35 years of climate records for a disaster: downloaded once, then kept for 6 hours."""
    return measured_causes(d)


def render_disaster(d, prices, changes, headlines):
    severity = disaster_severity(d)
    icon = "🌋" if d["type"] in ("Earthquake", "Volcano") else "☁️"
    region, impacts, specific = disaster_impacts(d)
    countries = {c.strip() for c in d["country"].split(",") if c.strip()}
    title = d["name"] if len(d["name"]) <= 60 else f"{d['type']}: {region or 'multiple countries'} ({len(countries)} countries)"
    header(title, f"{icon} {d['type']} · {d['alert']} alert", severity)
    with st.spinner("Checking 35 years of climate records..."):
        causes_measured, chart = cached_causes(d)

    tabs = st.tabs(["📊 Overview", "❓ Why", "📈 Markets", "📰 News", "🔬 Deep research"])
    with tabs[0]:
        effect = ("expect real damage and disruption for days or weeks" if d["alert"] == "Red"
                  else "local disruption likely; global markets react only if it hits key ports, crops, mines or factories")
        bottom_line(f"{d['type']} in {region or d['country'][:60]}: {effect}.", severity)
        c1, c2 = st.columns(2)
        c3, _ = st.columns(2)
        c1.metric("Alert", d["alert"])
        c2.metric("Started", d["started"])
        c3.metric("Region", region or "Other")
        if d["severity"]:
            st.markdown(f"**Measured strength:** {d['severity']}")
        st.markdown(f"**Where:** {d['country'][:400]}")
        if chart is not None and not chart.empty:
            line_chart(chart, "Rain each month at the event's centre, % of normal (100% = normal)", "% of normal",
                       colour="#3fa9ff", bars=True)
        subtitle("👀 What to watch next")
        watch = {"Cyclone": ["The storm's forecast track: which coasts, ports and cities it heads toward.",
                             "Wind speed: weakening over cooler water or land, or strengthening over warm water."],
                 "Drought": ["Rainfall over the coming weeks vs normal.", "River and reservoir levels; harvest estimates."],
                 "Flood": ["River levels downstream.", "Damage reports for farms, factories and transport."],
                 "Wildfire": ["Wind forecasts and containment percentage.", "Evacuations near towns and power lines."],
                 "Earthquake": ["Aftershocks (common for days to weeks).", "Damage reports for ports, factories and power."],
                 "Volcano": ["Alert level changes from the local volcano agency.", "Ash clouds affecting flights."]}
        bullets(watch.get(d["type"], []))

    with tabs[1]:
        subtitle("📏 Measured causes (from real data)")
        if causes_measured:
            st.markdown("\n".join(causes_measured))
        if d["type"] in ("Earthquake", "Volcano"):
            region_name = find_region(d["lat"], d["lon"])
            st.markdown(f"**Why here (plate tectonics):** {TECTONICS.get(region_name, 'This location is not in our tectonics table yet; check USGS for the local fault.')}")
            if d["severity"]:
                st.markdown(f"**Measured strength:** {d['severity']}. Shallow quakes (under ~70 km deep) shake the "
                            "surface much harder than deep ones of the same magnitude.")
        subtitle("📰 What the news says")
        causes = news_themes(headlines)
        subtitle("📚 How this kind of event works (short)")
        st.markdown(HAZARD_BASICS.get(d["type"], ""))
        subtitle("🎯 How sure is this?")
        st.markdown("- **Measured causes** come from climate records, live sea temperature or plate maps: reliable "
                    "for the centre point of the event.\n- Human factors (water use, land management, building quality) "
                    "aren't in free live data; use 🔬 Deep research for those.")

    with tabs[2]:
        if specific:
            track_record_note(f"{d['type']} in {region}")
        note = (f"Researched effects for a **{d['type'].lower()} in {region}**." if specific else
                f"No region-specific research for a {d['type'].lower()} in {region or 'this area'} yet: showing "
                "**general** effects only. Use 🔬 Deep research for this exact event.")
        render_impacts(impacts, prices, changes, since=d["started"],
                       since_label=f"since the event began ({d['started']})", note=note)
    with tabs[3]:
        news_bullets(headlines, 15)
    with tabs[4]:
        render_deep_research(f"disaster|{d['name']}|{d['started']}",
                             f"{d['name']} ({d['type']}), {d['alert']} alert since {d['started']}, affecting "
                             f"{d['country'][:300]}. Strength: {d['severity']}. Measured climate data: "
                             f"{' '.join(causes_measured)[:1200]}. Explain the specific causes (including human factors "
                             "such as water use or land use if relevant), what led to it, and specific market effects.")


# ===========================================================================
# ☁️ SEVERE WEATHER RIGHT NOW (at a chokepoint or hub)
# ===========================================================================
def render_rough(place_kind, place, weather, prices, changes):
    severity = rough_severity(weather)
    header(f"Severe weather: {place}", "☁️ Live weather", severity)
    flags = weather_flags(weather)
    tabs = st.tabs(["📊 Overview", "❓ Why", "📈 Markets"])
    with tabs[0]:
        bottom_line(f"{', '.join(f[0].lower() for f in flags)} at {place} right now. A short-term risk: "
                    "usually clears within hours to a couple of days.", severity)
        c1, c2 = st.columns(2)
        c3, _ = st.columns(2)
        c1.metric("Wind gusts", f"{weather['gusts']:.0f} km/h")
        c2.metric("Waves", f"{weather['waves_m']:.1f} m" if weather.get("waves_m") is not None else "n/a")
        c3.metric("Visibility", f"{weather['visibility_km']:.1f} km" if weather.get("visibility_km") is not None else "n/a")
        st.markdown(describe_weather(weather))
        subtitle("What it affects")
        st.markdown("Ships may slow, anchor or be held by port authorities." if place_kind == "chokepoint" else
                    "Flights may be delayed, diverted or cancelled; a hub backlog can delay parcels for days.")
    with tabs[1]:
        subtitle("📏 Measured")
        bullets([f"**{name}**: {detail}" for name, detail in flags])
        st.markdown("Thresholds used: gusts ≥ 60 km/h (strong) / ≥ 90 km/h (storm-force); waves ≥ 3 m (rough) / "
                    "≥ 5 m (very rough); visibility < 1 km (fog). Above these, ports and airports often slow operations.")
    with tabs[2]:
        impacts = (CHOKEPOINT_IMPACTS if place_kind == "chokepoint" else HUB_IMPACTS).get(place, [])
        render_impacts(impacts, prices, changes, since_label="over the last month",
                       note="These markets matter only if the bad weather lasts long enough to disrupt traffic.")
