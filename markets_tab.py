# markets_tab.py
# 📈 The Markets page: every market Krypton follows, at a glance.
#   - Heat map: all ~120 markets grouped by sector, coloured by this month's move
#   - Biggest movers this week
#   - Price explorer (any market, last 12 months) + how a whole sector moved
#   - Every market as a card with its week / month / year moves

import plotly.graph_objects as go
import streamlit as st

from analysis import describe_move
from markets import SECTORS
from panels import chart_key, line_chart, pie_chart, stat_cards, subtitle


def _heat_map(changes):
    subtitle("🗺️ Heat map: every market, this month")
    labels, parents, colours, texts = [], [], [], []
    for sector, markets in SECTORS.items():
        labels.append(sector)
        parents.append("")
        colours.append(0)
        texts.append("")
        for name in markets:
            month = (changes.get(name) or {}).get("1 month (%)")
            if month is None:
                continue
            labels.append(name)
            parents.append(sector)
            colours.append(max(-15, min(15, month)))
            texts.append(f"{month:+.1f}%")
    figure = go.Figure(go.Treemap(
        labels=labels, parents=parents, text=texts, values=[1] * len(labels), branchvalues="remainder",
        marker=dict(colors=colours, colorscale=[[0, "#b3001b"], [0.5, "#1a1418"], [1, "#0f9d58"]], cmid=0,
                    line=dict(color="#060608", width=2)),
        texttemplate="<b>%{label}</b><br>%{text}", hovertemplate="%{label}: %{text}<extra></extra>",
        textfont=dict(family="Inter, sans-serif", color="#ffffff"), tiling=dict(pad=3)))
    figure.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(figure, width="stretch", key=chart_key("heatmap"))
    st.caption("ⓘ Each box is one market, grouped by sector. Green = up over the last month, red = down; the "
               "stronger the colour, the bigger the move. Click a sector to zoom in, click its title to zoom out.")


def _movers(changes):
    subtitle("⚡ Biggest movers this week")
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
    st.caption("ⓘ The change in price over the last 5 trading days. Big weekly moves often follow news: "
               "check the 🌍 World map for events that touch these markets.")


def _explorer(prices, changes):
    subtitle("🔎 Explore a market")
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
