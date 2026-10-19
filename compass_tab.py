# compass_tab.py
# 🧭 The Market Compass page, kept simple:
#   1. Today's reading (Bullish / Neutral / Bearish) with a gauge
#   2. What usually happens next (3 numbers from 18 years of history)
#   3. Why: the six signals, one line each
#   4. One chart: the S&P 500, coloured by the reading at the time
#   5. Leading sectors + serious world events
#   6. Can you trust it? (with the full numbers tucked away)
# The calculations live in compass.py; this file only draws the page.

import html

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from compass import LEAN, READINGS, SIGNALS, reading
from panels import GRID, chart_key, how_to_read, stat_cards, subtitle
from severity import SEVERITY

FONT = dict(family="Inter, sans-serif", color="#8a8a96")


def _hero(compass, name):
    info = READINGS[name]
    score = compass["today"]["Score"]
    left = (score + 100) / 2
    st.markdown(
        f"<div class='hero' style='--accent:{info['colour']}'>"
        f"<div class='hero-kicker'>🧭 THE US STOCK MARKET (S&amp;P 500) RIGHT NOW</div>"
        f"<div class='hero-main'><span class='hero-icon'>{info['icon']}</span>"
        f"<span class='hero-reading' style='color:{info['colour']}'>{name}</span></div>"
        f"<div class='hero-meaning'>{info['meaning']}</div>"
        f"<div class='gauge'><div class='gauge-mark' style='left:{left:.1f}%;background:{info['colour']};"
        f"box-shadow:0 0 14px {info['colour']}'></div></div>"
        "<div class='gauge-labels'><span>🐻 Bearish</span><span>⚖️ Neutral</span><span>🐂 Bullish</span></div>"
        f"<div class='hero-foot'>Score {score:+.0f} out of ±100 · market closes up to {compass['date']:%d %b %Y}</div>"
        "</div>", unsafe_allow_html=True)
    with st.expander("What do Bullish, Neutral and Bearish mean?"):
        for n, r in READINGS.items():
            st.markdown(f"{r['icon']} **{n}** (score {r['range']}): {r['meaning']}")
        st.caption("The score is the average of six market signals (shown below). It describes the market right now; "
                   "it's not a promise about the future and not advice to buy or sell.")


def _next_month(compass, name):
    test = compass["test"]
    odds, normal = test["by_reading"][name], test["all"]
    subtitle("🔮 What usually happens next")
    how_to_read(f"What the S&P 500 actually did over the following month, in the {odds['weeks']} past weeks that "
                f"were also {name} (since {test['start'].year}).")
    stat_cards([
        {"label": "Higher a month later", "value": f"{odds['up']:.0f}%",
         "explain": f"of the time. Normally: {normal['up']:.0f}%."},
        {"label": "Usual move in a month", "value": f"{odds['low']:+.0f}% to {odds['high']:+.0f}%",
         "explain": "8 times out of 10 it landed in this range."},
        {"label": "Chance of a big drop", "value": f"{odds['dip10']:.0f}%",
         "tone": "good" if odds["dip10"] <= normal["dip10"] else "bad",
         "delta": "lower than usual" if odds["dip10"] < normal["dip10"] else "higher than usual",
         "explain": f"of falling 10% or more at some point. Normally: {normal['dip10']:.0f}%."},
    ], per_row=3)


def _signals(compass, name):
    subtitle(f"🔍 Why it's {name.lower()}: the six signals")
    rows = []
    for signal, info in SIGNALS.items():
        value = compass["today"][signal]
        if value > 0.15:
            pill, tone, text = "🐂 Bullish", "good", info["up"]
        elif value < -0.15:
            pill, tone, text = "🐻 Bearish", "bad", info["down"]
        else:
            pill, tone, text = "⚖️ Neutral", "", "Near its normal level, not pushing either way."
        rows.append(f"<div class='signal-row'><span class='signal-name'>{info['icon']} {signal}</span>"
                    f"<span class='stat-delta {tone}'>{pill}</span><span class='signal-text'>{text}</span></div>")
    st.markdown(f"<div class='signal-list'>{''.join(rows)}</div>", unsafe_allow_html=True)
    with st.expander("What does each signal measure?"):
        for signal, info in SIGNALS.items():
            st.markdown(f"{info['icon']} **{signal}:** {info['what']}")


def _chart(compass):
    subtitle("📜 The last two years")
    how_to_read("The S&P 500's price, coloured by what the Compass said at the time: "
                "<b style='color:#3ddc84'>green</b> = Bullish, <b style='color:#ffb000'>amber</b> = Neutral, "
                "<b style='color:#ff2a3d'>red</b> = Bearish. The red stretches line up with the rough patches.")
    scores = compass["scores"]["Score"].iloc[-504:]
    sp = compass["sp500"].reindex(scores.index)
    figure = go.Figure()
    for label, colour, mask in (("Bullish", "#3ddc84", scores >= LEAN), ("Bearish", "#ff2a3d", scores <= -LEAN),
                                ("Neutral", "#ffb000", (scores > -LEAN) & (scores < LEAN))):
        # keep one day either side of each stretch so the coloured pieces join up smoothly
        keep = mask | mask.shift(1, fill_value=False) | mask.shift(-1, fill_value=False)
        figure.add_trace(go.Scatter(x=sp.index, y=np.where(keep, sp.values, np.nan), mode="lines", name=label,
                                    line=dict(color=colour, width=2.6, shape="spline", smoothing=0.6),
                                    hovertemplate=f"%{{x|%d %b %Y}}: %{{y:,.0f}} ({label})<extra></extra>"))
    figure.update_layout(template="plotly_dark", height=360, showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=10), font=FONT,
                         hovermode="x unified")
    figure.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
    figure.update_yaxes(gridcolor="rgba(255,255,255,0.04)", title_text="S&P 500")
    st.plotly_chart(figure, width="stretch", key=chart_key("compass_history"))


def _sectors(compass):
    subtitle("🧩 Leading sectors this month")
    how_to_read("Green bars rose this month, red fell. If safe sectors (Utilities, Everyday goods, Healthcare) lead, "
                "investors are being careful.")
    sectors = sorted(compass["sectors"].items(), key=lambda kv: kv[1]["month"])
    lo = min(0, min(v["month"] for _, v in sectors))
    hi = max(0, max(v["month"] for _, v in sectors))
    figure = go.Figure(go.Bar(
        x=[v["month"] for _, v in sectors], y=[k for k, _ in sectors], orientation="h",
        marker=dict(color=["#3ddc84" if v["month"] >= 0 else "#ff2a3d" for _, v in sectors], cornerradius=6),
        text=[f"{v['month']:+.1f}%" for _, v in sectors], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+.1f}% this month<extra></extra>"))
    figure.update_layout(template="plotly_dark", height=330, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=50, t=10, b=10),
                         font=dict(family="Inter, sans-serif", color="#a3a3ae"),
                         xaxis=dict(gridcolor=GRID, showticklabels=False, zeroline=True, zerolinecolor="#55555f",
                                    range=[lo * 1.35 - 1.5, hi * 1.2 + 1.5]))
    st.plotly_chart(figure, width="stretch", key=chart_key("compass_sectors"))


def _world(state):
    subtitle("🌍 Serious world events")
    how_to_read("From Krypton's live map. They're not part of the score, but they can move the stocks they touch.")
    serious = sorted([e for e in state["events"] if e["severity"] in ("Critical", "High")],
                     key=lambda e: -SEVERITY[e["severity"]]["rank"])
    if not serious:
        st.markdown("Nothing serious on the map right now.")
        return
    rows = "".join(f"<div class='risk-row'><span class='risk-dot' style='background:{e['colour']}'></span>"
                   f"<b>{html.escape(e['name'])}</b><span class='muted'>{e['severity']}</span></div>"
                   for e in serious[:6])
    st.markdown(f"<div class='risk-list'>{rows}</div>", unsafe_allow_html=True)


def _trust(compass):
    subtitle("🎯 Can you trust it?")
    test = compass["test"]
    bull, bear = test["by_reading"].get("Bullish"), test["by_reading"].get("Bearish")
    good, bad = st.columns(2)
    if bull and bear:
        good.success(f"**✅ Good at spotting rough months.** After a Bearish reading, a big drop came "
                     f"{bear['dip10']:.0f}% of the time, vs {bull['dip10']:.0f}% after a Bullish one.")
        bad.warning(f"**❌ Not good at calling up or down.** Even after Bearish readings the market rose "
                    f"{bear['up']:.0f}% of the time, because it often bounces back.")
    with st.expander("See the full numbers"):
        rows = ["<table class='ktable'><tr><th>Reading</th><th>Weeks</th><th>Higher a month later</th>"
                "<th>Average move</th><th>Usual range</th><th>Fell 10%+</th></tr>"]
        for name, s in list(test["by_reading"].items()) + [("All weeks", test["all"])]:
            icon = READINGS[name]["icon"] if name in READINGS else "📊"
            rows.append(f"<tr><td>{icon} {name}</td><td>{s['weeks']}</td><td>{s['up']:.0f}%</td>"
                        f"<td>{s['avg']:+.1f}%</td><td>{s['low']:+.1f}% to {s['high']:+.1f}%</td>"
                        f"<td>{s['dip10']:.0f}%</td></tr>")
        st.markdown("".join(rows) + "</table>", unsafe_allow_html=True)
        st.caption(f"Every week from {test['start']:%b %Y} to {test['end']:%b %Y}, using only the data available "
                   f"on each day. Options traders currently expect a move of about ±{compass['month_move']:.1f}% "
                   f"over the next month (from the VIX, {compass['vix']:.0f} today).")
    with st.expander("📊 Krypton's event arrows: track record"):
        from tabs_extra import track_record_tab
        track_record_tab()


def compass_tab(state, user):
    compass = state.get("compass")
    if not compass:
        st.warning("The Market Compass couldn't load its market data right now. Please try again in a few minutes.")
        return
    name = reading(compass["today"]["Score"])
    _hero(compass, name)
    _next_month(compass, name)
    _signals(compass, name)
    _chart(compass)
    left, right = st.columns([3, 2], gap="large")
    with left:
        _sectors(compass)
    with right:
        _world(state)
    _trust(compass)
    st.caption("For learning only. Not financial advice: Krypton never tells you to buy or sell anything.")
