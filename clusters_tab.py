# clusters_tab.py
# 🧬 The Clusters page: families of markets that move together, across the whole market and inside
# each sector. Every section explains what it shows and how to read it.
# The calculations live in clusters.py; this file only draws the page.

import html

import plotly.graph_objects as go
import streamlit as st

from clusters import TOGETHER, build
from panels import chart_key, how_to_read, stat_cards, subtitle


@st.cache_data(ttl=3600, show_spinner=False)
def _clusters(prices, changes):
    return build(prices, changes)


def _strength(cohesion):
    if cohesion >= 0.7:
        return "very tight"
    if cohesion >= 0.55:
        return "tight"
    if cohesion >= 0.4:
        return "loose"
    return "weak"


def _name(cluster):
    """A readable, unique name: the family's most typical member (+ its main sector for context)."""
    main = max(cluster["sectors"], key=cluster["sectors"].get)
    return main, f"{cluster['anchor']} group", cluster["anchor"]


def _chips(names, highlight=None):
    return "".join(f"<span class='chip{' chip-anchor' if n == highlight else ''}'>{html.escape(n)}</span>"
                   for n in names)


def _sunburst(data, changes):
    subtitle("🌳 The family tree: sectors → sub-clusters → markets")
    how_to_read(
        "Start in the centre and move outwards. The <b>inner ring</b> is the 12 sectors. The <b>middle ring</b> splits "
        "each sector into <b>sub-clusters</b>: markets inside that sector that really move together. The <b>outer "
        "ring</b> is each market. <b>Colour</b> = how it moved this month (green up, red down). "
        "<b>Click</b> any slice to zoom in; click the centre to zoom back out.")
    ids, labels, parents, colours, hovers = ["all"], ["All markets"], [""], [0], ["All markets"]
    for sector, info in data["sectors"].items():
        ids.append(sector)
        labels.append(sector)
        parents.append("all")
        colours.append(0)
        hovers.append(f"{sector}: moves together {info['cohesion'] * 100:.0f}/100 on average")
        for i, sub in enumerate(info["subclusters"]):
            sub_id = f"{sector}|{i}"
            single = len(sub["members"]) == 1
            ids.append(sub_id)
            labels.append(sub["members"][0] if single else f"{sub['anchor']} & co")
            parents.append(sector)
            colours.append(sub["month"] or 0)
            hovers.append(("Moves on its own" if single else
                           f"{len(sub['members'])} markets · move together {sub['cohesion'] * 100:.0f}/100")
                          + (f" · {sub['month']:+.1f}% this month" if sub["month"] is not None else ""))
            if single:
                continue
            for m in sub["members"]:
                move = changes.get(m, {}).get("1 month (%)")
                ids.append(f"{sub_id}|{m}")
                labels.append(m)
                parents.append(sub_id)
                colours.append(move or 0)
                hovers.append(f"{m}: {move:+.1f}% this month" if move is not None else m)
    figure = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, hovertext=hovers, hoverinfo="text",
        marker=dict(colors=[max(-12, min(12, c)) for c in colours], cmid=0,
                    colorscale=[[0, "#c1121f"], [0.5, "#1b1418"], [1, "#1f9d5c"]],
                    line=dict(color="#060608", width=1.5)),
        insidetextorientation="radial", maxdepth=3, textfont=dict(family="Inter, sans-serif", color="#f2f2f5")))
    figure.update_layout(height=640, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(figure, width="stretch", key=chart_key("sunburst"))


def _market_wide(data):
    subtitle("🔗 Clusters across the whole market")
    how_to_read(
        "These families were found <b>without looking at sectors</b>: only at how prices actually moved. "
        "Each family is named after its <b>most typical member</b> (the highlighted chip). <b>Move together</b> is "
        "the average link inside the family: <b>100</b> = they always move identically, <b>0</b> = no link. "
        "When a family "
        "<b>spans several sectors</b>, it reveals a hidden link (for example, a country's stock market moving with "
        "the metals it exports).")
    families = [c for c in data["market_wide"] if len(c["members"]) > 1]
    cards = []
    for c in families:
        main, title, anchor = _name(c)
        icon = main.split(" ", 1)[0]
        spans = ""
        if len(c["sectors"]) > 1:
            spans = ("<div class='cluster-spans'>🔀 Spans " + ", ".join(
                f"{html.escape(s.split(' ', 1)[-1])} ({n})" for s, n in c["sectors"].items()) + "</div>")
        move = ""
        if c["month"] is not None:
            move = (f"<span class='stat-delta {'good' if c['month'] >= 0 else 'bad'}'>"
                    f"{c['month']:+.1f}% this month</span>")
        cards.append(
            f"<div class='cluster-card'><div class='cluster-head'><span class='cluster-title'>{icon} "
            f"{html.escape(title)}</span>{move}</div>"
            f"<div class='cluster-meta'>Mostly {html.escape(main.split(' ', 1)[-1])} · {len(c['members'])} markets · move together "
            f"<b>{c['cohesion'] * 100:.0f}/100</b> ({_strength(c['cohesion'])})</div>"
            f"<div class='bar'><div style='width:{max(0, c['cohesion']) * 100:.0f}%'></div></div>"
            f"<div class='chips'>{_chips(c['members'], anchor)}</div>{spans}</div>")
    st.markdown(f"<div class='cluster-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)

    loners = [c["members"][0] for c in data["market_wide"] if len(c["members"]) == 1]
    if loners:
        subtitle("🐺 Lone wolves: markets that move on their own")
        how_to_read(
            "These markets didn't move closely enough with any other to join a family. They follow their own "
            "news: a single crop's harvest, one company's results, or a local event. That makes them useful for "
            "spreading risk, because they rarely all fall at once.")
        st.markdown(f"<div class='chips'>{_chips(loners)}</div>", unsafe_allow_html=True)


def _sector_dive(data):
    subtitle("🔬 Inside a sector")
    how_to_read(
        "Pick a sector to see how its markets are linked. In the grid, each square is <b>one pair of markets</b>: "
        "<b>bright red</b> = they move almost identically, <b>dark</b> = unrelated, <b>blue</b> = they tend to move "
        "in <b>opposite</b> directions. Markets are ordered by sub-cluster, so bright blocks along the diagonal "
        "are the sub-clusters listed beside it.")
    sector = st.selectbox("Sector", list(data["sectors"]), key="cluster_sector")
    info = data["sectors"][sector]
    left, right = st.columns([3, 2], gap="large")
    with left:
        matrix = info["matrix"]
        figure = go.Figure(go.Heatmap(
            z=matrix.values, x=list(matrix.columns), y=list(matrix.index), zmin=-1, zmax=1,
            colorscale=[[0, "#2f6fed"], [0.5, "#0d0b0e"], [0.75, "#7a0c19"], [1, "#ff2a3d"]],
            hovertemplate="%{y} & %{x}: %{z:.2f}<extra></extra>", xgap=2, ygap=2,
            colorbar=dict(title="Link", tickvals=[-1, 0, 1], ticktext=["opposite", "none", "identical"])))
        figure.update_layout(template="plotly_dark", height=max(360, 34 * len(matrix) + 120),
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Inter, sans-serif", color="#a3a3ae"),
                             xaxis=dict(tickangle=-40, showgrid=False), yaxis=dict(autorange="reversed", showgrid=False))
        st.plotly_chart(figure, width="stretch", key=chart_key("corr"))
    with right:
        families = [s for s in info["subclusters"] if len(s["members"]) > 1]
        stat_cards([
            {"label": "How together this sector moves", "value": f"{info['cohesion'] * 100:.0f}/100",
             "explain": "The average link between every pair of markets in the sector. High = the whole sector tends "
                        "to rise and fall as one; low = it's really several different businesses."},
            {"label": "Sub-clusters found", "value": len(families),
             "explain": "Groups of 2+ markets in this sector that move closely together (listed below)."},
        ], per_row=1)
        for s in families:
            st.markdown(f"<div class='cluster-card'><div class='cluster-meta'><b>{html.escape(s['anchor'])} & co</b> · "
                        f"move together {s['cohesion'] * 100:.0f}/100 ({_strength(s['cohesion'])})</div>"
                        f"<div class='chips'>{_chips(s['members'], s['anchor'])}</div></div>", unsafe_allow_html=True)
        solo = [s["members"][0] for s in info["subclusters"] if len(s["members"]) == 1]
        if solo:
            st.caption("Move on their own within this sector: " + ", ".join(solo) + ".")


def clusters_tab(state):
    st.markdown("### 🧬 Clusters")
    how_to_read(
        "Some markets rise and fall <b>together</b>, because the same things drive them (oil companies and the oil "
        "price, airlines and cruise lines). Krypton compares every market's daily ups and downs over the last year "
        "with every other market's, and groups the ones that move alike into <b>clusters</b>. Inside each sector it "
        "also finds smaller <b>sub-clusters</b>. Two markets join only if their moves were at least "
        f"<b>{TOGETHER * 100:.0f}/100</b> alike.", "What are clusters?")
    with st.spinner("Comparing every market with every other market..."):
        data = _clusters(state["prices"], state["changes"])
    families = [c for c in data["market_wide"] if len(c["members"]) > 1]
    tightest = max(families, key=lambda c: c["cohesion"]) if families else None
    stat_cards([
        {"label": "Markets compared", "value": len(data["corr"]),
         "explain": f"Every pair of them: {len(data['corr']) * (len(data['corr']) - 1) // 2:,} comparisons."},
        {"label": "Families found", "value": len(families),
         "explain": "Groups of 2 or more markets that move together, across the whole market."},
        {"label": "Lone wolves", "value": len(data["market_wide"]) - len(families),
         "explain": "Markets that don't move closely with any other."},
        {"label": "Tightest family", "value": f"{tightest['cohesion'] * 100:.0f}/100" if tightest else "n/a",
         "explain": f"The {_name(tightest)[1]}: its markets move almost as one." if tightest else ""},
    ], per_row=4)
    _market_wide(data)
    _sunburst(data, state["changes"])
    _sector_dive(data)
    subtitle("💡 Why clusters matter")
    how_to_read(
        "Owning five stocks from the <b>same cluster</b> is a bit like owning one big bet: when that family has a bad "
        "day, they usually all fall together. Spreading across <b>different clusters</b> (or lone wolves) is how "
        "investors reduce that risk. Clusters can change over time, especially in a crisis, when many markets "
        "suddenly start moving together.", "Why this matters")
    st.caption("Based on daily closing prices over the last 12 months. For learning only, not financial advice.")
