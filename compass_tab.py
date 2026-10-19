# compass_tab.py
# 🧭 The Market Compass page: today's "market weather", next-month odds from 18 years of history,
# the six signals behind the reading, sectors, world risk, and an honest "how reliable is this?".
# The calculations live in compass.py; this file only draws the page.

import html

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from compass import LEAN, READINGS, SIGNALS, reading
from panels import GRID, chart_key, stat_cards, subtitle
from severity import SEVERITY


def _gauge(score, colour):
    """A slim bar from -100 (stormy) to +100 (calm) with a marker at today's score."""
    left = (score + 100) / 2
    return (f"<div class='gauge'><div class='gauge-fill'></div>"
            f"<div class='gauge-mark' style='left:{left:.1f}%;background:{colour};box-shadow:0 0 14px {colour}'></div></div>"
            "<div class='gauge-labels'><span>⛈️ Stormy −100</span><span>⛅ Choppy</span><span>☀️ Calm +100</span></div>")


def _hero(compass, name):
    info = READINGS[name]
    score = compass["today"]["Score"]
    week = compass.get("score_week_ago")
    change = ""
    if week is not None:
        diff = score - week
        direction = "better" if diff > 3 else "worse" if diff < -3 else "about the same"
        change = f" · {abs(diff):.0f} points {direction} than a week ago" if direction != "about the same" \
            else " · about the same as a week ago"
    st.markdown(
        f"<div class='hero' style='--accent:{info['colour']}'>"
        f"<div class='hero-kicker'>🧭 MARKET WEATHER · US STOCK MARKET (S&amp;P 500)</div>"
        f"<div class='hero-main'><span class='hero-icon'>{info['icon']}</span>"
        f"<span class='hero-reading' style='color:{info['colour']}'>{name}</span>"
        f"<span class='hero-score'>score {score:+.0f}</span></div>"
        f"<div class='hero-meaning'>{info['meaning']}</div>"
        f"{_gauge(score, info['colour'])}"
        f"<div class='hero-foot'>Based on market closes up to {compass['date']:%d %b %Y}{change}.</div>"
        "</div>", unsafe_allow_html=True)


def _odds(compass, name):
    test = compass["test"]
    odds, normal = test["by_reading"][name], test["all"]
    years = test["end"].year - test["start"].year
    subtitle("🔮 The next month: what history says after readings like today's")
    stat_cards([
        {"label": "Chance the market is higher in a month", "value": f"{odds['up']:.0f}%",
         "delta": f"normal: {normal['up']:.0f}%", "tone": "good" if odds["up"] >= normal["up"] else "bad",
         "explain": f"In the {odds['weeks']} weeks since {test['start'].year} with a '{name}' reading, the S&P 500 "
                    f"was higher one month later this often. Over all weeks it was {normal['up']:.0f}%."},
        {"label": "Typical range for the month", "value": f"{odds['low']:+.1f}% to {odds['high']:+.1f}%",
         "explain": "8 times out of 10, the S&P 500's move over the next month landed inside this range "
                    f"(the average was {odds['avg']:+.1f}%)."},
        {"label": "Chance of a 10% drop", "value": f"{odds['dip10']:.0f}%",
         "delta": f"normal: {normal['dip10']:.0f}%", "tone": "good" if odds["dip10"] <= normal["dip10"] else "bad",
         "explain": "How often the market fell 10% or more at some point during the following month. "
                    "This is where the Compass is most useful."},
        {"label": "Swing traders expect", "value": f"±{compass['month_move']:.1f}%",
         "explain": f"From the VIX 'fear index' ({compass['vix']:.0f} today): the move options traders are pricing "
                    "for the next month, with about a 2-in-3 chance of staying inside it."},
    ])
    st.caption(f"ⓘ All numbers come from {years} years of real S&P 500 history (checked once a week). "
               "The past is a guide, not a promise.")


def _signals(compass):
    subtitle("🔍 The six signals behind the reading")
    cards = []
    for name, info in SIGNALS.items():
        value = compass["today"][name]
        if value > 0.15:
            word, tone, text = "▲ Positive", "good", info["up"]
        elif value < -0.15:
            word, tone, text = "▼ Negative", "bad", info["down"]
        else:
            word, tone, text = "◆ Neutral", None, "Close to its normal level: not pushing either way."
        cards.append({"label": f"{info['icon']} {name}", "value": word, "delta": f"{value * 100:+.0f} of ±100",
                      "tone": tone, "explain": f"{text}<br><span style='color:#6f6f7a'>Measures: {info['what']}</span>"})
    stat_cards(cards, per_row=3)
    st.caption("ⓘ The score is the average of these six signals (each from −100 to +100). Every signal uses only "
               "data that was available on that day, so the history test is fair.")


def _history_chart(compass):
    subtitle("📜 The last two years")
    scores = compass["scores"]["Score"].iloc[-504:]
    sp = compass["sp500"].reindex(scores.index)
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.06)
    figure.add_trace(go.Scatter(x=sp.index, y=sp.values, mode="lines", line=dict(color="#e9e9ee", width=2),
                                name="S&P 500", hovertemplate="%{x|%d %b %Y}: %{y:,.0f}<extra></extra>"), 1, 1)
    colours = ["#3ddc84" if v >= LEAN else "#ff2a3d" if v <= -LEAN else "#ffb000" for v in scores.values]
    figure.add_trace(go.Bar(x=scores.index, y=scores.values, marker_color=colours, name="Compass score",
                            hovertemplate="%{x|%d %b %Y}: %{y:+.0f}<extra></extra>"), 2, 1)
    figure.update_layout(template="plotly_dark", height=430, showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=10),
                         font=dict(family="Inter, sans-serif", color="#8a8a96"), bargap=0)
    figure.update_yaxes(gridcolor=GRID)
    figure.update_xaxes(gridcolor=GRID)
    figure.update_yaxes(title_text="S&P 500", row=1, col=1)
    figure.update_yaxes(title_text="Score", range=[-100, 100], row=2, col=1)
    st.plotly_chart(figure, width="stretch", key=chart_key("compass_history"))
    st.caption("ⓘ Top: the S&P 500's price. Bottom: the Compass score each day (green = calm uptrend, amber = choppy, "
               "red = stormy). Notice how red stretches line up with the market's rough patches.")


def _sectors(compass):
    subtitle("🧩 Which parts of the market are leading")
    sectors = sorted(compass["sectors"].items(), key=lambda kv: kv[1]["month"])
    figure = go.Figure(go.Bar(
        x=[v["month"] for _, v in sectors], y=[k for k, _ in sectors], orientation="h",
        marker_color=["#3ddc84" if v["month"] >= 0 else "#ff2a3d" for _, v in sectors],
        text=[f"{v['month']:+.1f}%" for _, v in sectors], textposition="outside",
        hovertemplate="%{y}: %{x:+.1f}% this month<extra></extra>"))
    figure.update_layout(template="plotly_dark", height=330, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=40, t=10, b=10),
                         font=dict(family="Inter, sans-serif", color="#a3a3ae"),
                         xaxis=dict(gridcolor=GRID, title="Change over the last month (%)", zeroline=True,
                                    zerolinecolor="#55555f",
                                    # room on both sides so the "+6.5%" / "-1.3%" labels never hit the names
                                    range=[min(0, min(v["month"] for _, v in sectors)) * 1.35 - 1.5,
                                           max(0, max(v["month"] for _, v in sectors)) * 1.2 + 1.5]))
    figure.update_traces(cliponaxis=False)
    st.plotly_chart(figure, width="stretch", key=chart_key("compass_sectors"))
    rising = sum(1 for v in compass["sectors"].values() if v["above_avg"])
    st.caption(f"ⓘ How the 9 big US sector funds moved over the last month. {rising} of 9 are above their "
               "50-day average. When defensive sectors (Utilities, Everyday goods, Healthcare) lead, investors "
               "are usually playing safe; when Technology and Shopping & leisure lead, they're feeling bold.")


def _world(state):
    subtitle("🌍 World risk right now (from Krypton's live map)")
    serious = sorted([e for e in state["events"] if e["severity"] in ("Critical", "High")],
                     key=lambda e: -SEVERITY[e["severity"]]["rank"])
    if not serious:
        st.markdown("No Critical or High events on the map right now.")
    else:
        st.markdown("\n".join(f"- **{html.escape(e['name'])}** · {e['category']} · {e['severity']}"
                              for e in serious[:5]))
    st.caption(f"ⓘ {len(serious)} serious events on the map. These are NOT part of the score: in Krypton's own "
               "tests, single world events rarely changed the whole market's direction for long. They matter most "
               "for the specific stocks they touch (see 🌍 World map and 💼 My portfolio).")


def _reliability(compass):
    subtitle("🎯 How reliable is the Compass?")
    test = compass["test"]
    calm, stormy = test["by_reading"].get("Calm uptrend"), test["by_reading"].get("Stormy")
    good, bad = st.columns(2)
    with good:
        st.success("**✅ Good at: warning you about rough months.**\n\n"
                   + (f"After stormy readings, a 10% drop came {stormy['dip10']:.0f}% of the time, vs "
                      f"{calm['dip10']:.0f}% after calm ones, and daily swings were "
                      f"{stormy['swings'] / calm['swings']:.1f}× bigger." if calm and stormy else ""))
    with bad:
        st.warning("**❌ Not good at: calling up or down.**\n\n"
                   + (f"After stormy readings the market still rose {stormy['up']:.0f}% of the time (it often "
                      "bounces after a fall). Nobody can reliably predict next month's direction from public data."
                      if stormy else ""))
    rows = ["<table class='ktable'><tr><th>Reading</th><th>Weeks</th><th>Market higher a month later</th>"
            "<th>Average move</th><th>Typical range</th><th>Fell 10%+ during the month</th><th>How bumpy</th></tr>"]
    for name, s in list(test["by_reading"].items()) + [("All weeks", test["all"])]:
        icon = READINGS[name]["icon"] if name in READINGS else "📊"
        rows.append(f"<tr><td>{icon} {name}</td><td>{s['weeks']}</td><td>{s['up']:.0f}%</td><td>{s['avg']:+.1f}%</td>"
                    f"<td>{s['low']:+.1f}% to {s['high']:+.1f}%</td><td>{s['dip10']:.0f}%</td>"
                    f"<td>{s['swings']:.0f}%</td></tr>")
    st.markdown("".join(rows) + "</table>", unsafe_allow_html=True)
    st.caption(f"ⓘ Every week from {test['start']:%b %Y} to {test['end']:%b %Y}: the reading that day, and what the "
               "S&P 500 did over the next month. 'How bumpy' = the yearly-rate size of daily swings (bigger = rougher).")


def compass_tab(state, user):
    compass = state.get("compass")
    if not compass:
        st.warning("The Market Compass couldn't load its market data right now. Please try again in a few minutes.")
        return
    name = reading(compass["today"]["Score"])
    _hero(compass, name)
    _odds(compass, name)
    _signals(compass)
    _history_chart(compass)
    left, right = st.columns([3, 2])
    with left:
        _sectors(compass)
    with right:
        _world(state)
    _reliability(compass)
    with st.expander("📊 Krypton's event arrows: track record (▲/▼ on stocks linked to world events)"):
        from tabs_extra import track_record_tab
        track_record_tab()
    st.caption("🧭 The Market Compass describes market conditions using public data. It is for learning only and is "
               "not financial advice: it doesn't tell you to buy or sell anything.")
