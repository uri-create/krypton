# cookies.py
# Saves and reads the "stay logged in" cookie (see users.py: 9-day login tickets).
# Both happen in the browser through a tiny invisible component (cookie_component/index.html),
# because Streamlit's online hosting doesn't pass browser cookies through to the app.

import os

import streamlit.components.v1 as components

COOKIE_NAME = "krypton_login"

_cookie = components.declare_component(
    "krypton_cookie", path=os.path.join(os.path.dirname(__file__), "cookie_component"))


def read_ticket():
    """The saved ticket, "" if this browser has none, or None if the browser hasn't answered yet."""
    return _cookie(mode="read", name=COOKIE_NAME, key="krypton_cookie_read", default=None)


def save_ticket(ticket, days):
    _cookie(mode="save", name=COOKIE_NAME, value=ticket, max_age=days * 24 * 3600, key="krypton_cookie",
            default=None)


def delete_ticket():
    _cookie(mode="save", name=COOKIE_NAME, value="", max_age=0, key="krypton_cookie", default=None)
