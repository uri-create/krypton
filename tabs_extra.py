# tabs_extra.py
# The main tabs beside the live map:
#   💼 My portfolio · 🔔 Alerts · 📊 Track record · 🤖 Ask the analyst · 📰 Daily briefing

import datetime as dt
import html
import os
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from alerts import (alert_text, check_for_alerts, load_log, load_settings, save_settings, send_notifications,
                    severity_colour)
from analyst import api_key_available, ask
from backtest import load_results, run_backtest, summarise
from briefing import list_briefings, read_briefing, write_briefing
from layers import CATEGORIES
from panels import line_chart, pie_chart, subtitle
from portfolio import exposure, holding_prices, load_portfolio, lookup_holding, save_portfolio
from why_moved import explain, load_today, week_move
from severity import SEVERITY
from billing import add_cost, ai_access, locked_message


def ai_ready(user):
    """AI features need the API key AND Krypton Pro (admins always; see billing.py)."""
    return ai_access(user)[0] and api_key_available()


def ai_off(user, key):
    """Explain why an AI feature is unavailable (and offer Krypton Pro)."""
    allowed, reason = ai_access(user)
    if not allowed:
        locked_message(user, reason, key)
    else:
        st.caption("AI is offline right now.")


def badge(severity):
    colour = severity_colour(severity)
    return (f"<span style='color:{colour};border:1px solid {colour};padding:1px 7px;font-size:0.72rem;"
            f"letter-spacing:0.1em'>{severity.upper()}</span>")


# ===========================================================================
# 💼 MY PORTFOLIO
# ===========================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def cached_holding_prices(tickers):
    return holding_prices([{"ticker": t} for t in tickers])


def holding_summary(h, links):
    """A short summary of everything important about one holding, built only from the measured data."""
    t = h["ticker"]
    named = [l for l in links if l["link"] == "Named"]
    measured = [l for l in links if l["link"] == "Measured"]
    by_severity = {}
    for l in links:
        by_severity[l["severity"]] = by_severity.get(l["severity"], 0) + 1
    severity_text = ", ".join(f"{n} {s.lower()}" for s, n in sorted(by_severity.items(),
                                                                     key=lambda x: -SEVERITY[x[0]]["rank"]))
    lines = [f"**Exposure:** {len(links)} live event{'s' if len(links) != 1 else ''} ({severity_text})."]

    if named:
        parts = []
        for l in named:
            move = next((f for f in l["facts"] if "has moved" in f), "")
            parts.append(f"**{l['event']}** (expected {l['direction']})" + (f": {move.split(' has moved ')[1]}"
                                                                             if move else ""))
        lines.append(f"**Named in Krypton research for:** {'; '.join(parts)}")

    if measured:
        drivers = {}
        for l in measured:
            drivers.setdefault(l["driver"], []).append(l)
        main, items = max(drivers.items(), key=lambda kv: len(kv[1]))
        lines.append(f"**Biggest driver:** {t} moves with **{main}** (correlation {items[0]['corr']:+.2f}), "
                     f"which {len(items)} of these events hit."
                     + (f" Also moves with: {', '.join(d for d in drivers if d != main)}." if len(drivers) > 1 else ""))

    worst = max(links, key=lambda l: SEVERITY[l["severity"]]["rank"])
    if worst["link"] == "Measured" and worst["driver_move"] is not None and worst["own_move"] is not None:
        period = f"Since {worst['move_start']:%d %b %Y}" if worst["since"] else "Over the last 30 days"
        lines.append(f"**Most serious:** {worst['event']} ({worst['severity']}). {period}: "
                     f"{worst['driver']} {worst['driver_move']:+.1f}%, {t} {worst['own_move']:+.1f}%.")
    else:
        lines.append(f"**Most serious:** {worst['event']} ({worst['severity']}).")

    ups = sum(1 for l in links if l["direction"] == "▲")
    downs = sum(1 for l in links if l["direction"] == "▼")
    if ups or downs:
        lean = "up ▲" if ups > downs else "down ▼" if downs > ups else "both ways"
        lines.append(f"**Where the links point:** {lean} ({ups} up, {downs} down). Not a prediction: "
                     "Krypton's rules haven't beaten chance historically (see 📊 Track record).")
    return lines


def render_holding(h, links):
    """Summary first, then tidy details under subtitles."""
    t = h["ticker"]
    with st.container(border=True):
        st.markdown("**📌 Summary**")
        st.markdown("\n".join(f"- {line}" for line in holding_summary(h, links)))

    named = [l for l in links if l["link"] == "Named"]
    if named:
        subtitle("🎯 Named in Krypton research")
        for l in named:
            st.markdown(f"{badge(l['severity'])} &nbsp; **{html.escape(l['event'])}** ({l['category']}) · expected "
                        f"{l['direction']}", unsafe_allow_html=True)
            lines = [f"- ✅ {fact}" for fact in l["facts"]] + [f"- 📚 *Research note:* {l['note']}"]
            st.markdown("\n".join(lines))

    groups = {}
    for l in [x for x in links if x["link"] == "Measured"]:
        groups.setdefault(l["driver"], []).append(l)
    if groups:
        subtitle("📈 Measured price links")
        st.caption("Correlation = how closely the daily price moves matched over the last ~12 months "
                   "(after removing normal stock-market swings). 1.00 = always together, 0 = unrelated.")
    for driver, items in groups.items():
        worst = max(items, key=lambda x: SEVERITY[x["severity"]]["rank"])["severity"]
        together = "same direction as" if items[0]["corr"] > 0 else "opposite direction to"
        st.markdown(f"{badge(worst)} &nbsp; **{driver}** · {t} moves in the {together} it "
                    f"(correlation **{items[0]['corr']:+.2f}** over {items[0]['days']} trading days) · "
                    f"{len(items)} event{'s' if len(items) != 1 else ''}", unsafe_allow_html=True)

        # Events with their own start date get their own line; events without one share the
        # same "last 30 days" numbers, so they're merged into ONE line instead of repeating.
        dated = [l for l in items if l["since"]]
        undated = [l for l in items if not l["since"]]
        lines = []
        for l in dated:
            if l["driver_move"] is not None and l["own_move"] is not None:
                lines.append(f"- **{l['event']}** ({l['severity']}): since it began on {l['move_start']:%d %b %Y}, "
                             f"{driver} **{l['driver_move']:+.1f}%**, {t} **{l['own_move']:+.1f}%** ✅")
            else:
                lines.append(f"- **{l['event']}** ({l['severity']})")
        if undated:
            names = ", ".join(f"{l['event']} ({l['severity']})" for l in undated)
            first = undated[0]
            move = (f": over the last 30 days, {driver} **{first['driver_move']:+.1f}%**, {t} "
                    f"**{first['own_move']:+.1f}%** ✅" if first["driver_move"] is not None
                    and first["own_move"] is not None else "")
            lines.append(f"- **Ongoing, no exact start date:** {names}{move}")
        st.markdown("\n".join(lines))

        with st.expander(f"📚 Why each event is linked to {driver} (research notes)"):
            st.markdown("\n".join(f"- **{l['event']}:** {l['note']}" for l in items))


PLAIN_DRIVERS = {
    "Brent oil": "oil prices", "WTI oil": "US oil prices", "Natural gas (US)": "gas prices",
    "European natural gas (TTF)": "European gas prices", "Gold": "the gold price", "Wheat": "wheat prices",
}


def simple_watch_lines(h, links, limit=3):
    """Up to 3 short, plain-English lines: which world events could affect this stock, and how."""
    if not links:
        return ["Nothing big in the world is linked to this stock right now."]
    lines = []
    for l in [x for x in links if x["link"] == "Named"][:limit]:
        lines.append(f"**{l['event']}** ({l['severity'].lower()}): {l['note']}")
    drivers = {}
    for l in [x for x in links if x["link"] == "Measured"]:
        drivers.setdefault(l["driver"], []).append(l)
    for driver, items in sorted(drivers.items(), key=lambda kv: -len(kv[1])):
        if len(lines) >= limit:
            break
        worst = max(items, key=lambda x: SEVERITY[x["severity"]]["rank"])
        plain = PLAIN_DRIVERS.get(driver, driver)
        how = "goes up and down with" if items[0]["corr"] > 0 else "tends to move opposite to"
        extra = f" and {len(items) - 1} more" if len(items) > 1 else ""
        lines.append(f"**{plain.capitalize() if plain[0].islower() else plain}**: {h['ticker']} usually {how} "
                     f"{plain}, which {worst['event']}{extra} could push {'up' if worst['driver_direction'] == '▲' else 'down'}.")
    return lines


def portfolio_tab(state, user):
    st.markdown("### 💼 My portfolio")
    st.caption("Add the stocks, funds or commodities you own (or want to watch). For each one, Krypton shows "
               "which live events affect it and why. Saved only on this computer.")
    store = user["store"]
    holdings = load_portfolio(store)

    with st.form("add_holding", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        ticker = c1.text_input("Ticker symbol", placeholder="e.g. AAPL, XOM, TSM, SPY, KO, BZ=F", max_chars=15)
        added = c2.form_submit_button("➕ Add", type="primary")
    if added and ticker.strip():
        if not re.fullmatch(r"[A-Za-z0-9.=^\-]{1,15}", ticker.strip()):
            st.error("Tickers only use letters, numbers and . = ^ - (e.g. AAPL, BRK-B, BZ=F).")
        elif len(holdings) >= 50:
            st.error("Your portfolio can hold up to 50 items.")
        elif ticker.strip().upper() in [h["ticker"] for h in holdings]:
            st.warning("Already in your portfolio.")
        else:
            with st.spinner("Looking it up..."):
                found = lookup_holding(ticker)
            if found:
                holdings.append(found)
                save_portfolio(store, holdings)
                st.success(f"Added {found['name']} ({found['ticker']}).")
            else:
                st.error(f"Couldn't find a market called '{ticker}'. Check the ticker on Yahoo Finance.")
    if not holdings:
        st.info("Your portfolio is empty. Add a ticker above to see what affects it.")
        return

    with st.spinner("Measuring real price data for your holdings..."):
        held = cached_holding_prices(tuple(h["ticker"] for h in holdings))
        exposed = exposure(holdings, state["events"], state["prices"], held, load_results())

    # ---- Explain the moves (AI + web search, saved for the day)
    market_week = week_move(state["prices"]["S&P 500"]) if "S&P 500" in state["prices"] else 0.0
    missing = [h for h in holdings if load_today(store, h["ticker"]) is None and h["ticker"] in held]
    if missing and ai_ready(user):
        if st.button(f"🧠 Find out why my stocks moved this week ({len(missing)} to check, about "
                     f"{len(missing) * 5}¢)", type="primary"):
            progress = st.progress(0.0, text="Searching the news...")
            for i, h in enumerate(missing, 1):
                if not ai_access(user)[0]:
                    st.warning("You've used this month's AI allowance. It resets on the 1st of next month.")
                    break
                try:
                    result = explain(store, h["ticker"], h["name"], week_move(held[h["ticker"]]) or 0.0,
                                     market_week or 0.0)
                    add_cost(user, result.get("cost"))
                except Exception as error:
                    st.warning(f"{h['ticker']}: couldn't check ({error}).")
                progress.progress(i / len(missing), text=f"Checked {h['ticker']}")
            st.rerun()

    elif missing and not ai_access(user)[0]:
        locked_message(user, ai_access(user)[1], "portfolio")

    # ---- One short card per stock
    for h in holdings:
        links = exposed[h["ticker"]]
        own = held[h["ticker"]].dropna() if h["ticker"] in held else pd.Series(dtype=float)
        week = week_move(own)
        with st.container(border=True):
            # Line 1: name + this week's real move, big and clear
            if week is not None:
                colour = "#ff2a3d" if week < 0 else "#3ddc84"
                arrow = "▼" if week < 0 else "▲"
                move_html = (f"<span style='color:{colour};font-size:1.25rem;font-weight:800'>{arrow} "
                             f"{abs(week):.1f}%</span> <small style='color:#77777f'>this week</small>")
            else:
                move_html = ""
            st.markdown(f"<span style='font-size:1.25rem;font-weight:800;color:#e8e8ee'>{h['ticker']}</span> "
                        f"<span style='color:#77777f'>{html.escape(h['name'])}</span> &nbsp;&nbsp; {move_html}",
                        unsafe_allow_html=True)

            # Why it moved (real news, found by the AI)
            saved = load_today(store, h["ticker"])
            st.markdown("<div class='section'>🧠 Why it moved</div>", unsafe_allow_html=True)
            if saved:
                st.markdown(saved["text"])
            elif not ai_ready(user):
                st.caption("🔒 Krypton Pro shows the real news behind this move.")
            else:
                st.caption("Press the 🧠 button above to look up the real news.")

            # What in the world could affect it (max 3 short lines, plain English)
            st.markdown("<div class='section'>🌍 World events to watch</div>", unsafe_allow_html=True)
            st.markdown("\n".join(f"- {line}" for line in simple_watch_lines(h, links)))

            with st.expander("More details"):
                if h["ticker"] in held:
                    line_chart(held[h["ticker"]], f"{h['ticker']} price, last 12 months", "Price", height=170)
                if links:
                    render_holding(h, links)
                if st.button("🗑️ Remove from portfolio", key=f"remove_{h['ticker']}"):
                    save_portfolio(store, [x for x in holdings if x["ticker"] != h["ticker"]])
                    st.rerun()


# ===========================================================================
# 🔔 ALERTS
# ===========================================================================
CHANGE_WORDS = {"🆕 NEW": ("🆕", "New", "appeared"), "⬆️ ESCALATED": ("⬆️", "Worse", "got more serious"),
                "⬇️ EASED": ("⬇️", "Calmer", "calmed down")}


def alerts_tab(state, user):
    st.markdown("### 🔔 Alerts")
    st.caption("Every 30 minutes Krypton compares the world with the last check and records each serious event "
               "that appears, gets worse, or calms down.")
    store = user["store"]
    settings = load_settings(store)
    log = load_log(store)
    now = dt.datetime.now()

    def when(alert):
        return dt.datetime.strptime(alert["time"], "%Y-%m-%d %H:%M")

    serious_now = sorted([e for e in state["events"] if e["severity"] in ("Critical", "High")],
                         key=lambda e: -SEVERITY[e["severity"]]["rank"])

    # ---------- Summary numbers ----------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Serious events right now", len(serious_now), help="Critical or High severity, live from the map.")
    c2.metric("Alerts, last 24 hours", sum(1 for a in log if now - when(a) <= dt.timedelta(hours=24)))
    c3.metric("Alerts, last 7 days", sum(1 for a in log if now - when(a) <= dt.timedelta(days=7)))
    c4.metric("You're alerted at", f"{settings['min_severity']}+", help="Change this in ⚙️ Alert settings below.")

    # ---------- Right now ----------
    subtitle(f"📌 Right now: {len(serious_now)} serious events")
    rows = ["<table style='width:100%;border-collapse:collapse;font-size:0.82rem'>",
            "<tr style='color:#77777f;text-align:left;border-bottom:1px solid #2a1216'>"
            "<th>Severity</th><th>Event</th><th>Type</th></tr>"]
    for e in serious_now[:15]:
        rows.append(f"<tr style='border-bottom:1px solid #160a0c'><td style='padding:4px 0'>{badge(e['severity'])}</td>"
                    f"<td><b>{html.escape(e['name'])}</b></td><td style='color:#9a9aa4'>{e['category']}</td></tr>")
    rows.append("</table>")
    st.markdown("".join(rows), unsafe_allow_html=True)
    if len(serious_now) > 15:
        st.caption(f"…and {len(serious_now) - 15} more on the map.")

    # ---------- History ----------
    subtitle(f"📜 Alert history ({len(log)})")
    st.caption("🆕 New = a serious event appeared · ⬆️ Worse = its severity went up · ⬇️ Calmer = it dropped "
               "below your alert level.")
    if not log:
        st.info("No alerts yet. Krypton only alerts on REAL changes between two checks. The first check just "
                "records how the world looks, so alerts start from the next change.")
    else:
        days = sorted({when(a).date() for a in log}, reverse=True)
        for day in days:
            items = [a for a in log if when(a).date() == day]
            st.markdown(f"**{day:%A %d %B %Y}** · {len(items)} alert{'s' if len(items) != 1 else ''}")
            table = ["<table style='width:100%;border-collapse:collapse;font-size:0.8rem;margin-bottom:10px'>",
                     "<tr style='color:#77777f;text-align:left;border-bottom:1px solid #2a1216'>"
                     "<th>Time</th><th>Change</th><th>Event</th><th>Severity</th><th>Markets to watch</th></tr>"]
            for a in items:
                icon, word, _ = CHANGE_WORDS.get(a["change"], ("", a["change"], ""))
                severity = (f"{a['was']} → {badge(a['severity'])}" if a["was"] and a["was"] != a["severity"]
                            else badge(a["severity"]))
                mine = (f"<br><small style='color:#ff8a95'>⚠️ affects your {', '.join(a['your_holdings'])}</small>"
                        if a.get("your_holdings") else "")
                table.append(f"<tr style='border-bottom:1px solid #160a0c'><td style='padding:4px 0'>{when(a):%H:%M}</td>"
                             f"<td>{icon} {word}</td><td><b>{html.escape(a['event'])}</b><br><small style='color:#9a9aa4'>"
                             f"{a['category']}</small>{mine}</td><td>{severity}</td>"
                             f"<td style='color:#c9c9d1'>{html.escape(a['markets'] or '—')}</td></tr>")
            table.append("</table>")
            st.markdown("".join(table), unsafe_allow_html=True)

        # Charts only when there's enough data for them to mean something
        if len(days) >= 2:
            per_day = pd.Series({d.strftime("%d %b"): sum(1 for a in log if when(a).date() == d)
                                 for d in sorted(days)})
            line_chart(per_day, "Alerts per day", "Alerts", bars=True, colour="#ff7a00", height=220)
        categories = pd.Series([a["category"] for a in log]).value_counts()
        if len(categories) >= 2:
            pie_chart([f"{c} ({n})" for c, n in categories.items()], list(categories.values),
                      "What the alerts were about", note="Each colour is a type of event. Number = alerts.")

    # ---------- Settings (tucked away) ----------
    with st.expander("⚙️ Alert settings & notifications"):
        with st.form("alert_settings"):
            minimum = st.select_slider("Alert me from this severity up", options=["Moderate", "High", "Critical"],
                                       value=settings["min_severity"] if settings["min_severity"] != "Low" else "Moderate")
            categories = st.multiselect("Types of events", list(CATEGORIES), default=settings["categories"])
            portfolio_only = st.toggle("Only events that affect my portfolio", value=settings["portfolio_only"])
            desktop = st.toggle("Windows desktop notifications", value=settings["desktop"])
            telegram = st.toggle("Telegram messages to my phone", value=settings["telegram"])
            chat_id = st.text_input("Your Telegram chat ID (optional)", value=settings.get("telegram_chat_id", ""),
                                    max_chars=20,
                                    help="See TELEGRAM_SETUP.md, step 2. Lets the Krypton bot message YOU.")
            if st.form_submit_button("💾 Save settings", type="primary"):
                chat_id = chat_id.strip() if re.fullmatch(r"-?[0-9]{1,20}", chat_id.strip()) else ""
                save_settings(store, {**settings, "min_severity": minimum, "categories": categories,
                                       "portfolio_only": portfolio_only, "desktop": desktop, "telegram": telegram,
                                       "telegram_chat_id": chat_id.strip()})
                st.success("Saved.")
        if not os.environ.get("TELEGRAM_BOT_TOKEN"):
            st.caption("📱 Telegram isn't set up yet: see TELEGRAM_SETUP.md in the WorldWatch folder (about 5 minutes).")
        st.markdown("Alerts arrive even when this page is closed, as long as the **alert watcher** is running:")
        st.code("cd C:\\Users\\uri\\Projects\\WorldWatch; python alert_watcher.py", language="bash")
        if st.button("🔍 Check for changes now"):
            new = check_for_alerts(state, store, settings)
            sent = send_notifications(new, settings, desktop_allowed=user["is_admin"])
            st.success(f"{len(new)} new alert(s)" + (f", sent via {', '.join(sent)}" if sent else "") + ".")


# ===========================================================================
# 📊 TRACK RECORD
# ===========================================================================
MIN_EVENTS = 5  # need at least this many SEPARATE past events before judging an event type


def luck_range(base, n):
    """How far from 'just guessing' a score can land by pure luck (95% of the time)."""
    return 1.96 * (base * (1 - base) / n) ** 0.5 if n else 1


def verdict(hit, base, predictions, events):
    if events < MIN_EVENTS:
        return "⚪", "Too few events to judge"
    if hit - base > luck_range(base, predictions):
        return "✅", "Better than guessing"
    if base - hit > luck_range(base, predictions):
        return "❌", "Worse than guessing"
    return "➖", "Same as guessing"


def score_bar(label, score, colour):
    """A simple horizontal bar: '48 out of 100'."""
    return (f"<div style='margin:6px 0 14px 0'><div style='font-size:0.95rem;color:#e8e8ee;margin-bottom:4px'>"
            f"<b>{label}</b>: right <b style='font-size:1.3rem;color:{colour}'>{score}</b> times out of 100</div>"
            f"<div style='background:#1a0c0e;height:22px;width:100%;border:1px solid #2a1216'>"
            f"<div style='background:{colour};height:100%;width:{score}%'></div></div></div>")


def track_record_tab():
    st.markdown("### 📊 Can you trust Krypton's arrows?")
    st.markdown("Krypton shows **▲ up** and **▼ down** arrows for stocks linked to world events. "
                "We checked if those arrows were actually right in the past.")
    results = load_results()
    if not results:
        if st.button("▶️ Run the check (about 1–2 minutes)", type="primary"):
            status = st.empty()
            with st.spinner("Checking against history..."):
                run_backtest(progress=lambda msg: status.info(msg))
            st.rerun()
        return

    table = pd.DataFrame(results["predictions"])
    hit, base = table["hit"].mean(), table["base_rate"].mean()
    events = table[["event", "date"]].drop_duplicates().shape[0]
    right, coin = round(hit * 100), round(base * 100)
    beats = hit - base > luck_range(base, len(table))

    # ---------- The answer, in one line ----------
    if beats:
        st.success(f"## ✅ Yes, a bit.\nKrypton's arrows were right more often than guessing.")
    else:
        st.error("## ❌ Not for predicting prices.\nKrypton's arrows were right about as often as flipping a coin.")

    # ---------- Side by side ----------
    st.markdown(score_bar("Krypton's arrows", right, "#ff2a3d") + score_bar("Just guessing", coin, "#9a9aa4"),
                unsafe_allow_html=True)
    st.caption(f"Tested on {events} real past events (storms, earthquakes, droughts and blocked shipping routes "
               f"since 2018). For each one we checked what the linked stocks really did over the next 30 days.")

    # ---------- What it means ----------
    good, bad = st.columns(2)
    with good:
        st.markdown("#### ✅ Krypton IS good for")
        st.markdown("- Seeing **what's happening** around the world, live\n"
                    "- Knowing **why** it's happening\n"
                    "- Knowing **which stocks are exposed** to it")
    with bad:
        st.markdown("#### ❌ Krypton is NOT good for")
        st.markdown("- **Predicting** if a stock will go up or down\n"
                    "- Deciding what to **buy or sell**\n"
                    "- Beating the market")
    st.caption("Why? By the time news shows up in free data, big investors have usually already traded on it.")

    # ---------- For the curious ----------
    with st.expander("🔎 For the curious: full details"):
        grouped = table.groupby("rule").agg(predictions=("hit", "size"), hit=("hit", "mean"),
                                            base=("base_rate", "mean"))
        grouped["events"] = table[["rule", "event", "date"]].drop_duplicates().groupby("rule").size()
        grouped = grouped[grouped["predictions"] >= 10].sort_values("predictions", ascending=False)
        st.markdown("**Score by type of event**")
        rows = ["<table style='width:100%;border-collapse:collapse;font-size:0.8rem'>",
                "<tr style='color:#77777f;text-align:left;border-bottom:1px solid #2a1216'>"
                "<th>Type of event</th><th>Past events</th><th>Arrows right</th><th>Guessing</th><th>Verdict</th></tr>"]
        for rule, r in grouped.iterrows():
            icon, word = verdict(r["hit"], r["base"], r["predictions"], r["events"])
            rows.append(f"<tr style='border-bottom:1px solid #160a0c'><td style='padding:3px 0'>{rule}</td>"
                        f"<td>{int(r['events'])}</td><td>{r['hit']:.0%}</td><td>{r['base']:.0%}</td>"
                        f"<td>{icon} {word}</td></tr>")
        rows.append("</table>")
        st.markdown("".join(rows), unsafe_allow_html=True)
        st.caption(f"'Too few events' = fewer than {MIN_EVENTS} separate past events, so the score could be luck. "
                   f"'Guessing' = how often each stock moved that way in any random 30 days since 2018.")
        st.markdown("**Every past event tested**")
        st.dataframe(pd.DataFrame(results["events"]).sort_values("date", ascending=False)
                     [["date", "kind", "name", "detail"]], hide_index=True, width="stretch")
        st.caption(f"Last checked: {results['run']}.")
        if st.button("🔄 Run the check again (about 1–2 minutes)"):
            with st.spinner("Checking against history..."):
                run_backtest(progress=lambda msg: None)
            st.rerun()


# ===========================================================================
# 🤖 ASK THE ANALYST
# ===========================================================================
EXAMPLES = ["Why is traffic through the Strait of Hormuz down so much, and what happens next?",
            "Which of my holdings is most at risk this week, and why?",
            "What would a Chinese blockade of Taiwan do to chip stocks?",
            "Explain today's biggest risk to oil prices like I'm new to investing."]


def analyst_tab(state, user):
    st.markdown("### 🤖 Ask the analyst")
    st.caption("Chat with an AI analyst that sees everything on Krypton right now (events, severity, affected "
               "markets, your portfolio, the track record) and searches the web for the latest news.")
    if not ai_ready(user):
        ai_off(user, "analyst")
        st.markdown("**Example questions you'll be able to ask:**\n" + "\n".join(f"- {q}" for q in EXAMPLES))
        return

    history = st.session_state.setdefault("analyst_chat", [])
    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if not history:
        st.markdown("**Try:** " + " · ".join(f"*{q}*" for q in EXAMPLES[:3]))
    question = st.chat_input("Ask about any event, region, market or your portfolio...", max_chars=1000)
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            if not ai_access(user)[0]:
                st.warning("You've used this month's AI allowance. It resets on the 1st of next month.")
                st.stop()
            with st.spinner("Thinking and searching..."):
                results = load_results()
                overall = summarise(results)[0] if results else None
                try:
                    answer, sources, cost = ask(question, history, state, user["store"], overall)
                    add_cost(user, cost)
                except Exception as error:
                    answer, sources = f"Something went wrong: {error}", []
            if sources:
                answer += "\n\n**Sources:**\n" + "\n".join(f"- [{s['title']}]({s['url']})" for s in sources[:8])
            st.markdown(answer)
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]


# ===========================================================================
# 📰 DAILY BRIEFING
# ===========================================================================
def briefing_tab(state, user):
    st.markdown("### 📰 Daily briefing")
    st.caption("A 2-minute summary of what changed, the most serious situations, your portfolio and the week's "
               "biggest market moves. The alert watcher writes one automatically every morning.")
    if st.button("📝 Write today's briefing now", type="primary"):
        write_briefing(state, user["store"])
        st.success("Written.")
    files = list_briefings(user["store"])
    if not files:
        st.info("No briefings yet. Click the button above to write today's.")
        return
    chosen = st.selectbox("Briefing", files, format_func=lambda f: dt.datetime.strptime(f, "%Y-%m-%d")
                          .strftime("%A %d %B %Y"))
    with st.container(border=True):
        st.markdown(read_briefing(user["store"], chosen))
