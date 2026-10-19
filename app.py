# app.py
# Krypton: a live global situation monitor.
# Shipping chokepoints, air cargo hubs, weather, military activity, earthquakes and markets,
# on one dark map. Click any icon for a full breakdown: what's happening, why, and what it affects.
#
# Run it FROM THIS FOLDER (so the dark theme in .streamlit/config.toml loads):
#   cd C:\Users\uri\Projects\WorldWatch
#   python -m streamlit run app.py

import datetime as dt
import html
import math

import folium
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from analysis import STATUS_STYLE, build_briefing, chokepoint_status, describe_move, price_changes
from data_sources import (CHOKEPOINTS, get_air_history, get_air_traffic, get_chokepoint_traffic,
                          get_disasters, get_headlines, get_many_headlines, get_prices, get_weather)
from explain_layers import air_hub_status, military_intensity, weather_flags
from layers import AIR_HUBS, AIR_ROUTES, CATEGORIES, CONFLICT_ZONES, SEA_ROUTES
from engine import build_state, safe  # noqa: E402
from globe import krypton_globe, to_event_id
from markets import SECTORS
from tabs_extra import alerts_tab, analyst_tab, briefing_tab, portfolio_tab, track_record_tab
from auth_ui import account_tab, login_gate
from storage import MISCONFIGURED
from panels import (SEVERITY, chokepoint_severity, conflict_severity, disaster_severity, hub_severity,
                    line_chart, pie_chart, render_chokepoint, render_conflict, render_disaster, render_hub,
                    render_rough, rough_severity)

st.set_page_config(page_title="Krypton", page_icon="🔺", layout="wide")
st.session_state["_chart_n"] = 0  # chart ID counter, see panels.chart_key

# KRYPTON palette: near-black, blood red, cold grey
CYAN, AMBER, RED, GRID = "#ff2a3d", "#ffb000", "#ff2a3d", "#2a1216"   # "CYAN" is now the red accent

# ===========================================================================
# LOOK & FEEL: classified research terminal. Black, blood red, glitch title, scanlines
# ===========================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stDataFrame {{ font-family: 'JetBrains Mono', monospace; }}

/* Almost-black background with a faint red grid and a dark red glow at the top */
.stApp {{
  background-color: #020203;
  background-image:
    radial-gradient(ellipse at top, rgba(120,0,15,0.22) 0%, transparent 55%),
    linear-gradient(rgba(255,42,61,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,42,61,0.03) 1px, transparent 1px);
  background-size: 100% 100%, 46px 46px, 46px 46px;
}}
/* Scanlines over everything (purely visual, doesn't block clicks) */
.stApp::after {{
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 9999;
  background: repeating-linear-gradient(0deg, rgba(0,0,0,0.25) 0px, rgba(0,0,0,0.25) 1px,
              transparent 1px, transparent 3px);
}}
h1, h2, h3 {{ text-transform: uppercase; letter-spacing: 0.16em; font-weight: 800 !important; }}
h3 {{ color: #9a9aa4 !important; font-size: 0.9rem !important; border-bottom: 1px solid {GRID};
      padding-bottom: 6px; }}
h3::before {{ content: "▌"; color: {RED}; margin-right: 6px; }}
[data-testid="stVerticalBlockBorderWrapper"] {{
  border-color: {GRID} !important; background: rgba(8,4,5,0.94);
  box-shadow: 0 0 22px rgba(255,42,61,0.05), inset 0 0 40px rgba(0,0,0,0.7);
}}
[data-testid="stMetricValue"] {{ color: #e8e8ee; }}
a {{ color: #ff6b78 !important; }}
button[kind="primary"] {{ background: #8b0f1f !important; border-color: {RED} !important; }}

/* Top status bar */
.hud {{ display:flex; flex-wrap:wrap; align-items:center; gap:30px; padding:12px 18px;
        border:1px solid {GRID}; border-left:3px solid {RED}; background:rgba(6,2,3,0.96);
        margin-bottom:6px; box-shadow: 0 0 30px rgba(255,42,61,0.10); }}
.hud-title {{ font-size:1.7rem; font-weight:800; letter-spacing:0.38em; color:#f2f2f5; position:relative;
              text-shadow: 2px 0 {RED}, -2px 0 rgba(0,200,255,0.35); animation: glitch 4s infinite; }}
.hud-tag {{ font-size:0.62rem; color:{RED}; border:1px solid {RED}; padding:1px 6px; letter-spacing:0.25em; }}
.hud-item {{ font-size:0.68rem; color:#77777f; letter-spacing:0.16em; text-transform:uppercase; }}
.hud-item b {{ display:block; font-size:1.2rem; color:#e8e8ee; letter-spacing:0.05em; }}
.live {{ color:{RED}; font-weight:800; letter-spacing:0.25em; }}
.live::before {{ content:"●"; margin-right:6px; animation: blink 1.1s infinite; }}
@keyframes blink {{ 50% {{ opacity: 0.1; }} }}
@keyframes glitch {{
  0%,92%,100% {{ text-shadow: 2px 0 {RED}, -2px 0 rgba(0,200,255,0.35); transform: none; }}
  93% {{ text-shadow: -3px 0 {RED}, 3px 0 rgba(0,200,255,0.5); transform: translateX(2px) skewX(-8deg); }}
  95% {{ text-shadow: 3px 0 {RED}, -3px 0 rgba(0,200,255,0.5); transform: translateX(-2px); opacity: 0.8; }}
  97% {{ transform: none; opacity: 1; }}
}}

/* Side panel */
.panel-title {{ color:#f2f2f5; font-size:1.1rem; font-weight:800; letter-spacing:0.1em;
                text-transform:uppercase; border-left:3px solid {RED}; padding-left:8px; }}
.badge {{ display:inline-block; padding:2px 10px; border:1px solid; font-size:0.72rem;
          letter-spacing:0.14em; text-transform:uppercase; margin-top:4px; }}
.section {{ color:#8a2a35; font-size:0.72rem; letter-spacing:0.2em; text-transform:uppercase;
            margin-top:14px; border-top:1px solid {GRID}; padding-top:8px; }}
.section::before {{ content:"// "; }}
</style>
""", unsafe_allow_html=True)

# Styles INSIDE the map: raw glowing icons, pulsing alerts, darker tiles, vignette + scanlines
MAP_CSS = f"""
<style>
.ww-div {{ background: transparent !important; border: none !important; }}
.ww-icon {{ font-size: 18px; filter: drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor);
            transition: transform 0.15s; cursor: pointer; }}
.ww-icon:hover {{ transform: scale(1.35); }}
.ww-pulse {{ animation: wwpulse 1.4s ease-in-out infinite; }}
@keyframes wwpulse {{ 0%,100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.45; transform: scale(1.25); }} }}
.leaflet-tile-pane {{ filter: brightness(0.9) contrast(1.1) saturate(1.15); }}
.leaflet-container {{ background: #020203 !important; }}
.leaflet-container::after {{
  content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 450;
  background:
    radial-gradient(ellipse at center, transparent 60%, rgba(10,0,2,0.6) 100%),
    repeating-linear-gradient(0deg, rgba(0,0,0,0.12) 0px, rgba(0,0,0,0.12) 1px, transparent 1px, transparent 3px);
}}
.leaflet-bar a {{ background: #0a0405 !important; color: {CYAN} !important; border-color: {GRID} !important; }}
.leaflet-bar {{ border: 1px solid {GRID} !important; box-shadow: 0 0 10px rgba(255,42,61,0.2) !important; }}
.leaflet-control-attribution {{ background: rgba(3,5,9,0.7) !important; color: #4f6475 !important; }}
.leaflet-control-attribution a {{ color: #4f6475 !important; }}
.leaflet-tooltip {{ background: #05080d; color: #c8d3e0; border: 1px solid {GRID};
                    font-family: 'JetBrains Mono', monospace; font-size: 11px; box-shadow: 0 0 10px #000; }}
</style>
"""


# ===========================================================================
# DATA (cached so the page is fast and we're kind to the free servers)
# ===========================================================================
MINUTE, HOUR = 60, 3600

@st.cache_data(ttl=6 * HOUR, show_spinner=False)
def cached_traffic():
    return get_chokepoint_traffic()

@st.cache_data(ttl=HOUR, show_spinner=False)
def cached_disasters():
    return get_disasters()

@st.cache_data(ttl=HOUR, show_spinner=False)
def cached_prices():
    return get_prices()

@st.cache_data(ttl=15 * MINUTE, show_spinner=False)
def cached_air():
    try:
        return get_air_traffic(AIR_HUBS, CONFLICT_ZONES)
    except Exception:
        return None

@st.cache_data(ttl=30 * MINUTE, show_spinner=False)
def cached_weather():
    try:
        return get_weather(CHOKEPOINTS, marine=True), get_weather(AIR_HUBS)
    except Exception:
        return {}, {}

@st.cache_data(ttl=HOUR, show_spinner=False)
def cached_conflict_news():
    return get_many_headlines({name: zone["news"] for name, zone in CONFLICT_ZONES.items()})

@st.cache_data(ttl=HOUR, show_spinner=False)
def cached_headlines(topic):
    try:
        return get_headlines(topic)
    except Exception:
        return []


def great_circle(lat1, lon1, lat2, lon2, steps=40):
    """Points along the shortest path over the globe (how planes actually fly), so air routes curve.
    Longitudes are 'unwrapped' so a route across the Pacific doesn't jump across the whole map."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    d = 2 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2
                                + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2))
    points, previous = [], None
    for i in range(steps + 1):
        f = i / steps
        a, b = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
        x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
        y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
        z = a * math.sin(p1) + b * math.sin(p2)
        lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
        lon = math.degrees(math.atan2(y, x))
        if previous is not None:
            while lon - previous > 180:
                lon -= 360
            while lon - previous < -180:
                lon += 360
        points.append((lat, lon))
        previous = lon
    return points


# ===========================================================================
# LOG IN (nothing below this runs until someone is logged in)
# ===========================================================================
if MISCONFIGURED:  # online without the real database: lock everything (see storage.py)
    st.error("🔧 Krypton is being set up and will be back shortly.")
    st.stop()
user = login_gate()

# ===========================================================================
# LOAD
# ===========================================================================
try:
    with st.spinner("Acquiring feeds: ships, aircraft, weather, conflicts, markets..."):
        traffic = cached_traffic()
        disasters = cached_disasters()
        prices = cached_prices()
        air = cached_air()
        sea_weather, hub_weather = cached_weather()
        conflict_news = cached_conflict_news()
except Exception as error:
    st.error(f"Couldn't load data: {error}. Try refreshing in a minute.")
    st.stop()

state = build_state({"traffic": traffic, "disasters": disasters, "prices": prices, "air": air,
                     "sea_weather": sea_weather, "hub_weather": hub_weather, "conflict_news": conflict_news})
air_history, statuses, status_by_name = state["air_history"], state["statuses"], state["status_by_name"]
changes, conflict_info, conflict_levels = state["changes"], state["conflict_info"], state["conflict_levels"]
events = state["events"]

# ===========================================================================
# HUD STATUS BAR
# ===========================================================================
disrupted = sum(1 for s in statuses if s["Status"] == "Disrupted")
active_conflicts = sum(1 for level in conflict_levels.values() if level in ("High", "Elevated"))
red_alerts = sum(1 for d in disasters if d["alert"] == "Red")
planes = f"{air['total_planes']:,}" if air else "—"
st.markdown(f"""
<div class="hud">
  <div class="hud-title">KRYPTON</div>
  <div class="live">LIVE</div>
  <div class="hud-tag">CLASSIFIED // GLOBAL SITUATION MONITOR</div>
  <div class="hud-item">Chokepoints disrupted<b style="color:{RED}">{disrupted} / {len(statuses)}</b></div>
  <div class="hud-item">Active conflicts<b style="color:{RED}">{active_conflicts}</b></div>
  <div class="hud-item">Red disaster alerts<b style="color:{AMBER}">{red_alerts}</b></div>
  <div class="hud-item">Aircraft tracked<b>{planes}</b></div>
  <div class="hud-item">Operator<b>{html.escape(user['username'])}{' · admin' if user['is_admin'] else ''}</b></div>
</div>
""", unsafe_allow_html=True)
st.caption("For learning and research only. Not financial advice.")

# ===========================================================================
# MAIN TABS
# ===========================================================================
main_tabs = st.tabs(["🗺️ Live map", "💼 My portfolio", "🔔 Alerts", "📊 Track record", "🤖 Ask the analyst",
                     "📰 Daily briefing", "👤 Account"])
with main_tabs[1]:
    portfolio_tab(state, user)
with main_tabs[2]:
    alerts_tab(state, user)
with main_tabs[3]:
    track_record_tab()
with main_tabs[4]:
    analyst_tab(state, user)
with main_tabs[5]:
    briefing_tab(state, user)
with main_tabs[6]:
    account_tab(user)

with main_tabs[0]:
    # ===========================================================================
    # LAYER FILTER (click to switch a category on/off)
    # ===========================================================================
    counts = {c: sum(1 for e in events if e["category"] == c) for c in CATEGORIES}
    labels = {c: f"{CATEGORIES[c]['emoji']} {c} ({counts[c]})" for c in CATEGORIES}
    shown = st.pills("LAYERS · click to turn on/off", list(CATEGORIES), selection_mode="multi",
                     default=list(CATEGORIES), format_func=lambda c: labels[c])
    shown = set(shown or [])
    show_routes = st.toggle("Show shipping & air routes", value=True)

    # ===========================================================================
    # MAP + CLICK-TO-EXPLAIN PANEL
    # ===========================================================================
    visible = [e for e in events if e["category"] in shown]
    if "selected" not in st.session_state:
        worst = sorted(statuses, key=lambda s: list(STATUS_STYLE).index(s["Status"]))[0]
        st.session_state["selected"] = ("chokepoint", worst["Chokepoint"])

    map_col, panel_col = st.columns([3, 2])

    with map_col:
        view = st.radio("View", ["🌍 Globe", "🗺️ Flat map"], horizontal=True, label_visibility="collapsed")
        if view == "🌍 Globe":
            # The globe gets plain data: events, shipping lanes and air routes
            globe_events = [{"id": e["id"], "lat": e["lat"], "lng": e["lon"], "icon": e["icon"],
                             "colour": e["colour"], "pulse": e["pulse"], "tooltip": e["tooltip"]} for e in visible]
            sea, air_arcs = [], []
            if show_routes and "Shipping" in shown:
                order = list(STATUS_STYLE)
                for route, info in SEA_ROUTES.items():
                    worst = max((status_by_name[c]["Status"] for c in info["chokepoints"] if c in status_by_name),
                                key=order.index, default="Normal")
                    worst = "Normal" if worst == "Unusually busy" else worst
                    sea.append({"coords": [list(p) for p in info["points"]], "colour": STATUS_STYLE[worst]["colour"],
                                "dashed": worst == "Disrupted", "label": f"🛳️ {route} · {worst}"})
            if show_routes and "Air cargo" in shown:
                for a, b in AIR_ROUTES:
                    air_arcs.append({"startLat": AIR_HUBS[a]["lat"], "startLng": AIR_HUBS[a]["lon"],
                                     "endLat": AIR_HUBS[b]["lat"], "endLng": AIR_HUBS[b]["lon"], "label": f"✈️ {a} ⇄ {b}"})
            picked = krypton_globe(globe_events, sea, air_arcs, height=640, key="globe")
            if picked and picked.get("t") != st.session_state.get("last_globe_click"):
                st.session_state["last_globe_click"] = picked["t"]
                st.session_state["selected"] = to_event_id(picked["id"])
                st.rerun()  # redraw the side panel for the clicked event
        else:
            world_map = folium.Map(
                location=[24, 45], zoom_start=2, min_zoom=2, max_zoom=12, world_copy_jump=True,
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Imagery &copy; Esri",
            )
            # Country borders + names on top of the satellite photos (free Esri reference layer)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
                attr="Labels &copy; Esri", overlay=True, opacity=0.85,
            ).add_to(world_map)
            world_map.get_root().header.add_child(folium.Element(MAP_CSS))

            if show_routes and "Shipping" in shown:
                order = list(STATUS_STYLE)
                for route, info in SEA_ROUTES.items():
                    worst = max((status_by_name[c]["Status"] for c in info["chokepoints"] if c in status_by_name),
                                key=order.index, default="Normal")
                    if worst == "Unusually busy":
                        worst = "Normal"
                    folium.PolyLine(info["points"], color=STATUS_STYLE[worst]["colour"], weight=1.6, opacity=0.55,
                                    dash_array="6 6" if worst == "Disrupted" else None,
                                    tooltip=f"🛳️ {route.upper()} · route status: {worst}").add_to(world_map)
            if show_routes and "Air cargo" in shown:
                for a, b in AIR_ROUTES:
                    ha, hb = AIR_HUBS[a], AIR_HUBS[b]
                    folium.PolyLine(great_circle(ha["lat"], ha["lon"], hb["lat"], hb["lon"]), color=CYAN, weight=1,
                                    opacity=0.35, dash_array="2 6", tooltip=f"✈️ {a} ⇄ {b}").add_to(world_map)

            for e in visible:
                pulse = " ww-pulse" if e["pulse"] else ""
                folium.Marker(
                    [e["lat"], e["lon"]],
                    icon=folium.DivIcon(
                        html=f'<i class="fa-solid {e["icon"]} ww-icon{pulse}" style="color:{e["colour"]}"></i>',
                        icon_size=(24, 24), icon_anchor=(12, 12), class_name="ww-div"),
                    tooltip=e["tooltip"],
                ).add_to(world_map)

            clicked = st_folium(world_map, height=600, use_container_width=True, key="worldmap") or {}

            # Which icon was clicked? Match the click position to the nearest visible icon.
            spot = clicked.get("last_object_clicked") or clicked.get("last_clicked")
            if spot and spot != st.session_state.get("last_spot") and visible:
                st.session_state["last_spot"] = spot
                nearest = min(visible, key=lambda e: (e["lat"] - spot["lat"]) ** 2 + (e["lon"] - spot["lng"]) ** 2)
                reach = 10 / 2 ** max((clicked.get("zoom") or 2) - 2, 0)  # "near" shrinks as you zoom in
                if (nearest["lat"] - spot["lat"]) ** 2 + (nearest["lon"] - spot["lng"]) ** 2 <= reach ** 2:
                    st.session_state["selected"] = nearest["id"]

        # Map key: icon SHAPE = type of event, icon COLOUR = severity
        shapes = " &nbsp;&nbsp; ".join(f"<i class='fa-solid {CATEGORIES[c]['icon']}'></i> {c}" for c in CATEGORIES)
        colours = " &nbsp;&nbsp; ".join(
            f"<span style='color:{v['colour']};text-shadow:0 0 6px {v['colour']}'>●</span> <b>{k}</b>: {v['meaning']}"
            for k, v in SEVERITY.items())
        st.markdown(
            "<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css'>"
            f"<div style='font-size:0.74rem;color:#7d93aa;line-height:1.9'><b>SHAPE = what it is:</b> {shapes}<br>"
            f"<b>COLOUR = how severe:</b> {colours}<br>Pulsing = critical · lines = sea lanes (coloured by status) "
            "and air cargo lanes (dotted)</div>", unsafe_allow_html=True)

    with panel_col:
        with st.container(border=True, height=760):
            kind, which = st.session_state["selected"]
            if kind == "chokepoint":
                render_chokepoint(which, status_by_name[which], traffic, prices, changes,
                                  cached_headlines(CHOKEPOINTS[which]["news"]), disasters, sea_weather.get(which))
            elif kind == "hub":
                render_hub(which, air, air_history, hub_weather.get(which),
                           cached_headlines(f"{which.split(' (')[0]} airport cargo"), prices, changes, conflict_levels)
            elif kind == "conflict":
                render_conflict(which, conflict_news.get(which, []), air, air_history, statuses, prices, changes)
            elif kind == "rough":
                place_kind, place = which
                render_rough(place_kind, place, (sea_weather if place_kind == "chokepoint" else hub_weather).get(place),
                             prices, changes)
            else:
                d = disasters[which]
                render_disaster(d, prices, changes, cached_headlines(d["name"]))

    # ===========================================================================
    # BRIEFING
    # ===========================================================================
    with st.container(border=True):
        st.markdown("### 📋 Situation briefing")
        lines = build_briefing(statuses, changes, disasters)
        hot = [f"**{n}**" for n, level in conflict_levels.items() if level == "High"]
        if hot:
            lines.insert(0, f"🛡️ **High military activity:** {', '.join(hot)}.")
        quiet_hubs = [n for n in AIR_HUBS if air_hub_status(n, air, air_history)[0] == "Unusually quiet"]
        if quiet_hubs:
            lines.append(f"✈️ **Unusually quiet cargo hubs:** {', '.join(quiet_hubs)}.")
        bad_weather = [e["tooltip"].split(" · ")[1].title() for e in events if e["id"][0] == "rough"]
        if bad_weather:
            lines.append(f"☁️ **Severe weather right now at:** {', '.join(bad_weather)}.")
        for line in lines:
            st.markdown(f"- {line}")
        st.caption(f"Sources: IMF PortWatch (ships, ~1 week delay), OpenSky (live aircraft), Open-Meteo (weather), "
                   f"GDACS (disasters), Google News (headlines), Yahoo Finance (prices).")

    # ===========================================================================
    # DETAIL SECTIONS
    # ===========================================================================
    st.markdown("### 🚢 Chokepoints at a glance")
    st.dataframe([{"": STATUS_STYLE[s["Status"]]["emoji"], **{k: v for k, v in s.items() if k != "Data up to"}}
                  for s in statuses], hide_index=True, width="stretch")

    st.markdown("### 🔍 Trends")
    problem_first = sorted(statuses, key=lambda s: list(STATUS_STYLE).index(s["Status"]))
    left, right = st.columns(2)
    with left:
        chosen = st.selectbox("Shipping chokepoint", [s["Chokepoint"] for s in problem_first])
        daily = traffic[traffic["chokepoint"] == chosen].set_index("date").sort_index()
        line_chart(daily["ships"].rolling(7).mean(), f"Ships passing through {chosen} per day (7-day average)",
                   "Ships per day", height=300)
        kinds = ["tankers", "container ships", "bulk carriers"]
        p1, p2 = st.columns(2)
        with p1:
            pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-7:].mean().values), "Ship types: this week")
        with p2:
            if len(daily) >= 372:
                pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-372:-365].mean().values),
                          "Ship types: a year ago")
    with right:
        sector = st.selectbox("Sector", list(SECTORS))
        market = st.selectbox("Market", [m for m in SECTORS[sector] if m in prices.columns])
        line_chart(prices[market], f"{market}: daily price, last 12 months", "Price", colour="#ffb000", height=300)
        month_moves = {m: (changes.get(m) or {}).get("1 month (%)") for m in SECTORS[sector]}
        risers = sum(1 for v in month_moves.values() if v is not None and v > 1)
        fallers = sum(1 for v in month_moves.values() if v is not None and v < -1)
        flat = len(month_moves) - risers - fallers
        pie_chart(["Up more than 1%", "Down more than 1%", "About flat"], [risers, fallers, flat],
                  f"{sector}: how its markets moved this month")

    st.markdown("### 📈 Markets by sector")
    st.caption("Price now and change over the last month. Hover the ⓘ for 1-week and 1-year moves.")
    for tab, sector in zip(st.tabs(list(SECTORS)), SECTORS):
        with tab:
            names = [m for m in SECTORS[sector] if m in changes]
            cols = st.columns(4)
            for i, name in enumerate(names):
                c = changes[name]
                month = c["1 month (%)"]
                cols[i % 4].metric(name, f"{c['Price']:,.2f}",
                                   delta=f"{month:+.1f}% this month" if month is not None else None,
                                   help=f"1 week: {describe_move(c['1 week (%)'])} · 1 year: {describe_move(c['1 year (%)'])}")
