# landing.py
# The landing page: what visitors see before they have an account.
#   - a bold headline and a one-line pitch
#   - live numbers from Krypton itself (market reading, companies tracked, world events)
#   - the sign-up / log-in card
#   - what's inside (six features) and where the data comes from
# While a visitor reads, the live data starts loading in the background, so the app is ready the
# moment they log in.

import html

import streamlit as st

from compass import READINGS, reading
from live_data import ready_state, warm_up

# Simple line icons (inline SVG, drawn in the theme's accent colour)
ICONS = {
    "compass": '<circle cx="12" cy="12" r="9"/><polygon points="15.5,8.5 13.5,13.5 8.5,15.5 10.5,10.5"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><line x1="16" y1="16" x2="20.5" y2="20.5"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><line x1="3" y1="12" x2="21" y2="12"/>',
    "grid": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/>'
            '<rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    "clusters": '<circle cx="6" cy="7" r="2.5"/><circle cx="17" cy="6" r="2.5"/><circle cx="12" cy="17" r="2.5"/>'
                '<line x1="8.2" y1="7.8" x2="10.6" y2="15"/><line x1="15.6" y1="8.1" x2="13.2" y2="15"/>'
                '<line x1="8.5" y1="6.8" x2="14.5" y2="6.2"/>',
    "spark": '<path d="M12 3 L13.8 9.2 L20 11 L13.8 12.8 L12 19 L10.2 12.8 L4 11 L10.2 9.2 Z"/>',
}

FEATURES = [
    ("compass", "Market Compass", "Is the market bullish or bearish today? Six signals, one answer, tested on "
                                  "18 years of history."),
    ("search", "Universal search", "Look up any stock: its size, its shares, what it does in plain words, and "
                                   "its price history."),
    ("globe", "Live world map", "Shipping lanes, conflicts, storms and disasters on a 3D globe, and which stocks "
                                "they hit."),
    ("grid", "Sectors at a glance", "Every US-listed company, sorted by sector and size, coloured by today's move."),
    ("clusters", "Clusters", "Find which stocks move together, so you can see when five holdings are really "
                             "one big bet."),
    ("spark", "AI analyst", "Ask questions about the market and get sourced answers, written in plain English. "
                            "(Krypton Pro)"),
]

SOURCES = ["Nasdaq", "Yahoo Finance", "IMF PortWatch", "GDACS (UN / EU)", "Open-Meteo", "OpenSky", "Wikipedia"]


def _icon(name):
    return (f"<svg viewBox='0 0 24 24' width='26' height='26' fill='none' stroke='currentColor' stroke-width='1.6' "
            f"stroke-linecap='round' stroke-linejoin='round'>{ICONS[name]}</svg>")


def _live_chips():
    state = ready_state()
    if not state:
        return "<span class='chip-live muted-chip'>Live data loading…</span>"
    chips = []
    if state.get("compass"):
        name = reading(state["compass"]["today"]["Score"])
        colour = READINGS[name]["colour"]
        chips.append(f"<span class='chip-live' style='color:{colour};border-color:{colour}55;background:{colour}14'>"
                     f"<span class='dot' style='background:{colour}'></span>Market is {name.lower()} right now</span>")
    universe = state.get("universe")
    if universe is not None:
        chips.append(f"<span class='chip-live'><b>{len(universe):,}</b> companies tracked</span>")
    chips.append(f"<span class='chip-live'><b>{len(state['events'])}</b> live world events</span>")
    chips.append("<span class='chip-live'><b>18 years</b> of tested history</span>")
    return "".join(chips)


def hero():
    warm_up()
    st.markdown(
        "<div class='landing-hero'>"
        "<div class='landing-brand'>KRYPTON</div>"
        "<div class='landing-kicker'><span class='dot'></span>MARKET INTELLIGENCE · LIVE</div>"
        "<h1 class='landing-title'>See what <span class='grad'>moves</span> the market.</h1>"
        "<p class='landing-sub'>Krypton watches shipping lanes, wars, storms and thousands of stocks around the "
        "clock, then tells you in plain words what it means for the market.</p>"
        f"<div class='landing-chips'>{_live_chips()}</div>"
        "</div>", unsafe_allow_html=True)


def features():
    cards = "".join(f"<div class='feature'><div class='feature-icon'>{_icon(icon)}</div>"
                    f"<div class='feature-title'>{html.escape(title)}</div>"
                    f"<div class='feature-text'>{html.escape(text)}</div></div>" for icon, title, text in FEATURES)
    sources = "".join(f"<span>{s}</span>" for s in SOURCES)
    st.markdown(
        f"<div class='landing-section'>What's inside</div><div class='feature-grid'>{cards}</div>"
        f"<div class='landing-section'>Built on real data</div><div class='source-strip'>{sources}</div>"
        "<div class='landing-foot'>Free to use. For learning and research only, not financial advice. "
        "Krypton never tells you to buy or sell anything.</div>", unsafe_allow_html=True)
