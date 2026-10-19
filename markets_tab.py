# markets_tab.py
# 📈 The Markets page: every market Krypton follows, at a glance.
#   - Heat map: all ~120 markets as rounded tiles grouped by sector, coloured by this month's move
#   - Biggest movers this week
#   - Price explorer (any market, last 12 months) + how a whole sector moved
#   - Every market as a card with its week / month / year moves

import html

import streamlit as st

from analysis import describe_move
from markets import SECTORS
from panels import how_to_read, line_chart, pie_chart, stat_cards, subtitle


def _tile_colour(move):
    """Smooth colour for a move: deeper green the more it rose, deeper red the more it fell."""
    strength = min(abs(move), 10) / 10
    if abs(move) < 0.5:
        return "rgba(255, 255, 255, 0.05)"
    rgb = "61, 220, 132" if move > 0 else "255, 42, 61"
    return f"rgba({rgb}, {0.10 + 0.55 * strength:.2f})"


def _heat_map(changes):
    subtitle("🗺️ Heat map: every market, this month")
    how_to_read(
        "Each tile is one market, grouped by sector and sorted from best to worst. <b>Green</b> = its price rose "
        "over the last month, <b>red</b> = it fell; the <b>deeper the colour</b>, the bigger the move (full colour = "
        "10% or more). The pill next to each sector is that sector's average move. Hover a tile to see its price.")
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
            f"title='{html.escape(name)}: {c['Price']:,.2f} ({c['1 month (%)']:+.1f}% this month)'>"
            f"<span class='tile-name'>{html.escape(name)}</span>"
            f"<span class='tile-move'>{c['1 month (%)']:+.1f}%</span></div>" for name, c in rows)
        tone = "good" if average >= 0 else "bad"
        cards.append(f"<div class='heat-sector'><div class='heat-head'><span>{html.escape(sector)}</span>"
                     f"<span class='stat-delta {tone}'>{average:+.1f}% avg</span></div>"
                     f"<div class='heat-tiles'>{tiles}</div></div>")
    legend = ("<div class='heat-legend'><span>−10%</span><div class='heat-scale'></div><span>+10%</span></div>")
    st.markdown(f"{legend}<div class='heat-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _movers(changes):
    subtitle("⚡ Biggest movers this week")
    how_to_read("The markets whose price changed the most over the last <b>5 trading days</b>, up and down. "
                "Big weekly moves usually follow news: check the 🌍 World map for events that touch them.")
    weekly = sorted(((name, c["1 week (%)"]) for name, c in changes.items() if c.get("1 week (%)") is not None),
                    key=lambda kv: kv[1])
    if not weekly:
        st.caption("No weekly data yet.")
        return
    up, down = st.columns(2)
    with up:
        st.markdown("**▲ Rose the most**")
        stat_cards([{"label": name, "value": f"{move:+.1f}%", "tone": "good",
                     "explain": f"Price now {changes[name]['Price']:,.2f}. This month: "
                                f"{describe_move(changes[name]['1 month (%)'])}."}
                    for name, move in reversed(weekly[-4:])], per_row=2)
    with down:
        st.markdown("**▼ Fell the most**")
        stat_cards([{"label": name, "value": f"{move:+.1f}%", "tone": "bad",
                     "explain": f"Price now {changes[name]['Price']:,.2f}. This month: "
                                f"{describe_move(changes[name]['1 month (%)'])}."}
                    for name, move in weekly[:4]], per_row=2)


def _explorer(prices, changes):
    subtitle("🔎 Explore a market")
    how_to_read("Pick a sector and a market to see its daily price over the last year. The ring on the right shows "
                "how many markets in that sector went up, went down or stayed flat this month.")
    left, right = st.columns([3, 2])
    with left:
        a, b = st.columns(2)
        sector = a.selectbox("Sector", list(SECTORS), key="explore_sector")
        options = [m for m in SECTORS[sector] if m in prices.columns]
        market = b.selectbox("Market", options, key="explore_market")
        line_chart(prices[market], f"{market}: daily price, last 12 months", "Price", colour="#ffb000", height=320,
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


def _all_markets(changes):
    subtitle("📋 Every market, sector by sector")
    how_to_read("Each card shows a market's <b>latest price</b> (big number), its move <b>this month</b> (green = up, "
                "red = down) and its moves over the last week and year.")
    for tab, sector in zip(st.tabs(list(SECTORS)), SECTORS):
        with tab:
            cards = []
            for name in [m for m in SECTORS[sector] if m in changes]:
                c = changes[name]
                month = c["1 month (%)"]
                cards.append({"label": name, "value": f"{c['Price']:,.2f}",
                              "delta": f"{month:+.1f}% this month" if month is not None else None,
                              "tone": "bad" if (month or 0) < 0 else "good",
                              "explain": f"Last week: {describe_move(c['1 week (%)'])} · "
                                         f"last year: {describe_move(c['1 year (%)'])}."})
            stat_cards(cards, per_row=4)


def markets_tab(state):
    st.markdown("### 📈 Markets")
    st.caption("Energy, shipping, airlines, defence, food, metals, tech and more: about 120 markets that react to "
               "world events. Prices are daily closes from Yahoo Finance.")
    _heat_map(state["changes"])
    _movers(state["changes"])
    _explorer(state["prices"], state["changes"])
    _all_markets(state["changes"])
