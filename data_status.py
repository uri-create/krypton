# data_status.py
# "Live data status": for every live feed, when Krypton last checked it, how new the newest data inside it
# is, and how often it refreshes. Shown in the Account tab, so anyone can confirm the data is current.

import html

import pandas as pd
import streamlit as st

from live_data import FEEDS, ready_state, status

FEED_INFO = {
    "universe": ("Company list", "Nasdaq"),
    "live_prices": ("Live company prices", "Yahoo Finance"),
    "prices": ("Watched markets (oil, metals, indices...)", "Yahoo Finance"),
    "compass": ("Market Compass", "Yahoo Finance"),
    "conflict_news": ("Conflict news", "Google News"),
    "disasters": ("Disasters", "GDACS (UN / EU)"),
    "air": ("Live aircraft", "OpenSky"),
    "weather": ("Weather and sea", "Open-Meteo"),
    "traffic": ("Ship traffic", "IMF PortWatch"),
}


def _ago(seconds):
    if seconds is None:
        return "not yet"
    if seconds < 90:
        return "just now"
    if seconds < 3600:
        return f"{seconds / 60:.0f} min ago"
    return f"{seconds / 3600:.1f} hours ago"


def _every(seconds):
    return f"{seconds / 3600:.0f} hours" if seconds >= 3600 * 2 else (
        "hour" if seconds == 3600 else f"{seconds / 60:.0f} min")


def _newest(name, state):
    """How new the newest data inside a feed is (plain text)."""
    try:
        if name == "traffic":
            return f"{pd.to_datetime(state['traffic']['date']).max():%d %b} (IMF publishes about a week late)"
        if name == "prices":
            return f"close of {state['prices'].index.max():%d %b}"
        if name == "compass" and state.get("compass"):
            return f"close of {state['compass']['date']:%d %b}"
        if name == "conflict_news":
            times = [h["published"] for v in state["conflict_news"].values() for h in v if h.get("published") is not None]
            return f"newest headline {max(times):%d %b %H:%M} UTC" if times else "no headlines"
        if name == "disasters":
            return f"{len(state['disasters'])} active events"
        if name == "air" and state.get("air"):
            return f"{state['air']['total_planes']:,} planes at {state['air'].get('time', '')} UTC"
        if name == "weather":
            return "current conditions"
        if name == "universe" and state.get("universe") is not None:
            return f"{len(state['universe']):,} companies"
        if name == "live_prices" and state.get("universe") is not None and "live" in state["universe"]:
            live = int(state["universe"]["live"].sum())
            return f"{live:,} companies priced live" if live else "loading..."
    except Exception:
        pass
    return "n/a"


def last_update_text():
    """'Data updated 3 min ago' for the top bar (the most recent of the fast feeds)."""
    ages = [age for name, (age, _) in status().items() if age is not None and FEEDS[name][1] <= 3600]
    return f"Data updated {_ago(min(ages))}" if ages else "Data loading"


def data_status_panel(state=None):
    state = state or ready_state() or {}
    st.markdown("#### Live data status")
    st.caption("Every live source Krypton uses, when it was last checked and how new its newest data is. Sources are "
               "re-checked automatically on their schedule whenever someone is using Krypton.")
    rows = ["<table class='ktable'><tr><th>Data</th><th>Source</th><th>Last checked</th><th>Newest data</th>"
            "<th>Checked every</th></tr>"]
    for name, (age, refreshing) in status().items():
        label, source = FEED_INFO.get(name, (name, ""))
        checked = _ago(age) + (" · updating now" if refreshing else "")
        rows.append(f"<tr><td>{html.escape(label)}</td><td>{html.escape(source)}</td><td>{checked}</td>"
                    f"<td>{html.escape(_newest(name, state))}</td><td>{_every(FEEDS[name][1])}</td></tr>")
    st.markdown("".join(rows) + "</table>", unsafe_allow_html=True)
