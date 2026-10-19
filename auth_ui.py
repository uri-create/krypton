# auth_ui.py
# The log-in / sign-up screen and the Account tab.

import secrets

import streamlit as st

from billing import cancel_subscription, is_pro, month_spend, plan_section
from cookies import delete_ticket, read_ticket, save_ticket
from users import (STAY_LOGGED_IN_DAYS, all_users, any_users, change_password, create_account, delete_account,
                   forget_login, forget_logins, get_user, log_in, new_login_ticket, set_ai_allowed, user_from_ticket)


def start_session(user):
    """Log this user in for this visit AND remember this browser for 9 days."""
    ticket = new_login_ticket(user["id"])
    st.session_state["user"] = user
    st.session_state["ticket"] = ticket
    st.session_state["new_ticket"] = ticket  # saved into the browser on the next page draw


def log_out():
    forget_login(st.session_state.get("ticket"))
    st.session_state.clear()
    st.session_state["logged_out"] = True  # also wipes the cookie from the browser (see login_gate)


def login_gate():
    """Return the logged-in user. If nobody is logged in, show the log-in screen and stop the page."""
    if st.session_state.get("user"):
        fresh = get_user(st.session_state["user"]["id"])  # re-read: permissions may have changed
        if fresh:
            st.session_state["user"] = fresh
            if st.session_state.get("new_ticket"):
                save_ticket(st.session_state["new_ticket"], STAY_LOGGED_IN_DAYS)
            return fresh
        st.session_state.pop("user")  # account was deleted

    # Logged in on this browser in the last 9 days? Then no password needed.
    if st.session_state.get("logged_out"):
        delete_ticket()
    else:
        ticket = read_ticket()
        remembered = user_from_ticket(ticket)
        if remembered:
            st.session_state["user"] = remembered
            st.session_state["ticket"] = ticket
            return remembered
        if ticket:
            st.session_state["login_expired"] = True

    from landing import features, hero
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        hero()
    with right:
        with st.container(border=True):
            _auth_forms()
    features()
    st.stop()


def _auth_forms():
    """The sign-up and log-in forms (on the landing page)."""
    if not any_users():
        st.info("No accounts yet. **The first account created becomes the admin** (the owner of this Krypton).")
    if st.session_state.get("login_expired"):
        st.caption(f"Your saved login has ended (it lasts {STAY_LOGGED_IN_DAYS} days). Please log in again.")
    sign_up_tab, log_in_tab = st.tabs(["Create free account", "Log in"])

    with log_in_tab:
        with st.form("log_in"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary", use_container_width=True):
                user, error = log_in(username.strip(), password)
                if user:
                    start_session(user)
                    st.rerun()
                st.error(error)

    with sign_up_tab:
        # A simple "are you human?" sum, new for each visitor, to slow down sign-up bots
        if "human_check" not in st.session_state:
            st.session_state["human_check"] = (secrets.randbelow(9) + 1, secrets.randbelow(9) + 1)
        a, b = st.session_state["human_check"]
        with st.form("sign_up"):
            username = st.text_input("Choose a username", max_chars=20, help="3–20 letters, numbers or _")
            password = st.text_input("Choose a password", type="password", max_chars=128,
                                     help="At least 8 characters")
            again = st.text_input("Type the password again", type="password", max_chars=128)
            answer = st.text_input(f"Are you human? What is {a} + {b}?", max_chars=3)
            agreed = st.checkbox("I've read the privacy notice below")
            if st.form_submit_button("Create free account", type="primary", use_container_width=True):
                if answer.strip() != str(a + b):
                    st.error("That sum isn't right. Try again.")
                elif not agreed:
                    st.error("Please read and tick the privacy notice first.")
                elif password != again:
                    st.error("The two passwords don't match.")
                else:
                    user, error = create_account(username.strip(), password, ip=visitor_ip())
                    if user:
                        st.session_state.pop("human_check", None)
                        start_session(user)
                        st.rerun()
                    st.error(error)
    st.caption("Free. No email needed. Your portfolio and briefings are private to your account.")
    with st.expander("Privacy notice"):
        st.markdown(PRIVACY_NOTICE)


PRIVACY_NOTICE = """
**What Krypton stores about you:** only your username, a scrambled (hashed) version of your password,
and what you add yourself: your portfolio and daily briefings.
No email, no real name, no location, no payment details.

**Who can see it:** only you, when logged in. Other users can never see your data. Your password
is stored as a one-way hash, so nobody, not even the person running Krypton, can read it.
The person running Krypton could technically open the database, as with any website.

**AI features (Krypton Pro):** when you use them, your questions and your list of stocks are sent
to Anthropic's AI to write the answers.

**Payments:** Krypton Pro is paid through Stripe. Krypton never sees or stores your card number.

**Deleting your data:** Account → Delete my account removes your account and everything in it.

**Not financial advice:** Krypton is for learning and research only.
"""


def visitor_ip():
    """The visitor's internet address (used only to limit sign-ups), if Streamlit can see it."""
    try:
        return st.context.ip_address
    except Exception:
        return None


def appearance(user):
    """Colour theme picker (saved to the account, so it follows you to any device)."""
    from theme import DEFAULT, THEMES
    st.markdown("#### Appearance")
    current = st.session_state.get("theme", DEFAULT)
    swatches = "".join(
        f"<span class='swatch' style='background:{t['accent']};box-shadow:0 0 14px {t['accent']}'></span>"
        f"<span class='swatch-name'>{name}</span>" for name, t in THEMES.items())
    st.markdown(f"<div class='swatches'>{swatches}</div>", unsafe_allow_html=True)
    picked = st.segmented_control("Colour theme", list(THEMES), default=current, key="theme_picker")
    if picked and picked != current:
        user["store"].write("theme", picked)
        st.session_state["theme"] = picked
        st.rerun()  # the whole app, so every page changes colour


def account_tab(user):
    st.markdown("### Your account")
    from panels import stat_cards
    stat_cards([
        {"label": "Username", "value": user["username"], "explain": "The name you log in with."},
        {"label": "Role", "value": "Admin" if user["is_admin"] else "User",
         "explain": "Admin = the owner of Krypton. Everyone else is a user."},
        {"label": "Plan", "value": "Admin" if user["is_admin"] else ("Pro" if is_pro(user) else "Free"),
         "explain": "Free = everything except the AI features. Pro = AI features unlocked."},
    ], per_row=3)
    st.caption(f"Account created {user['created']}. Your portfolio and briefings are stored privately "
               "and no other user can see them.")

    plan_section(user)
    appearance(user)
    from data_status import data_status_panel
    data_status_panel()

    st.caption(f"You stay logged in on this device for {STAY_LOGGED_IN_DAYS} days.")
    if st.button("Log out"):
        log_out()
        st.rerun()

    with st.expander("Change password"):
        with st.form("change_password", clear_on_submit=True):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            again = st.text_input("New password again", type="password")
            if st.form_submit_button("Change password"):
                if new != again:
                    st.error("The new passwords don't match.")
                else:
                    error = change_password(user["id"], old, new)
                    if error:
                        st.error(error)
                    else:
                        forget_logins(user["id"])  # log out every other device
                        start_session(user)
                        st.success("Password changed. Other devices have been logged out.")

    if not user["is_admin"]:
        with st.expander("Delete my account"):
            st.warning("This permanently deletes your account, portfolio and briefings. "
                       "A Krypton Pro subscription is cancelled too.")
            sure = st.checkbox("Yes, I understand this can't be undone")
            if st.button("Delete my account", disabled=not sure):
                if not cancel_subscription(user):
                    st.error("Couldn't cancel your subscription right now, so nothing was deleted. Try again soon.")
                    st.stop()
                delete_account(user["id"])
                st.session_state.clear()
                st.session_state["logged_out"] = True
                st.rerun()
        return

    # ---------- Admin only ----------
    st.markdown("### Admin: users")
    st.caption("AI features need a Krypton Pro subscription. "
               "'Free Pro' gives someone Pro without paying (same monthly AI limit).")
    for other in all_users():
        with st.container(border=True):
            left, middle, right = st.columns([2, 1.2, 1])
            badge = "· admin" if other["is_admin"] else ("· Pro" if is_pro(other) else "")
            left.markdown(f"**{other['username']}** {badge}  \n"
                          f"<small>joined {other['created']} · AI this month ${month_spend(other):.2f}</small>",
                          unsafe_allow_html=True)
            if other["is_admin"]:
                middle.markdown("AI: always on")
            else:
                allowed = middle.toggle("Free Pro", value=other["ai_allowed"], key=f"ai_{other['id']}")
                if allowed != other["ai_allowed"]:
                    set_ai_allowed(other["id"], allowed)
                    st.rerun()
                if right.button("Delete", key=f"delete_{other['id']}"):
                    st.session_state[f"confirm_{other['id']}"] = True
                if st.session_state.get(f"confirm_{other['id']}"):
                    st.warning(f"Delete **{other['username']}** and all their data?")
                    yes, no = st.columns(2)
                    if yes.button("Yes, delete", key=f"yes_{other['id']}"):
                        delete_account(other["id"])
                        st.session_state.pop(f"confirm_{other['id']}")
                        st.rerun()
                    if no.button("Cancel", key=f"no_{other['id']}"):
                        st.session_state.pop(f"confirm_{other['id']}")
                        st.rerun()
