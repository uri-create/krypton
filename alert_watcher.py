# alert_watcher.py
# Runs in the background and checks the world every 30 minutes, for EVERY user.
# Each user gets alerts based on their own settings and portfolio, saved in their own storage.
# Only the admin (whose computer this is) gets Windows desktop pop-ups; anyone can use Telegram.
# It also writes each user's daily briefing each morning.
#
# Start it with:   python alert_watcher.py          (keeps running, checks every 30 minutes)
#                  python alert_watcher.py --once   (one check, then stop; used by the online version,
#                                                    where GitHub Actions runs it every 30 minutes)
# Stop it with:    Ctrl + C

import datetime as dt
import sys
import time

from alerts import check_for_alerts, load_settings, send_notifications
from briefing import briefing_exists_today, write_briefing
from engine import build_state, fetch_all
from users import all_users

CHECK_EVERY_MINUTES = 30
BRIEFING_HOUR = 7  # write the daily briefing after 7:00 each morning


def check_once():
    state = build_state(fetch_all())  # the world is the same for everyone: fetch it once
    stamp = dt.datetime.now().strftime("%H:%M")
    users = all_users()
    for user in users:
        settings = load_settings(user["store"])
        alerts = check_for_alerts(state, user["store"], settings)
        sent = send_notifications(alerts, settings, desktop_allowed=user["is_admin"])
        if alerts:
            print(f"[{stamp}] {user['username']}: {len(alerts)} new alerts"
                  + (f" · sent via {', '.join(sent)}" if sent else ""))
        if dt.datetime.now().hour >= BRIEFING_HOUR and not briefing_exists_today(user["store"]):
            write_briefing(state, user["store"])
    print(f"[{stamp}] checked {len(state['events'])} events for {len(users)} user(s)")


if __name__ == "__main__":
    if "--once" in sys.argv:
        check_once()
        sys.exit(0)
    print(f"Krypton alert watcher started. Checking every {CHECK_EVERY_MINUTES} minutes. Ctrl+C to stop.")
    while True:
        try:
            check_once()
        except Exception as error:  # a feed being down shouldn't stop the watcher
            print(f"Check failed ({error}); will try again next time.")
        time.sleep(CHECK_EVERY_MINUTES * 60)
