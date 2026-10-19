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
from live_data import get_state
from globe import krypton_globe, to_event_id
from markets import SECTORS
from tabs_extra import alerts_tab, analyst_tab, briefing_tab, portfolio_tab, track_record_tab
from auth_ui import account_tab, login_gate
from billing import handle_return, pro_page
from storage import MISCONFIGURED
from panels import (SEVERITY, stat_cards, chokepoint_severity, conflict_severity, disaster_severity, hub_severity,
                    line_chart, pie_chart, render_chokepoint, render_conflict, render_disaster, render_hub,
                    render_rough, rough_severity)

st.set_page_config(page_title="Krypton", page_icon="🔺", layout="wide")
st.session_state["_chart_n"] = 0  # chart ID counter, see panels.chart_key

# KRYPTON palette: near-black, blood red, cold grey
CYAN, AMBER, RED, GRID = "#ff2a3d", "#ffb000", "#ff2a3d", "#3a1a20"   # "CYAN" is now the red accent

# ===========================================================================
# LOOK & FEEL: sleek and sinister. Near-black glass, blood-red glow, clean modern type.
# ===========================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {{
  --bg: #060608; --glass: rgba(20, 12, 15, 0.62); --glass-strong: rgba(14, 8, 10, 0.85);
  --line: rgba(255, 255, 255, 0.07); --line-red: rgba(255, 42, 61, 0.35);
  --red: {RED}; --red-deep: #8b0a1a; --text: #e9e9ee; --muted: #8a8a96;
}}
html, body, [class*="css"], .stMarkdown, .stDataFrame, button, input, textarea, select {{
  font-family: 'Inter', system-ui, sans-serif; }}
h1, h2, h3, .hud-title, .panel-title {{ font-family: 'Space Grotesk', 'Inter', sans-serif; }}

/* Deep black with soft crimson light bleeding in from the edges */
.stApp {{
  background-color: var(--bg);
  background-image:
    radial-gradient(1200px 600px at 15% -10%, rgba(150, 0, 20, 0.28), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(90, 0, 12, 0.22), transparent 55%),
    radial-gradient(800px 600px at 50% 120%, rgba(70, 0, 10, 0.25), transparent 60%);
  background-attachment: fixed;
}}
.block-container {{ padding-top: 2rem; }}

h1, h2 {{ font-weight: 700 !important; letter-spacing: -0.01em; color: var(--text) !important; }}
h3 {{ color: var(--text) !important; font-size: 1.02rem !important; font-weight: 600 !important;
      letter-spacing: 0.01em; display: flex; align-items: center; gap: 10px; margin-top: 0.6rem; }}
h3::before {{ content: ""; width: 4px; height: 18px; border-radius: 4px; flex: none;
              background: linear-gradient(180deg, var(--red), var(--red-deep));
              box-shadow: 0 0 12px rgba(255, 42, 61, 0.6); }}

/* Glass cards */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border: 1px solid var(--line) !important; border-radius: 16px !important;
  background: var(--glass); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.03);
  transition: border-color 0.25s, box-shadow 0.25s;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  border-color: var(--line-red) !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 28px rgba(255, 42, 61, 0.08); }}
[data-testid="stMetric"] {{ background: rgba(255, 255, 255, 0.02); border: 1px solid var(--line);
                            border-radius: 12px; padding: 10px 14px; }}
[data-testid="stMetricValue"] {{ color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; }}
[data-testid="stMetricLabel"] {{ color: var(--muted); }}
a {{ color: #ff6b78 !important; text-decoration: none; }}
a:hover {{ color: #ff9aa3 !important; }}

/* Buttons */
.stButton button, .stLinkButton a, .stFormSubmitButton button {{
  border-radius: 10px !important; border: 1px solid var(--line) !important; font-weight: 500;
  transition: all 0.2s ease; }}
.stButton button:hover, .stLinkButton a:hover {{ border-color: var(--line-red) !important;
  box-shadow: 0 0 18px rgba(255, 42, 61, 0.15); }}
button[kind="primary"], button[kind="primaryFormSubmit"], a[kind="primary"] {{
  background: linear-gradient(135deg, #ff2a3d, #a10d22) !important; border: none !important;
  color: #fff !important; box-shadow: 0 6px 22px rgba(255, 42, 61, 0.28); }}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover, a[kind="primary"]:hover {{
  box-shadow: 0 8px 30px rgba(255, 42, 61, 0.45); transform: translateY(-1px); }}

/* Tabs: clean underline with a red glow */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ border-radius: 10px 10px 0 0; padding: 8px 14px; color: var(--muted); }}
.stTabs [aria-selected="true"] {{ color: var(--text) !important; background: rgba(255, 42, 61, 0.07); }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--red); box-shadow: 0 0 12px var(--red); }}

/* Inputs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {{
  border-radius: 10px !important; background: rgba(255, 255, 255, 0.03) !important; }}
[data-testid="stExpander"] details {{ border-radius: 12px; border-color: var(--line); }}
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* Top status bar */
.hud {{ display: flex; flex-wrap: wrap; align-items: center; gap: 28px; padding: 18px 24px;
        border: 1px solid var(--line); border-radius: 18px; background: var(--glass-strong);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); margin-bottom: 8px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(255, 42, 61, 0.07);
        position: relative; overflow: hidden; }}
.hud::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
                background: linear-gradient(180deg, var(--red), transparent); }}
.hud-title {{ font-size: 1.75rem; font-weight: 700; letter-spacing: 0.32em;
              background: linear-gradient(90deg, #ffffff 0%, #ffb3ba 45%, var(--red) 100%);
              -webkit-background-clip: text; background-clip: text; color: transparent;
              filter: drop-shadow(0 0 18px rgba(255, 42, 61, 0.35)); }}
.hud-tag {{ font-size: 0.66rem; color: #ff8a95; border: 1px solid var(--line-red); border-radius: 999px;
            padding: 3px 10px; letter-spacing: 0.18em; background: rgba(255, 42, 61, 0.06); }}
.hud-item {{ font-size: 0.68rem; color: var(--muted); letter-spacing: 0.12em; text-transform: uppercase; }}
.hud-item b {{ display: block; font-size: 1.3rem; color: var(--text); letter-spacing: 0; font-weight: 600;
               text-transform: none; margin-top: 2px; font-variant-numeric: tabular-nums; }}
.live {{ display: inline-flex; align-items: center; gap: 8px; color: #ff8a95; font-size: 0.72rem;
         font-weight: 600; letter-spacing: 0.2em; padding: 4px 11px; border-radius: 999px;
         background: rgba(255, 42, 61, 0.1); border: 1px solid var(--line-red); }}
.live::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--red);
                 animation: ping 1.6s infinite; }}
@keyframes ping {{ 0% {{ box-shadow: 0 0 0 0 rgba(255, 42, 61, 0.7); }}
                   70% {{ box-shadow: 0 0 0 9px rgba(255, 42, 61, 0); }}
                   100% {{ box-shadow: 0 0 0 0 rgba(255, 42, 61, 0); }} }}

/* Side panel */
.panel-title {{ color: var(--text); font-size: 1.2rem; font-weight: 700; letter-spacing: 0.01em;
                border-left: 3px solid var(--red); padding-left: 10px; }}
.badge {{ display: inline-block; padding: 3px 11px; border: 1px solid; border-radius: 999px;
          font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 4px; }}
.section {{ color: #ff8a95; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;
            margin-top: 16px; border-top: 1px solid var(--line); padding-top: 10px; }}

/* Number cards that explain themselves (panels.stat_cards) */
.stat {{ background: rgba(255, 255, 255, 0.025); border: 1px solid var(--line); border-radius: 14px;
         padding: 14px 16px 12px; margin-bottom: 12px; height: calc(100% - 12px); }}
.stat-label {{ color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
               text-transform: uppercase; }}
.stat-value {{ color: var(--text); font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin-top: 4px;
               font-family: 'Space Grotesk', 'Inter', sans-serif; font-variant-numeric: tabular-nums; }}
.stat-delta {{ display: inline-block; margin-top: 6px; padding: 2px 9px; border-radius: 999px; font-size: 0.75rem;
               font-weight: 600; background: rgba(255, 255, 255, 0.06); color: var(--muted); }}
.stat-delta.bad {{ background: rgba(255, 42, 61, 0.14); color: #ff6b78; }}
.stat-delta.good {{ background: rgba(61, 220, 132, 0.12); color: #5ee39a; }}
.stat-explain {{ color: #a3a3ae; font-size: 0.8rem; line-height: 1.45; margin-top: 8px;
                 border-top: 1px solid var(--line); padding-top: 8px; }}

/* Slim dark scrollbars */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-thumb {{ background: rgba(255, 42, 61, 0.25); border-radius: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
</style>
""", unsafe_allow_html=True)

# Styles INSIDE the flat map: glowing icons, pulsing alerts, soft vignette
MAP_CSS = f"""
<style>
.ww-div {{ background: transparent !important; border: none !important; }}
.ww-icon {{ font-size: 18px; filter: drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor);
            transition: transform 0.15s; cursor: pointer; }}
.ww-icon:hover {{ transform: scale(1.35); }}
.ww-pulse {{ animation: wwpulse 1.4s ease-in-out infinite; }}
@keyframes wwpulse {{ 0%,100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.45; transform: scale(1.25); }} }}
.leaflet-tile-pane {{ filter: brightness(0.85) contrast(1.1) saturate(1.1); }}
.leaflet-container {{ background: #060608 !important; border-radius: 16px; }}
.leaflet-container::after {{
  content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 450;
  background: radial-gradient(ellipse at center, transparent 60%, rgba(10, 0, 2, 0.55) 100%);
}}
.leaflet-bar a {{ background: #120a0c !important; color: {CYAN} !important; border-color: {GRID} !important; }}
.leaflet-bar {{ border: 1px solid {GRID} !important; border-radius: 10px !important; overflow: hidden;
                box-shadow: 0 0 10px rgba(255,42,61,0.2) !important; }}
.leaflet-control-attribution {{ background: rgba(6,6,8,0.7) !important; color: #5a5a66 !important; }}
.leaflet-control-attribution a {{ color: #5a5a66 !important; }}
.leaflet-tooltip {{ background: rgba(14,8,10,0.95); color: #e9e9ee; border: 1px solid rgba(255,42,61,0.4);
                    border-radius: 10px; font-family: 'Inter', sans-serif; font-size: 12px;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.6); }}
</style>
"""


# ===========================================================================
# DATA (cached so the page is fast and we're kind to the free servers)
# ===========================================================================
MINUTE, HOUR = 60, 3600

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
    # For the owner: which secret NAMES the website can see (never their values), to fix setup mistakes
    try:
        names = sorted(st.secrets.keys())
        st.caption(f"Setup check: secrets found: {', '.join(names) or 'none'}. Needed: DATABASE_URL.")
    except Exception:
        st.caption("Setup check: the Secrets box couldn't be read. Check its formatting "
                   '(each line like NAME = "value", with straight quotes).')
    st.stop()
user = login_gate()
handle_return(user)  # just came back from paying on Stripe?
if st.session_state.get("pro_page"):  # a 🔒 button was pressed: show the Krypton Pro page instead
    pro_page(user)
    st.stop()

# ===========================================================================
# LOAD
# ===========================================================================
try:
    with st.spinner("Acquiring feeds: ships, aircraft, weather, conflicts, markets..."):
        state = get_state()  # instant after the first visit (see live_data.py)
except Exception as error:
    st.error("Couldn't load the live data right now. Try refreshing in a minute.")
    st.stop()
traffic, disasters, prices, air = state["traffic"], state["disasters"], state["prices"], state["air"]
sea_weather, hub_weather, conflict_news = state["sea_weather"], state["hub_weather"], state["conflict_news"]
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


def as_fragment(tab_function, chart_base):
    """Run a tab as a "fragment": clicking inside it redraws only that tab, not the whole app."""
    @st.fragment
    def run(*args):
        st.session_state["_chart_n"] = chart_base  # chart IDs stay the same on every redraw (panels.chart_key)
        tab_function(*args)
    return run


with main_tabs[1]:
    as_fragment(portfolio_tab, 10_000)(state, user)
with main_tabs[2]:
    as_fragment(alerts_tab, 20_000)(state, user)
with main_tabs[3]:
    as_fragment(track_record_tab, 30_000)()
with main_tabs[4]:
    as_fragment(analyst_tab, 40_000)(state, user)
with main_tabs[5]:
    as_fragment(briefing_tab, 50_000)(state, user)
with main_tabs[6]:
    as_fragment(account_tab, 60_000)(user)


@st.fragment
def map_and_panel():
    """The map/globe and the side panel. Clicking an icon redraws only this part."""
    st.session_state["_chart_n"] = 0
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
                st.rerun(scope="fragment")  # redraw just the map + side panel for the clicked event
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


@st.fragment
def trends_and_markets():
    """The charts and market tiles under the map. Changing a dropdown redraws only this part."""
    st.session_state["_chart_n"] = 5_000
    # ===========================================================================
    # DETAIL SECTIONS
    # ===========================================================================
    st.markdown("### 🚢 Chokepoints at a glance")
    st.caption("Each row is one of the world's key shipping routes. 'Ships/day' = average number of ships passing "
               "through each day; the % columns compare that with normal (the last 3 months) and with a year ago. "
               "Status sums it up: Normal, Below normal, Disrupted or Unusually busy.")
    st.dataframe([{"": STATUS_STYLE[s["Status"]]["emoji"], **{k: v for k, v in s.items() if k != "Data up to"}}
                  for s in statuses], hide_index=True, width="stretch")

    st.markdown("### 🔍 Trends")
    problem_first = sorted(statuses, key=lambda s: list(STATUS_STYLE).index(s["Status"]))
    left, right = st.columns(2)
    with left:
        chosen = st.selectbox("Shipping chokepoint", [s["Chokepoint"] for s in problem_first])
        daily = traffic[traffic["chokepoint"] == chosen].set_index("date").sort_index()
        line_chart(daily["ships"].rolling(7).mean(), f"Ships passing through {chosen} per day (7-day average)",
                   "Ships per day", height=300,
                   explain="Each point is the average number of ships per day over the week before it. "
                           "Pick a different chokepoint above to compare.")
        kinds = ["tankers", "container ships", "bulk carriers"]
        p1, p2 = st.columns(2)
        with p1:
            pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-7:].mean().values), "Ship types: this week",
                      note="Tankers carry oil & gas, container ships carry goods, bulk carriers carry grain, coal and ore.")
        with p2:
            if len(daily) >= 372:
                pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-372:-365].mean().values),
                          "Ship types: a year ago", note="The same mix a year ago, to spot which ships are staying away.")
    with right:
        sector = st.selectbox("Sector", list(SECTORS))
        market = st.selectbox("Market", [m for m in SECTORS[sector] if m in prices.columns])
        line_chart(prices[market], f"{market}: daily price, last 12 months", "Price", colour="#ffb000", height=300,
                   explain="The price at the end of each trading day over the last year.")
        month_moves = {m: (changes.get(m) or {}).get("1 month (%)") for m in SECTORS[sector]}
        risers = sum(1 for v in month_moves.values() if v is not None and v > 1)
        fallers = sum(1 for v in month_moves.values() if v is not None and v < -1)
        flat = len(month_moves) - risers - fallers
        pie_chart(["Up more than 1%", "Down more than 1%", "About flat"], [risers, fallers, flat],
                  f"{sector}: how its markets moved this month",
                  note=f"How many of the {len(month_moves)} {sector.split(' ', 1)[-1].lower()} markets Krypton follows "
                       "went up, went down, or stayed about flat over the last month.")

    st.markdown("### 📈 Markets by sector")
    st.caption("Each card shows a market's latest price, how much it moved this month (green = up, red = down), "
               "and its moves over the last week and year.")
    for tab, sector in zip(st.tabs(list(SECTORS)), SECTORS):
        with tab:
            cards = []
            for name in [m for m in SECTORS[sector] if m in changes]:
                c = changes[name]
                month = c["1 month (%)"]
                cards.append({"label": name, "value": f"{c['Price']:,.2f}",
                              "delta": f"{month:+.1f}% this month" if month is not None else None,
                              "tone": "bad" if (month or 0) < 0 else "good",
                              "explain": f"Latest price. Last week: {describe_move(c['1 week (%)'])} · "
                                         f"last year: {describe_move(c['1 year (%)'])}."})
            stat_cards(cards, per_row=4)


with main_tabs[0]:
    map_and_panel()
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
    trends_and_markets()
