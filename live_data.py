# live_data.py
# Keeps Krypton's live feeds ready in memory so pages open instantly.
#
# Before: each feed was kept for 15-60 minutes, then the NEXT visitor had to wait ~20 seconds
# while everything downloaded again.
# Now: visitors always get the latest copy straight away. When a copy gets old, a helper
# downloads a fresh one in the background and swaps it in when it's ready.
# Only the very first visitor after the server starts has to wait (and the feeds then download
# side by side instead of one after another, so even that is faster).

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from data_sources import (CHOKEPOINTS, get_air_traffic, get_chokepoint_traffic, get_disasters, get_many_headlines,
                          get_prices, get_weather)
from layers import AIR_HUBS, CONFLICT_ZONES

MINUTE, HOUR = 60, 3600


def _air():
    try:
        return get_air_traffic(AIR_HUBS, CONFLICT_ZONES)
    except Exception:
        return None


def _weather():
    try:
        return get_weather(CHOKEPOINTS, marine=True), get_weather(AIR_HUBS)
    except Exception:
        return {}, {}


def _conflict_news():
    return get_many_headlines({name: zone["news"] for name, zone in CONFLICT_ZONES.items()})


def _compass():
    try:
        from compass import build
        return build()
    except Exception:  # the rest of Krypton still works without it
        return None


# name: (download function, how old a copy may get before a fresh one is fetched)
FEEDS = {
    "traffic": (get_chokepoint_traffic, 6 * HOUR),
    "disasters": (get_disasters, HOUR),
    "prices": (get_prices, HOUR),
    "air": (_air, 15 * MINUTE),
    "weather": (_weather, 30 * MINUTE),
    "conflict_news": (_conflict_news, HOUR),
    "compass": (_compass, HOUR),
}

_copies = {}        # name -> (time downloaded, data)
_refreshing = set()  # feeds being downloaded in the background right now
_lock = threading.Lock()
_first_load = threading.Lock()


def _download(name):
    data = FEEDS[name][0]()
    with _lock:
        _copies[name] = (time.time(), data)
        _refreshing.discard(name)
    return data


def _refresh_in_background(name):
    def job():
        try:
            _download(name)
        except Exception:  # keep the old copy; try again next time someone visits
            with _lock:
                _refreshing.discard(name)
    threading.Thread(target=job, daemon=True).start()


def get_all():
    """Every feed, instantly if a copy exists. Raises if a feed has never downloaded successfully."""
    with _first_load:  # if nothing is ready yet, download the missing feeds side by side
        missing = [name for name in FEEDS if name not in _copies]
        if missing:
            with ThreadPoolExecutor(max_workers=len(missing)) as pool:
                for future in [pool.submit(_download, name) for name in missing]:
                    future.result()
    now = time.time()
    with _lock:
        for name, (_, max_age) in FEEDS.items():
            if now - _copies[name][0] > max_age and name not in _refreshing:
                _refreshing.add(name)
                _refresh_in_background(name)
        return {name: data for name, (_, data) in _copies.items()}


def version():
    """Changes whenever any feed gets a fresh copy (used to know when to rebuild the map's events)."""
    with _lock:
        return tuple(round(_copies[name][0]) for name in FEEDS if name in _copies)


_built = {"version": None, "state": None}


def get_state():
    """Everything the app needs (feeds + events), rebuilt only when a feed has a fresh copy."""
    from engine import build_state
    raw = get_all()
    current = version()
    if _built["version"] != current:
        sea_weather, hub_weather = raw["weather"]
        _built["state"] = build_state({"traffic": raw["traffic"], "disasters": raw["disasters"],
                                       "prices": raw["prices"], "air": raw["air"], "sea_weather": sea_weather,
                                       "hub_weather": hub_weather, "conflict_news": raw["conflict_news"]})
        _built["state"]["compass"] = raw["compass"]
        _built["version"] = current
    return _built["state"]
