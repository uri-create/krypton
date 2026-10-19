# clusters_tab.py
# 🧬 The Market Teams page: which markets move together, shown as simply as possible.
#   - Teams: groups of 3+ markets that keep rising and falling together
#   - Pairs: two markets that move together
#   - Find a market's teammates: pick any market, see which ones move most like it
#   - Loners: markets that follow their own path
# The calculations live in clusters.py; this file only draws the page.

import html

import streamlit as st

from clusters import build, buddies
from panels import how_to_read, subtitle


@st.cache_data(ttl=3600, show_spinner=False)
def _teams(prices, changes):
    return build(prices, changes)


def _closeness(together):
    """Plain words for 'moved the same way on X% of days' (50% = no link at all, like a coin flip)."""
    if together is None:
        return "unknown", 0
    if together >= 80:
        return "very close", together
    if together >= 70:
        return "close", together
    return "loose", together


def _meter(together):
    """A bar from 50% (no link) to 100% (always together)."""
    fill = max(0, min(100, (together - 50) * 2)) if together else 0
    return f"<div class='bar'><div style='width:{fill:.0f}%'></div></div>"


def _chips(names, limit=8, highlight=None):
    shown = "".join(f"<span class='chip{' chip-anchor' if n == highlight else ''}'>{html.escape(n)}</span>"
                    for n in names[:limit])
    if len(names) > limit:
        shown += f"<span class='chip chip-more'>+{len(names) - limit} more</span>"
    return f"<div class='chips'>{shown}</div>"


def _team_card(team):
    word, together = _closeness(team["together"])
    move = ""
    if team["month"] is not None:
        move = (f"<span class='stat-delta {'good' if team['month'] >= 0 else 'bad'}'>"
                f"{team['month']:+.1f}% this month</span>")
    return (f"<div class='cluster-card'><div class='cluster-head'><span class='cluster-title'>{team['icon']} "
            f"{html.escape(team['name'])}</span>{move}</div>"
            f"<div class='cluster-meta'><b>{len(team['members'])} markets</b> that moved the same way on "
            f"<b>{together:.0f}% of days</b> ({word})</div>{_meter(together)}"
            f"{_chips(team['members'], highlight=team['anchor'])}</div>")


def clusters_tab(state):
    st.markdown("### 🧬 Market teams")
    st.markdown("<div class='lead'>Some markets move as a <b>team</b>: when one goes up, the others usually go up "
                "too. Krypton compared a year of daily price moves for every market and found these teams.</div>",
                unsafe_allow_html=True)
    with st.spinner("Comparing every market with every other market..."):
        data = _teams(state["prices"], state["changes"])

    subtitle("👥 The teams")
    how_to_read("The <b>%</b> is how often the team's markets moved the <b>same direction on the same day</b>. "
                "50% would mean no link at all (like a coin flip); the closer to 100%, the tighter the team. "
                "The <b>highlighted</b> market is the one most typical of the team.")
    st.markdown(f"<div class='cluster-grid'>{''.join(_team_card(t) for t in data['teams'])}</div>",
                unsafe_allow_html=True)

    if data["pairs"]:
        subtitle("👫 Pairs that move together")
        rows = "".join(
            f"<div class='pair-row'><span>{html.escape(p['members'][0])} <span class='muted'>&amp;</span> "
            f"{html.escape(p['members'][1])}</span><span class='pair-pct'>same way on "
            f"<b>{p['together']:.0f}%</b> of days</span></div>" for p in data["pairs"] if p["together"])
        st.markdown(f"<div class='pair-list'>{rows}</div>", unsafe_allow_html=True)

    subtitle("🔎 Find a market's teammates")
    how_to_read("Pick any market to see the 5 markets that move most like it.")
    markets = sorted(data["corr"].columns)
    default = markets.index("Brent oil") if "Brent oil" in markets else 0
    chosen = st.selectbox("Market", markets, index=default, label_visibility="collapsed")
    team = data["team_of"].get(chosen)
    if team:
        st.markdown(f"**{chosen}** is in the **{team['icon']} {team['name']}**." if len(team["members"]) > 2
                    else f"**{chosen}** moves as a pair with **{[m for m in team['members'] if m != chosen][0]}**.")
    else:
        st.markdown(f"**{chosen}** is a loner: it doesn't move closely with any other market.")
    rows = "".join(
        f"<div class='buddy'><span class='buddy-name'>{html.escape(other)}</span>"
        f"<div class='buddy-bar'><div style='width:{max(0, min(100, ((pct or 50) - 50) * 2)):.0f}%'></div></div>"
        f"<span class='buddy-pct'>{pct:.0f}%</span></div>"
        for other, pct in buddies(data, chosen) if pct is not None)
    st.markdown(f"<div class='buddies'>{rows}</div>", unsafe_allow_html=True)
    st.caption(f"% = how often each one moved the same direction as {chosen} on the same day.")

    subtitle("🐺 Loners")
    how_to_read("These markets don't move closely with any other. They follow their own news, so they rarely all "
                "fall at once.")
    st.markdown(_chips(data["loners"], limit=60), unsafe_allow_html=True)

    subtitle("💡 Why this matters")
    st.markdown("<div class='lead'>Owning five markets from the <b>same team</b> is a bit like owning one big bet: "
                "when the team has a bad day, they usually all fall together. Mixing <b>different teams</b> spreads "
                "the risk.</div>", unsafe_allow_html=True)
    st.caption("Based on daily closing prices over the last 12 months. For learning only, not financial advice.")
