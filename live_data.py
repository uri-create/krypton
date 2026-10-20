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
from concurrent.futures import TimeoutError as FutureTimeout

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
        with ThreadPoolExecutor(max_workers=2) as pool:  # sea and airport weather side by side
            sea = pool.submit(get_weather, CHOKEPOINTS, True)
            hubs = pool.submit(get_weather, AIR_HUBS)
            return sea.result(), hubs.result()
    except Exception:
        return {}, {}


def _conflict_news():
    try:
        return get_many_headlines({name: zone["news"] for name, zone in CONFLICT_ZONES.items()})
    except Exception:  # news is helpful but not essential: the map still works without it
        return {}


def _disasters():
    try:
        return get_disasters()
    except Exception:  # if the disaster service is down, show the rest of the map anyway
        return []


def _universe():
    try:
        from universe import download
        return download()
    except Exception:  # the rest of Krypton still works without it
        return None


def _compass():
    try:
        from compass import build
        return build()
    except Exception:  # the rest of Krypton still works without it
        return None


def _live_prices():
    """Live prices for the largest companies (needs the company list first, so it runs after it)."""
    with _lock:
        companies = _copies.get("universe", (0, None))[1]
    if companies is None:
        return None
    from universe import live_prices
    return live_prices(companies)


# name: (download function, how old a copy may get before a fresh one is fetched)
FEEDS = {
    "traffic": (get_chokepoint_traffic, 6 * HOUR),
    "disasters": (_disasters, HOUR),
    "prices": (get_prices, HOUR),
    "air": (_air, 15 * MINUTE),
    "weather": (_weather, 30 * MINUTE),
    "conflict_news": (_conflict_news, HOUR),
    "compass": (_compass, HOUR),
    "universe": (_universe, 6 * HOUR),          # the company list itself (names, sectors, sizes)
    "live_prices": (_live_prices, 15 * MINUTE),  # live prices for the 1,000 largest companies
}
OPTIONAL = {"live_prices"}  # not waited for on the very first load: added the moment it's ready
FIRST_LOAD_LIMIT = 90       # seconds the very first visitor waits before slow sources are skipped for now
STAND_INS = {"disasters": [], "air": None, "weather": ({}, {}), "conflict_news": {}, "compass": None,
             "universe": None}  # what to show if a non-essential source is too slow on the first load


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
        missing = [name for name in FEEDS if name not in _copies and name not in OPTIONAL]
        if missing:
            pool = ThreadPoolExecutor(max_workers=len(missing))
            futures = {name: pool.submit(_download, name) for name in missing}
            pool.shutdown(wait=False)
            deadline = time.time() + FIRST_LOAD_LIMIT
            for name, future in futures.items():
                try:
                    future.result(timeout=max(1, deadline - time.time()))
                except FutureTimeout:
                    # A free source that stops answering must not freeze the site: use an empty stand-in
                    # for now (marked as very old, so it's retried on the next visit; the slow download
                    # also replaces it by itself if it finishes later). Essential feeds can't be faked.
                    if name not in STAND_INS:
                        raise
                    with _lock:
                        _copies.setdefault(name, (0, STAND_INS[name]))
    now = time.time()
    with _lock:
        for name, (_, max_age) in FEEDS.items():
            stale = name not in _copies or now - _copies[name][0] > max_age
            if stale and name not in _refreshing:
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
        from universe import apply_live
        companies = raw["universe"]
        if companies is not None:
            companies = apply_live(companies, raw.get("live_prices"))
        _built["state"]["universe"] = companies
        _built["version"] = current
    return _built["state"]


def status():
    """For the 'Live data status' panel: {feed: (seconds since last download, refreshing now?)}."""
    now = time.time()
    with _lock:
        return {name: (now - _copies[name][0] if name in _copies else None, name in _refreshing) for name in FEEDS}


def ready_state():
    """The latest built state if one exists already (never waits, never downloads), else None."""
    return _built["state"]


_warming = threading.Lock()


def warm_up():
    """Start downloading everything in the background (used on the landing page, so the app is
    ready by the time a visitor has signed up or logged in)."""
    if _built["state"] is not None or not _warming.acquire(blocking=False):
        return

    def job():
        try:
            get_state()
        except Exception:
            pass
        finally:
            _warming.release()
    threading.Thread(target=job, daemon=True).start()
