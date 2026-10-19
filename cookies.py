# cookies.py
# Saves and reads the "stay logged in" cookie (see users.py: 9-day login tickets).
# Writing happens in the browser through a tiny invisible component (cookie_component/index.html);
# reading uses Streamlit's st.context.cookies.

import os

import streamlit as st
import streamlit.components.v1 as components

COOKIE_NAME = "krypton_login"

_cookie = components.declare_component(
    "krypton_cookie", path=os.path.join(os.path.dirname(__file__), "cookie_component"))


def read_ticket():
    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None


def save_ticket(ticket, days):
    _cookie(name=COOKIE_NAME, value=ticket, max_age=days * 24 * 3600, key="krypton_cookie", default=None)


def delete_ticket():
    _cookie(name=COOKIE_NAME, value="", max_age=0, key="krypton_cookie", default=None)
