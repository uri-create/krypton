# briefing.py
# The DAILY BRIEFING: a 2-minute "what's going on in the world and my portfolio" report.
# Written each morning by the alert watcher (or on demand in the app), saved in each user's
# private storage. If an API key is set up, the AI can polish it into an analyst-style note.

import datetime as dt
import os

from alerts import load_log
from backtest import load_results, summarise
from markets import SECTORS
from portfolio import exposure, load_portfolio
from severity import rank



def today_name():
    return f"briefing:{dt.date.today():%Y-%m-%d}"


def briefing_exists_today(store):
    return store.exists(today_name())


def list_briefings(store):
    """Dates of this user's saved briefings, newest first (e.g. ["2026-10-19", ...])."""
    return sorted((name.split(":", 1)[1] for name in store.names("briefing:")), reverse=True)


def read_briefing(store, date):
    return store.read(f"briefing:{date}", "")


def build_briefing_text(state, store):
    """The briefing as Markdown text."""
    now = dt.datetime.now()
    events = sorted(state["events"], key=lambda e: -rank(e["severity"]))
    critical = [e for e in events if e["severity"] == "Critical"]
    high = [e for e in events if e["severity"] == "High"]
    lines = [f"# 🌐 Krypton daily briefing · {now:%A %d %B %Y}", ""]

    # --- Headline numbers
    lines += ["## At a glance",
              f"- **{len(critical)} critical** and **{len(high)} high-severity** events worldwide.",
              f"- Shipping chokepoints disrupted: **{sum(1 for s in state['statuses'] if s['Status'] == 'Disrupted')}"
              f" of {len(state['statuses'])}**.",
              f"- Aircraft tracked right now: **{state['air']['total_planes']:,}**." if state.get("air") else "",
              ""]
    from compass import summary_line
    weather = summary_line(state.get("compass"))
    if weather:
        lines[lines.index("## At a glance") + 1:lines.index("## At a glance") + 1] = [f"- 🧭 {weather}"]

    # --- What changed in the last 24 hours
    since = now - dt.timedelta(hours=24)
    recent = [a for a in load_log(store) if dt.datetime.strptime(a["time"], "%Y-%m-%d %H:%M") >= since]
    lines.append("## What changed in the last 24 hours")
    lines += [f"- {a['change']} **{a['event']}** ({a['category']}): now {a['severity']}"
              + (f" (was {a['was']})" if a["was"] and a["was"] != a["severity"] else "") for a in recent[:12]] \
        or ["- No new or escalated events (or the alert watcher wasn't running)."]
    lines.append("")

    # --- The most serious situations
    lines.append("## The most serious situations")
    for e in (critical + high)[:10]:
        movers = "; ".join(f"{d} {m}" for m, d, _ in e["impacts"][:3])
        lines.append(f"- **{e['severity']} · {e['name']}** ({e['category']})" + (f": watch {movers}" if movers else ""))
    lines.append("")

    # --- Portfolio
    holdings = load_portfolio(store)
    lines.append("## Your portfolio")
    if holdings:
        for ticker, links in exposure(holdings, state["events"]).items():
            direct = [l for l in links if l["link"] == "Named"]
            if direct:
                lines.append(f"- **{ticker}**: named in the effects of "
                             + "; ".join(f"{l['event']} ({l['severity']}, {l['direction']})" for l in direct[:3]))
            elif links:
                lines.append(f"- **{ticker}**: price measurably moves with markets hit by {len(links)} event(s).")
            else:
                lines.append(f"- **{ticker}**: no exposure to today's serious events.")
    else:
        lines.append("- No portfolio entered yet (add one in the 💼 My portfolio tab).")
    lines.append("")

    # --- Markets
    lines.append("## Biggest market moves this week, by sector")
    for sector, members in SECTORS.items():
        moves = [(m, state["changes"][m]["1 week (%)"]) for m in members
                 if m in state["changes"] and state["changes"][m]["1 week (%)"] is not None]
        if moves:
            best = max(moves, key=lambda x: abs(x[1]))
            lines.append(f"- {sector}: **{best[0]}** {best[1]:+.1f}%")
    lines.append("")

    # --- Honesty reminder from the track record
    results = load_results()
    if results:
        overall, _, _ = summarise(results)
        if overall:
            lines += ["## Track record reminder",
                      f"- Historically, Krypton's researched effects came true **{overall['hit_rate']:.0%}** of the "
                      f"time vs **{overall['base_rate']:.0%}** by chance ({overall['predictions']} predictions). "
                      "Use this to understand what's happening, not to predict prices.", ""]
    lines.append("_For learning and research only. Not financial advice._")
    return "\n".join(line for line in lines if line is not None)


def write_briefing(state, store):
    store.write(today_name(), build_briefing_text(state, store))
    return today_name()
