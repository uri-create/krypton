# app.py
# Krypton: a stock market guide built on a live global situation monitor.
# 🧭 Market Compass (today's market weather + honest odds), 🌍 a live globe of shipping, air cargo,
# weather, military activity and disasters, 📈 ~120 markets, your portfolio, alerts and an AI analyst.
#
# Run it FROM THIS FOLDER (so the dark theme in .streamlit/config.toml loads):
#   cd C:\Users\uri\Projects\WorldWatch
#   python -m streamlit run app.py

import html

import streamlit as st

from analysis import STATUS_STYLE, build_briefing
from auth_ui import account_tab, login_gate
from billing import handle_return, pro_page
from compass import READINGS, reading
from clusters_tab import clusters_tab
from compass_tab import compass_tab
from data_sources import CHOKEPOINTS, get_headlines
from explain_layers import air_hub_status
from globe import krypton_globe, to_event_id
from layers import AIR_HUBS, AIR_ROUTES, CATEGORIES, SEA_ROUTES
from live_data import get_state
from markets_tab import markets_tab
from panels import (SEVERITY, line_chart, pie_chart, render_chokepoint, render_conflict, render_disaster, render_hub,
                    render_rough)
from storage import MISCONFIGURED
from tabs_extra import analyst_tab, briefing_tab, portfolio_tab

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
h3 {{ color: var(--text) !important; font-size: 1.15rem !important; font-weight: 600 !important;
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
[data-testid="stVerticalBlockBorderWrapper"]:hover {{ border-color: rgba(255, 42, 61, 0.22) !important; }}
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

/* Tabs: a smooth segmented pill bar */
.stTabs [role="tablist"] {{ gap: 4px; padding: 5px; border-radius: 14px; border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.025); width: fit-content; max-width: 100%; overflow-x: auto; }}
.stTabs [role="tablist"]::after {{ display: none; }}
.stTabs [role="tab"] {{ border-radius: 10px; padding: 8px 16px; color: var(--muted); height: auto;
  border: none !important; transition: background 0.2s, color 0.2s; }}
.stTabs [role="tab"]::after, .stTabs [role="tab"]::before {{ display: none !important; }}
.stTabs [role="tab"]:hover {{ color: var(--text); background: rgba(255, 255, 255, 0.04); }}
.stTabs [role="tab"][aria-selected="true"] {{ color: #fff !important;
  background: linear-gradient(135deg, rgba(255, 42, 61, 0.24), rgba(139, 10, 26, 0.24)) !important;
  box-shadow: inset 0 0 0 1px rgba(255, 42, 61, 0.35); }}
.stTabs [role="tab"] > div {{ border: none !important; }}
.stTabs [data-testid="stTabPanel"] {{ padding-top: 18px; }}

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
.section {{ color: var(--text); font-family: 'Space Grotesk', 'Inter', sans-serif; font-size: 1.12rem;
            font-weight: 600; margin: 30px 0 6px; display: flex; align-items: center; gap: 8px; }}

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

.hud-right {{ margin-left: auto; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
.hud-pill {{ border: 1px solid; border-radius: 999px; padding: 6px 14px; font-weight: 600; font-size: 0.9rem; }}
.hud-user {{ color: var(--muted); font-size: 0.85rem; }}

/* Market Compass hero */
.hero {{ border: 1px solid var(--line); border-radius: 20px; padding: 22px 26px 18px; margin: 6px 0 14px;
         background: radial-gradient(600px 220px at 0% 0%, color-mix(in srgb, var(--accent) 16%, transparent),
                     transparent 70%), var(--glass-strong);
         box-shadow: 0 20px 60px rgba(0,0,0,0.45), 0 0 50px color-mix(in srgb, var(--accent) 10%, transparent); }}
.hero-kicker {{ color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.16em; }}
.hero-main {{ display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; margin-top: 6px; }}
.hero-icon {{ font-size: 2.4rem; }}
.hero-reading {{ font-family: 'Space Grotesk', sans-serif; font-size: 2.6rem; font-weight: 700; letter-spacing: -0.01em; }}
.hero-score {{ color: var(--muted); font-size: 1rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
.hero-meaning {{ color: #c9c9d1; font-size: 1rem; margin-top: 4px; }}
.hero-foot {{ color: #6f6f7a; font-size: 0.78rem; margin-top: 10px; }}
.gauge {{ position: relative; height: 10px; border-radius: 999px; margin: 16px 0 6px;
          background: linear-gradient(90deg, #ff2a3d 0%, #ffb000 50%, #3ddc84 100%); opacity: 0.85; }}
.gauge-mark {{ position: absolute; top: -5px; width: 6px; height: 20px; border-radius: 4px;
               transform: translateX(-50%); border: 2px solid #fff; }}
.gauge-labels {{ display: flex; justify-content: space-between; color: #6f6f7a; font-size: 0.72rem; }}

/* Clean tables */
.ktable {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 6px 0 4px; }}
.ktable th {{ text-align: left; color: var(--muted); font-weight: 600; font-size: 0.72rem; letter-spacing: 0.06em;
              text-transform: uppercase; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
.ktable td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); color: var(--text);
              font-variant-numeric: tabular-nums; }}
.ktable tr:hover td {{ background: rgba(255, 42, 61, 0.04); }}

/* "How to read this" explainer boxes */
.howto {{ color: #9a9aa6; font-size: 0.88rem; line-height: 1.55; margin: 0 0 14px; max-width: 860px; }}
.howto b {{ color: #e9e9ee; font-weight: 600; }}
.howto-title {{ color: #ff8a95; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em;
                text-transform: uppercase; margin-bottom: 4px; }}
.muted {{ color: #7a7a86; }}

/* Compass legend */
.legend {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-top: 16px; }}
.legend-item {{ display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border-radius: 12px;
                background: rgba(255, 255, 255, 0.025); border: 1px solid var(--line); font-size: 0.82rem; }}
.legend-range {{ color: var(--muted); font-size: 0.72rem; font-variant-numeric: tabular-nums; }}
.legend-text {{ color: #a3a3ae; font-size: 0.78rem; line-height: 1.4; }}

/* World-risk list */
.risk-list {{ display: flex; flex-direction: column; gap: 6px; }}
.risk-row {{ display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 12px;
             background: rgba(255, 255, 255, 0.025); border: 1px solid var(--line); flex-wrap: wrap; }}
.risk-row .muted {{ margin-left: auto; font-size: 0.78rem; }}
.risk-dot {{ width: 8px; height: 8px; border-radius: 50%; flex: none; }}

/* Heat map tiles */
.heat-legend {{ display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 0.75rem;
                margin: 0 0 12px; }}
.heat-scale {{ width: 220px; height: 8px; border-radius: 999px;
               background: linear-gradient(90deg, rgba(255,42,61,0.65), rgba(255,255,255,0.06), rgba(61,220,132,0.65)); }}
.heat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 14px; }}
.heat-sector {{ border: 1px solid var(--line); border-radius: 16px; padding: 12px; background: var(--glass); }}
.heat-head {{ display: flex; justify-content: space-between; align-items: center; color: var(--text);
              font-weight: 600; font-size: 0.9rem; margin-bottom: 10px; }}
.heat-head .stat-delta {{ margin-top: 0; }}
.heat-tiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 6px; }}
.tile {{ border-radius: 10px; padding: 9px 10px; display: flex; flex-direction: column; gap: 3px; min-height: 52px;
         border: 1px solid rgba(255, 255, 255, 0.05); transition: transform 0.15s, box-shadow 0.15s; cursor: default; }}
.tile:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5); }}
.tile-name {{ color: #e9e9ee; font-size: 0.72rem; line-height: 1.2; overflow: hidden; text-overflow: ellipsis;
              display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }}
.tile-move {{ color: #fff; font-weight: 700; font-size: 0.92rem; font-variant-numeric: tabular-nums;
              font-family: 'Space Grotesk', 'Inter', sans-serif; }}

/* Cluster cards and chips */
.cluster-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; margin-bottom: 8px; }}
.cluster-card {{ border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px; background: var(--glass);
                 margin-bottom: 10px; }}
.cluster-head {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
.cluster-head .stat-delta {{ margin-top: 0; }}
.cluster-title {{ color: var(--text); font-weight: 600; font-size: 1rem; font-family: 'Space Grotesk', 'Inter', sans-serif; }}
.cluster-meta {{ color: #a3a3ae; font-size: 0.8rem; margin: 6px 0; }}
.cluster-spans {{ color: #ffb000; font-size: 0.76rem; margin-top: 8px; }}
.bar {{ height: 5px; border-radius: 999px; background: rgba(255, 255, 255, 0.06); overflow: hidden; margin-bottom: 10px; }}
.bar > div {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8b0a1a, var(--red)); }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{ font-size: 0.74rem; color: #c9c9d1; padding: 4px 10px; border-radius: 999px;
         background: rgba(255, 255, 255, 0.04); border: 1px solid var(--line); }}
.chip-anchor {{ color: #fff; border-color: rgba(255, 42, 61, 0.5); background: rgba(255, 42, 61, 0.12); }}

/* Simple page pieces */
.lead {{ color: #c4c4cc; font-size: 1.02rem; line-height: 1.6; max-width: 820px; margin: 2px 0 10px; }}
.signal-list, .pair-list, .buddies {{ display: flex; flex-direction: column; gap: 8px; }}
.signal-row {{ display: grid; grid-template-columns: 150px 120px 1fr; align-items: center; gap: 14px;
               padding: 12px 16px; border-radius: 14px; background: rgba(255, 255, 255, 0.025);
               border: 1px solid var(--line); }}
.signal-row .stat-delta {{ margin-top: 0; text-align: center; }}
.signal-name {{ color: var(--text); font-weight: 600; }}
.signal-text {{ color: #a3a3ae; font-size: 0.88rem; }}
@media (max-width: 760px) {{ .signal-row {{ grid-template-columns: 1fr; gap: 6px; }} }}
.pair-row {{ display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 10px 16px;
             border-radius: 12px; background: rgba(255, 255, 255, 0.025); border: 1px solid var(--line);
             color: var(--text); font-size: 0.9rem; }}
.pair-pct {{ color: var(--muted); font-size: 0.85rem; }}
.pair-pct b {{ color: var(--text); }}
.buddy {{ display: grid; grid-template-columns: minmax(140px, 240px) 1fr 52px; align-items: center; gap: 14px;
          padding: 8px 4px; }}
.buddy-name {{ color: var(--text); font-size: 0.9rem; }}
.buddy-bar {{ height: 10px; border-radius: 999px; background: rgba(255, 255, 255, 0.05); overflow: hidden; }}
.buddy-bar > div {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8b0a1a, var(--red)); }}
.buddy-pct {{ color: var(--text); font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }}
.chip-more {{ color: var(--muted); border-style: dashed; }}

/* Slim dark scrollbars */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-thumb {{ background: rgba(255, 42, 61, 0.25); border-radius: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
</style>
""", unsafe_allow_html=True)

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
except Exception:
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
reading_html = ""
if state.get("compass"):
    _name = reading(state["compass"]["today"]["Score"])
    _colour = READINGS[_name]["colour"]
    reading_html = (f'<div class="hud-pill" style="color:{_colour};border-color:{_colour}55;background:{_colour}14">'
                    f'{READINGS[_name]["icon"]} Market is {_name.lower()}</div>')
st.markdown(f"""
<div class="hud">
  <div class="hud-title">KRYPTON</div>
  <div class="live">LIVE</div>
  <div class="hud-tag">CLASSIFIED // MARKET INTELLIGENCE</div>
  <div class="hud-right">
    {reading_html}
    <div class="hud-user">👤 {html.escape(user['username'])}{' · admin' if user['is_admin'] else ''}</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.caption("For learning and research only. Not financial advice.")

# ===========================================================================
# MAIN TABS
# ===========================================================================
main_tabs = st.tabs(["🧭 Market Compass", "🌍 World map", "📈 Markets", "🧬 Teams", "💼 My portfolio",
                     "🤖 Ask the analyst", "📰 Daily briefing", "👤 Account"])


def as_fragment(tab_function, chart_base):
    """Run a tab as a "fragment": clicking inside it redraws only that tab, not the whole app."""
    @st.fragment
    def run(*args):
        st.session_state["_chart_n"] = chart_base  # chart IDs stay the same on every redraw (panels.chart_key)
        tab_function(*args)
    return run


with main_tabs[0]:
    as_fragment(compass_tab, 70_000)(state, user)
with main_tabs[2]:
    as_fragment(markets_tab, 80_000)(state)
with main_tabs[3]:
    as_fragment(clusters_tab, 20_000)(state)
with main_tabs[4]:
    as_fragment(portfolio_tab, 10_000)(state, user)
with main_tabs[5]:
    as_fragment(analyst_tab, 40_000)(state, user)
with main_tabs[6]:
    as_fragment(briefing_tab, 50_000)(state, user)
with main_tabs[7]:
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
def shipping_trends():
    """Shipping details under the map. Changing the dropdown redraws only this part."""
    st.session_state["_chart_n"] = 5_000
    st.markdown("### 🚢 Shipping routes")
    problem_first = sorted(statuses, key=lambda s: list(STATUS_STYLE).index(s["Status"]))
    left, right = st.columns([3, 2])
    with left:
        chosen = st.selectbox("Shipping chokepoint", [s["Chokepoint"] for s in problem_first])
        daily = traffic[traffic["chokepoint"] == chosen].set_index("date").sort_index()
        line_chart(daily["ships"].rolling(7).mean(), f"Ships passing through {chosen} per day (7-day average)",
                   "Ships per day", height=320,
                   explain="Each point is the average number of ships per day over the week before it. "
                           "Pick a different chokepoint above to compare.")
    with right:
        kinds = ["tankers", "container ships", "bulk carriers"]
        pie_chart([k.capitalize() for k in kinds], list(daily[kinds].iloc[-7:].mean().values), "Ship types: this week",
                  note="Tankers carry oil & gas, container ships carry goods, bulk carriers carry grain, coal and ore.")


with main_tabs[1]:
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
        st.caption("Sources: IMF PortWatch (ships, ~1 week delay), OpenSky (live aircraft), Open-Meteo (weather), "
                   "GDACS (disasters), Google News (headlines), Yahoo Finance (prices).")
    shipping_trends()
