# compass_tab.py
# 🧭 The Market Compass page: is the US stock market Bullish, Neutral or Bearish right now?
# Next-month odds from 18 years of history, the six signals behind the reading, sectors,
# world risk, and an honest "how reliable is this?". Every section says how to read it.
# The calculations live in compass.py; this file only draws the page.

import html

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from compass import LEAN, READINGS, SIGNALS, reading
from panels import GRID, chart_key, how_to_read, stat_cards, subtitle
from severity import SEVERITY

FONT = dict(family="Inter, sans-serif", color="#8a8a96")


def _gauge(score, colour):
    """A slim bar from -100 (bearish) to +100 (bullish) with a marker at today's score."""
    left = (score + 100) / 2
    return (f"<div class='gauge'><div class='gauge-mark' style='left:{left:.1f}%;background:{colour};"
            f"box-shadow:0 0 14px {colour}'></div></div>"
            "<div class='gauge-labels'><span>🐻 Bearish −100</span><span>⚖️ Neutral 0</span>"
            "<span>🐂 Bullish +100</span></div>")


def _hero(compass, name):
    info = READINGS[name]
    score = compass["today"]["Score"]
    week = compass.get("score_week_ago")
    change = ""
    if week is not None:
        diff = score - week
        change = (f" · {abs(diff):.0f} points {'more bullish' if diff > 0 else 'more bearish'} than a week ago"
                  if abs(diff) > 3 else " · about the same as a week ago")
    legend = "".join(
        f"<div class='legend-item'><span style='color:{r['colour']}'>{r['icon']} <b>{n}</b></span>"
        f"<span class='legend-range'>{r['range']}</span><span class='legend-text'>{r['meaning']}</span></div>"
        for n, r in READINGS.items())
    st.markdown(
        f"<div class='hero' style='--accent:{info['colour']}'>"
        f"<div class='hero-kicker'>🧭 MARKET COMPASS · US STOCK MARKET (S&amp;P 500)</div>"
        f"<div class='hero-main'><span class='hero-icon'>{info['icon']}</span>"
        f"<span class='hero-reading' style='color:{info['colour']}'>{name}</span>"
        f"<span class='hero-score'>score {score:+.0f} / 100</span></div>"
        f"<div class='hero-meaning'>{info['meaning']}</div>"
        f"{_gauge(score, info['colour'])}"
        f"<div class='hero-foot'>Based on market closes up to {compass['date']:%d %b %Y}{change}.</div>"
        f"<div class='legend'>{legend}</div>"
        "</div>", unsafe_allow_html=True)
    how_to_read(
        "The Compass reads <b>six well-known market signals</b> (below) and averages them into one score from "
        "<b>−100</b> to <b>+100</b>. Above +25 the market is <b>Bullish</b> (most signals point up), below −25 it is "
        "<b>Bearish</b> (most point down), in between it is <b>Neutral</b> (they disagree). It describes the market "
        "<b>right now</b>. It is not a promise about the future, and it is not advice to buy or sell.",
        "What is the Market Compass?")


def _odds(compass, name):
    test = compass["test"]
    odds, normal = test["by_reading"][name], test["all"]
    subtitle("🔮 The next month: what history says after readings like today's")
    how_to_read(
        f"Krypton went back through <b>every week since {test['start'].year}</b>, found the weeks with a "
        f"<b>{name}</b> reading like today's, and checked what the S&P 500 really did over the following month. "
        "The <b>'normal'</b> pill shows the same number for all weeks, so you can see if today's reading changes "
        "the odds. These are real past results, not Krypton's guesses.")
    stat_cards([
        {"label": "Chance the market is higher in a month", "value": f"{odds['up']:.0f}%",
         "delta": f"normal: {normal['up']:.0f}%", "tone": "good" if odds["up"] >= normal["up"] else "bad",
         "explain": f"In the {odds['weeks']} past weeks with a {name} reading, the S&P 500 was higher one month "
                    f"later {odds['up']:.0f}% of the time."},
        {"label": "Typical range for the month", "value": f"{odds['low']:+.1f}% to {odds['high']:+.1f}%",
         "explain": "8 times out of 10, the S&P 500's move over the next month landed inside this range "
                    f"(the average was {odds['avg']:+.1f}%)."},
        {"label": "Chance of a 10% drop", "value": f"{odds['dip10']:.0f}%",
         "delta": f"normal: {normal['dip10']:.0f}%", "tone": "good" if odds["dip10"] <= normal["dip10"] else "bad",
         "explain": "How often the market fell 10% or more at some point during the following month. "
                    "This is where the Compass is most useful."},
        {"label": "Move options traders expect", "value": f"±{compass['month_move']:.1f}%",
         "explain": f"From the VIX 'fear index' ({compass['vix']:.0f} today): the size of move traders are paying to "
                    "protect against over the next month (about a 2-in-3 chance of staying inside it)."},
    ])


def _signals(compass):
    subtitle("🔍 The six signals behind the reading")
    how_to_read(
        "Each card is one signal, scored from <b>−100</b> (bearish) to <b>+100</b> (bullish). "
        "<b>▲ Bullish</b> = pushing the market reading up, <b>▼ Bearish</b> = pushing it down, "
        "<b>◆ Neutral</b> = near normal. The big score at the top is simply the <b>average of these six</b>. "
        "When most cards agree, the reading is strong; when they're split, it's Neutral.")
    cards = []
    for name, info in SIGNALS.items():
        value = compass["today"][name]
        if value > 0.15:
            word, tone, text = "▲ Bullish", "good", info["up"]
        elif value < -0.15:
            word, tone, text = "▼ Bearish", "bad", info["down"]
        else:
            word, tone, text = "◆ Neutral", None, "Close to its normal level: not pushing either way."
        cards.append({"label": f"{info['icon']} {name}", "value": word, "delta": f"{value * 100:+.0f} / 100",
                      "tone": tone, "explain": f"{text}<br><span class='muted'>Measures: {info['what']}</span>"})
    stat_cards(cards, per_row=3)


def _history_chart(compass):
    subtitle("📜 The last two years")
    how_to_read(
        "<b>Top:</b> the S&P 500's price. <b>Bottom:</b> the Compass score on each day: <b>green</b> = Bullish, "
        "<b>amber</b> = Neutral, <b>red</b> = Bearish. Look at how the red patches line up with the market's sharp "
        "falls: that's the Compass doing its main job, flagging rough periods.")
    scores = compass["scores"]["Score"].iloc[-504:]
    sp = compass["sp500"].reindex(scores.index)
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.06)
    figure.add_trace(go.Scatter(x=sp.index, y=sp.values, mode="lines", line=dict(color="#e9e9ee", width=2),
                                fill="tozeroy", fillcolor="rgba(233,233,238,0.04)",
                                hovertemplate="%{x|%d %b %Y}: %{y:,.0f}<extra></extra>"), 1, 1)
    colours = ["#3ddc84" if v >= LEAN else "#ff2a3d" if v <= -LEAN else "#ffb000" for v in scores.values]
    figure.add_trace(go.Bar(x=scores.index, y=scores.values, marker_color=colours, marker_line_width=0,
                            hovertemplate="%{x|%d %b %Y}: %{y:+.0f}<extra></extra>"), 2, 1)
    figure.update_layout(template="plotly_dark", height=440, showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=10), font=FONT, bargap=0)
    figure.update_yaxes(gridcolor=GRID, zeroline=False)
    figure.update_xaxes(gridcolor=GRID)
    figure.update_yaxes(title_text="S&P 500", range=[sp.min() * 0.97, sp.max() * 1.02], row=1, col=1)
    figure.update_yaxes(title_text="Score", range=[-100, 100], row=2, col=1)
    st.plotly_chart(figure, width="stretch", key=chart_key("compass_history"))


def _sectors(compass):
    subtitle("🧩 Which parts of the market are leading")
    how_to_read(
        "How the 9 big US sector funds moved over the last month (<b>green</b> = up, <b>red</b> = down). "
        "If <b>defensive</b> sectors lead (Utilities, Everyday goods, Healthcare), investors are usually playing "
        "safe. If <b>bold</b> sectors lead (Technology, Shopping &amp; leisure, Industry), they're confident.")
    sectors = sorted(compass["sectors"].items(), key=lambda kv: kv[1]["month"])
    lo = min(0, min(v["month"] for _, v in sectors))
    hi = max(0, max(v["month"] for _, v in sectors))
    figure = go.Figure(go.Bar(
        x=[v["month"] for _, v in sectors], y=[k for k, _ in sectors], orientation="h",
        marker=dict(color=["#3ddc84" if v["month"] >= 0 else "#ff2a3d" for _, v in sectors], cornerradius=6),
        text=[f"{v['month']:+.1f}%" for _, v in sectors], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+.1f}% this month<extra></extra>"))
    figure.update_layout(template="plotly_dark", height=340, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=50, t=10, b=10),
                         font=dict(family="Inter, sans-serif", color="#a3a3ae"),
                         xaxis=dict(gridcolor=GRID, title="Change over the last month (%)", zeroline=True,
                                    zerolinecolor="#55555f", range=[lo * 1.35 - 1.5, hi * 1.2 + 1.5]))
    st.plotly_chart(figure, width="stretch", key=chart_key("compass_sectors"))
    rising = sum(1 for v in compass["sectors"].values() if v["above_avg"])
    st.caption(f"{rising} of 9 sectors are above their 50-day average price.")


def _world(state):
    subtitle("🌍 World risk right now")
    how_to_read(
        "The most serious events on Krypton's live map (Critical or High). They are <b>not</b> part of the score: "
        "in Krypton's own tests, single world events rarely changed the whole market's direction for long. They "
        "matter most for the specific stocks they touch (see 🌍 World map and 💼 My portfolio).")
    serious = sorted([e for e in state["events"] if e["severity"] in ("Critical", "High")],
                     key=lambda e: -SEVERITY[e["severity"]]["rank"])
    if not serious:
        st.markdown("No Critical or High events on the map right now.")
        return
    rows = "".join(f"<div class='risk-row'><span class='risk-dot' style='background:{e['colour']}'></span>"
                   f"<b>{html.escape(e['name'])}</b><span class='muted'>{e['category']} · {e['severity']}</span></div>"
                   for e in serious[:6])
    st.markdown(f"<div class='risk-list'>{rows}</div>", unsafe_allow_html=True)
    st.caption(f"{len(serious)} serious events on the map in total.")


def _reliability(compass):
    subtitle("🎯 How reliable is the Compass?")
    how_to_read(
        "Every row is one reading. <b>Market higher a month later</b> = how often the S&P 500 had risen one month "
        "later. <b>Typical range</b> = where 8 out of 10 monthly moves landed. <b>Fell 10%+</b> = how often there "
        "was a big drop along the way. <b>How bumpy</b> = the size of daily swings (bigger = rougher). "
        "Compare each row with <b>All weeks</b> to see what the reading really adds.")
    test = compass["test"]
    bull, bear = test["by_reading"].get("Bullish"), test["by_reading"].get("Bearish")
    good, bad = st.columns(2)
    with good:
        st.success("**✅ Good at: warning you about rough months.**\n\n"
                   + (f"After bearish readings, a 10% drop came {bear['dip10']:.0f}% of the time, vs "
                      f"{bull['dip10']:.0f}% after bullish ones, and daily swings were "
                      f"{bear['swings'] / bull['swings']:.1f}× bigger." if bull and bear else ""))
    with bad:
        st.warning("**❌ Not good at: calling up or down.**\n\n"
                   + (f"After bearish readings the market still rose {bear['up']:.0f}% of the time (it often "
                      "bounces after a fall). Nobody can reliably predict next month's direction from public data."
                      if bear else ""))
    rows = ["<table class='ktable'><tr><th>Reading</th><th>Weeks</th><th>Market higher a month later</th>"
            "<th>Average move</th><th>Typical range</th><th>Fell 10%+ during the month</th><th>How bumpy</th></tr>"]
    for name, s in list(test["by_reading"].items()) + [("All weeks", test["all"])]:
        icon = READINGS[name]["icon"] if name in READINGS else "📊"
        rows.append(f"<tr><td>{icon} {name}</td><td>{s['weeks']}</td><td>{s['up']:.0f}%</td><td>{s['avg']:+.1f}%</td>"
                    f"<td>{s['low']:+.1f}% to {s['high']:+.1f}%</td><td>{s['dip10']:.0f}%</td>"
                    f"<td>{s['swings']:.0f}%</td></tr>")
    st.markdown("".join(rows) + "</table>", unsafe_allow_html=True)
    st.caption(f"Checked every week from {test['start']:%b %Y} to {test['end']:%b %Y}, using only the data available "
               "on each day.")


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
    left, right = st.columns([3, 2], gap="large")
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
