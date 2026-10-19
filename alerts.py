# alerts.py
# Spots what CHANGED since the last check and sends alerts:
#   🆕 NEW        an event appeared at or above your chosen severity
#   ⬆️ ESCALATED  an event's severity went up
#   ⬇️ EASED      an event dropped back below your chosen severity
#
# Alerts are saved in each user's private storage (shown in the app) and can also be sent as:
#   - Windows desktop notifications (built in)
#   - Telegram messages to your phone (optional, see TELEGRAM_SETUP.md)

import datetime as dt

import requests

from engine import event_key
from portfolio import exposure, load_portfolio
from severity import SEVERITY, rank
from storage import get_secret

DEFAULT_SETTINGS = {
    "min_severity": "High",
    "categories": ["Shipping", "Air cargo", "Weather", "Military", "Quakes & volcanoes"],
    "portfolio_only": False,
    "desktop": True,
    "telegram": True,
}


def load_settings(store):
    return {**DEFAULT_SETTINGS, **store.read("alert_settings", {})}


def save_settings(store, settings):
    store.write("alert_settings", settings)


def load_log(store):
    return store.read("alerts", [])


def check_for_alerts(state, store, settings=None):
    """Compare current events with the last check. Returns the list of NEW alerts (and logs them)."""
    settings = settings or load_settings(store)
    minimum = rank(settings["min_severity"])
    holdings = load_portfolio(store)
    exposed = exposure(holdings, state["events"]) if holdings else {}

    last_seen = store.read("alert_last_seen", None)
    current = {event_key(e): e["severity"] for e in state["events"]}
    store.write("alert_last_seen", current)
    if last_seen is None:
        return []  # first ever check: just remember the current state, don't flood you with alerts

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    alerts = []
    for e in state["events"]:
        if e["category"] not in settings["categories"]:
            continue
        key, severity = event_key(e), e["severity"]
        before = last_seen.get(key)
        my_holdings = [t for t, links in exposed.items() if any(l["id"] == e["id"] for l in links)]
        if settings["portfolio_only"] and not my_holdings:
            continue
        if rank(severity) >= minimum and before is None:
            change = "🆕 NEW"
        elif rank(severity) >= minimum and before and rank(severity) > rank(before):
            change = "⬆️ ESCALATED"
        elif before and rank(before) >= minimum > rank(severity):
            change = "⬇️ EASED"
        else:
            continue
        top_markets = ", ".join(f"{d} {m}" for m, d, _ in e["impacts"][:4])
        alerts.append({
            "time": now, "change": change, "event": e["name"], "category": e["category"],
            "severity": severity, "was": before,
            "markets": top_markets, "your_holdings": my_holdings, "id": e["id"],  # tuples save as lists
        })

    if alerts:
        store.write("alerts", (alerts + load_log(store))[:300])  # newest first, keep the last 300
    return alerts


def alert_text(a):
    text = f"{a['change']} · {a['severity'].upper()} · {a['event']} ({a['category']})"
    if a["was"] and a["was"] != a["severity"]:
        text += f" [was {a['was']}]"
    if a["markets"]:
        text += f"\nMarkets: {a['markets']}"
    if a["your_holdings"]:
        text += f"\n⚠️ Affects your: {', '.join(a['your_holdings'])}"
    return text


def send_notifications(alerts, settings, desktop_allowed=True):
    """Desktop notification (one summary) + Telegram (if set up). Returns what was sent.
    desktop_allowed: only the admin (whose PC this is) gets Windows pop-ups."""
    sent = []
    if not alerts:
        return sent
    if settings.get("desktop") and desktop_allowed:
        try:
            from plyer import notification
            worst = max(alerts, key=lambda a: rank(a["severity"]))
            more = f" (+{len(alerts) - 1} more)" if len(alerts) > 1 else ""
            notification.notify(title=f"Krypton: {worst['change']} {worst['severity']}{more}",
                                message=f"{worst['event']}"[:250], app_name="Krypton", timeout=10)
            sent.append("desktop")
        except Exception:
            pass
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat = settings.get("telegram_chat_id") or (get_secret("TELEGRAM_CHAT_ID") if desktop_allowed else None)
    if settings.get("telegram") and token and chat:
        message = "🌐 Krypton alerts\n\n" + "\n\n".join(alert_text(a) for a in alerts[:10])
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": message[:4000]}, timeout=30)
            sent.append("telegram")
        except requests.RequestException:
            pass
    return sent


def severity_colour(severity):
    return SEVERITY[severity]["colour"]
