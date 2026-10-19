# markets_tab.py
# The Markets page: every market Krypton follows, at a glance.
#   - Heat map: all ~120 markets as tiles (official name + ticker) grouped by sector, coloured by this month's move
#   - Biggest movers this week
#   - Price explorer (any market, last 12 months) + how a whole sector moved

import html

import streamlit as st

from analysis import describe_move
from markets import EQUITY_SECTORS, FULL_NAME, SECTORS, label, ticker
from panels import how_to_read, line_chart, pie_chart, stat_cards, subtitle


def _tile_colour(move):
    """Smooth colour for a move: deeper green the more it rose, deeper red the more it fell."""
    strength = min(abs(move), 10) / 10
    if abs(move) < 0.5:
        return "rgba(255, 255, 255, 0.05)"
    rgb = "61, 220, 132" if move > 0 else "255, 42, 61"
    return f"rgba({rgb}, {0.10 + 0.55 * strength:.2f})"


def _heat_map(changes):
    subtitle("Heat map: one-month performance")
    how_to_read("Every market Krypton follows, grouped by sector: company shares first, then commodities, indices "
                "and currencies. <b>Green</b> = up this month, <b>red</b> = down. The deeper the colour, the bigger "
                "the move.")
    cards = []
    for sector, markets in SECTORS.items():
        rows = [(name, changes[name]) for name in markets
                if name in changes and changes[name].get("1 month (%)") is not None]
        if not rows:
            continue
        rows.sort(key=lambda r: -r[1]["1 month (%)"])
        average = sum(c["1 month (%)"] for _, c in rows) / len(rows)
        tiles = "".join(
            f"<div class='tile' style='background:{_tile_colour(c['1 month (%)'])}' "
            f"title='{html.escape(label(name))}: {c['Price']:,.2f} ({c['1 month (%)']:+.1f}% this month)'>"
            f"<span class='tile-ticker'>{html.escape(ticker(name))}</span>"
            f"<span class='tile-name'>{html.escape(FULL_NAME.get(name, name))}</span>"
            f"<span class='tile-move'>{c['1 month (%)']:+.1f}%</span></div>" for name, c in rows)
        tone = "good" if average >= 0 else "bad"
        kind = "" if sector in EQUITY_SECTORS else " heat-other"
        cards.append(f"<div class='heat-sector{kind}'><div class='heat-head'><span>{html.escape(sector)}</span>"
                     f"<span class='stat-delta {tone}'>{average:+.1f}% avg</span></div>"
                     f"<div class='heat-tiles'>{tiles}</div></div>")
    legend = ("<div class='heat-legend'><span>−10%</span><div class='heat-scale'></div><span>+10%</span></div>")
    st.markdown(f"{legend}<div class='heat-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _movers(changes):
    subtitle("Biggest movers this week")
    how_to_read("The biggest price changes over the last 5 trading days.")
    weekly = sorted(((name, c["1 week (%)"]) for name, c in changes.items() if c.get("1 week (%)") is not None),
                    key=lambda kv: kv[1])
    if not weekly:
        st.caption("No weekly data yet.")
        return
    up, down = st.columns(2)
    with up:
        st.markdown("**Biggest gains**")
        stat_cards([{"label": label(name), "value": f"{move:+.1f}%", "tone": "good",
                     "explain": f"Price now {changes[name]['Price']:,.2f}. This month: "
                                f"{describe_move(changes[name]['1 month (%)'])}."}
                    for name, move in reversed(weekly[-4:])], per_row=2)
    with down:
        st.markdown("**Biggest losses**")
        stat_cards([{"label": label(name), "value": f"{move:+.1f}%", "tone": "bad",
                     "explain": f"Price now {changes[name]['Price']:,.2f}. This month: "
                                f"{describe_move(changes[name]['1 month (%)'])}."}
                    for name, move in weekly[:4]], per_row=2)


def _explorer(prices, changes):
    subtitle("Price history")
    how_to_read("Pick any market to see its price over the last year.")
    left, right = st.columns([3, 2])
    with left:
        a, b = st.columns(2)
        sector = a.selectbox("Sector", list(SECTORS), key="explore_sector")
        options = [m for m in SECTORS[sector] if m in prices.columns]
        market = b.selectbox("Market", options, key="explore_market", format_func=label)
        line_chart(prices[market], f"{label(market)}: daily price, last 12 months", "Price", colour="#ffb000", height=320,
                   explain="The price at the end of each trading day over the last year.")
    with right:
        moves = {m: (changes.get(m) or {}).get("1 month (%)") for m in SECTORS[sector]}
        risers = sum(1 for v in moves.values() if v is not None and v > 1)
        fallers = sum(1 for v in moves.values() if v is not None and v < -1)
        flat = len(moves) - risers - fallers
        pie_chart(["Up more than 1%", "Down more than 1%", "About flat"], [risers, fallers, flat],
                  f"{sector}: how its markets moved this month", colours=["#3ddc84", "#ff2a3d", "#9a9aa4"],
                  note=f"How many of the {len(moves)} markets in this sector went up, went down, or stayed about "
                       "flat over the last month.")


def markets_tab(state):
    st.markdown("### Markets")
    st.markdown("<div class='lead'>About 120 markets that react to world events: oil, shipping, airlines, defence, "
                "food, metals, tech and more.</div>", unsafe_allow_html=True)
    _heat_map(state["changes"])
    _movers(state["changes"])
    _explorer(state["prices"], state["changes"])
