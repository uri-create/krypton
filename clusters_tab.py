# clusters_tab.py
# The Clusters page: which markets move together, shown as simply as possible.
#   - Clusters: groups of 3+ markets that keep rising and falling together
#   - Pairs: two markets that move together
#   - Find a market's closest matches: pick any market, see which ones move most like it
#   - Independent markets: ones that follow their own path
# Every market is shown by its official name and ticker, e.g. "Exxon Mobil Corporation (XOM)".
# The calculations live in clusters.py; this file only draws the page.

import html

import streamlit as st

from clusters import build, buddies
from markets import label
from panels import how_to_read, subtitle


@st.cache_data(ttl=3600, show_spinner=False)
def _clusters(prices, changes):
    return build(prices, changes)


def _closeness(together):
    """Plain words for 'moved the same way on X% of days' (50% = no link at all, like a coin flip)."""
    if together is None:
        return "unknown"
    if together >= 80:
        return "very strong"
    if together >= 70:
        return "strong"
    return "moderate"


def _meter(together):
    """A bar from 50% (no link) to 100% (always together)."""
    fill = max(0, min(100, (together - 50) * 2)) if together else 0
    return f"<div class='bar'><div style='width:{fill:.0f}%'></div></div>"


def _chips(names, limit=8, highlight=None):
    shown = "".join(f"<span class='chip{' chip-anchor' if n == highlight else ''}'>{html.escape(label(n))}</span>"
                    for n in names[:limit])
    if len(names) > limit:
        shown += f"<span class='chip chip-more'>+{len(names) - limit} more</span>"
    return f"<div class='chips'>{shown}</div>"


def _cluster_card(cluster):
    together = cluster["together"] or 0
    move = ""
    if cluster["month"] is not None:
        move = (f"<span class='stat-delta {'good' if cluster['month'] >= 0 else 'bad'}'>"
                f"{cluster['month']:+.1f}% this month</span>")
    mixed = ""
    if cluster["mixed"]:
        mixed = ("<div class='cluster-spans'>Includes markets from: "
                 + ", ".join(html.escape(s) for s in cluster["sectors"]) + "</div>")
    return (f"<div class='cluster-card'><div class='cluster-head'><span class='cluster-title'>"
            f"{html.escape(cluster['name'])}</span>{move}</div>"
            f"<div class='cluster-meta'><b>{len(cluster['members'])} markets</b> that moved the same direction on "
            f"<b>{together:.0f}% of days</b> ({_closeness(cluster['together'])} link)</div>{_meter(together)}"
            f"{_chips(cluster['members'], highlight=cluster['anchor'])}{mixed}</div>")


def clusters_tab(state):
    st.markdown("### Clusters")
    st.markdown("<div class='lead'>Some markets move as a group: when one goes up, the others usually go up too. "
                "Krypton compared a year of daily price moves for every market and grouped the ones that move "
                "together into <b>clusters</b>.</div>", unsafe_allow_html=True)
    with st.spinner("Comparing every market with every other market..."):
        data = _clusters(state["prices"], state["changes"])

    subtitle("The clusters")
    how_to_read("The <b>%</b> is how often the cluster's markets moved the <b>same direction on the same day</b>. "
                "50% would mean no link at all; the closer to 100%, the stronger the link. "
                "The <b>highlighted</b> market is the one most typical of the cluster.")
    st.markdown(f"<div class='cluster-grid'>{''.join(_cluster_card(c) for c in data['clusters'])}</div>",
                unsafe_allow_html=True)

    if data["pairs"]:
        subtitle("Pairs that move together")
        rows = "".join(
            f"<div class='pair-row'><span>{html.escape(label(p['members'][0]))} <span class='muted'>&amp;</span> "
            f"{html.escape(label(p['members'][1]))}</span><span class='pair-pct'>same direction on "
            f"<b>{p['together']:.0f}%</b> of days</span></div>" for p in data["pairs"] if p["together"])
        st.markdown(f"<div class='pair-list'>{rows}</div>", unsafe_allow_html=True)

    subtitle("Find a market's closest matches")
    how_to_read("Pick any market to see the 5 markets that move most like it.")
    markets = sorted(data["corr"].columns, key=label)
    default = markets.index("Brent oil") if "Brent oil" in markets else 0
    chosen = st.selectbox("Market", markets, index=default, format_func=label, label_visibility="collapsed")
    group = data["cluster_of"].get(chosen)
    if group and len(group["members"]) > 2:
        st.markdown(f"**{label(chosen)}** belongs to the **{group['name']}**.")
    elif group:
        partner = [m for m in group["members"] if m != chosen][0]
        st.markdown(f"**{label(chosen)}** moves as a pair with **{label(partner)}**.")
    else:
        st.markdown(f"**{label(chosen)}** is independent: it doesn't move closely with any other market.")
    rows = "".join(
        f"<div class='buddy'><span class='buddy-name'>{html.escape(label(other))}</span>"
        f"<div class='buddy-bar'><div style='width:{max(0, min(100, ((pct or 50) - 50) * 2)):.0f}%'></div></div>"
        f"<span class='buddy-pct'>{pct:.0f}%</span></div>"
        for other, pct in buddies(data, chosen) if pct is not None)
    st.markdown(f"<div class='buddies'>{rows}</div>", unsafe_allow_html=True)
    st.caption(f"% = how often each one moved the same direction as {label(chosen)} on the same day.")

    subtitle("Independent markets")
    how_to_read("These markets don't move closely with any other. They follow their own news, so they rarely all "
                "fall at once.")
    st.markdown(_chips(data["loners"], limit=60), unsafe_allow_html=True)

    subtitle("Why this matters")
    st.markdown("<div class='lead'>Owning five markets from the <b>same cluster</b> is a bit like owning one big bet: "
                "when the cluster has a bad day, they usually all fall together. Holding markets from "
                "<b>different clusters</b> spreads the risk.</div>", unsafe_allow_html=True)
    st.caption("Based on daily closing prices over the last 12 months. For learning only, not financial advice.")
