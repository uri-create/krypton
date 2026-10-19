# globe.py
# The 3D globe for Krypton (see globe_component/index.html for the drawing code).

import os

import streamlit.components.v1 as components

_globe = components.declare_component(
    "krypton_globe", path=os.path.join(os.path.dirname(__file__), "globe_component"))


def krypton_globe(events, sea_routes, air_routes, height=640, key=None):
    """Draw the globe. Returns the last clicked icon as {"id": ..., "t": time}, or None."""
    return _globe(events=events, sea=sea_routes, air=air_routes, height=height, key=key, default=None)


def to_event_id(value):
    """Ids travel through the browser as lists; turn them back into the tuples Krypton uses."""
    if isinstance(value, list):
        return tuple(to_event_id(v) for v in value)
    return value
