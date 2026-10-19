# billing.py
# Krypton Pro: a $14.99/month subscription that unlocks everything that costs YOU money (the AI).
#
#   Free for everyone:  live map, event panels, portfolio prices, alerts, track record, briefing.
#   Krypton Pro only:   🧠 "Why it moved", 🤖 Ask the analyst, 🔬 Deep research (they use your API key).
#
# How paying works (Stripe does all the money and card handling; Krypton never sees card numbers):
#   1. The user presses "Subscribe" -> Krypton asks Stripe for a checkout page labelled with their user id.
#   2. They pay on Stripe's page and come back to Krypton.
#   3. Krypton asks Stripe "does user 5 have an active subscription?" and unlocks Pro if yes.
#      It asks again once a day, so a cancelled subscription locks again by itself.
#
# Spending cap: every AI request's REAL cost is measured from what the API reports (words in/out +
# web searches) and added up per user per month. Subscribers get MONTHLY_AI_BUDGET of AI per month,
# so one subscriber can never cost you more than they pay.
#
# Secrets needed online (Streamlit -> Settings -> Secrets):
#   STRIPE_SECRET_KEY  - from Stripe -> Developers -> API keys (starts with sk_test_ or sk_live_)
#   STRIPE_PRICE_ID    - the $14.99/month price you create in Stripe (starts with price_)
#   APP_URL            - optional, defaults to the live site below

import datetime as dt

import streamlit as st
from sqlalchemy import insert, select, update

from storage import engine, get_secret, subscriptions

PRICE_TEXT = "$14.99/month"
MONTHLY_AI_BUDGET = 5.00  # US dollars of AI per subscriber per month (you keep the rest)
RECHECK_HOURS = 24
DEFAULT_APP_URL = "https://0krypton0.streamlit.app"

# Claude Opus 5.5 list prices (US dollars per 1 million tokens) and web search (per search)
PRICE_INPUT, PRICE_OUTPUT = 4.00, 20.00
PRICE_CACHE_WRITE, PRICE_CACHE_READ = 5.00, 0.40
PRICE_SEARCH = 0.01


# ---------------------------------------------------------------------------
# Measuring what each AI request really cost
# ---------------------------------------------------------------------------
def cost_of(response):
    """Real cost in US dollars of one API response, from the usage numbers the API sends back."""
    usage = response.usage
    tokens = (usage.input_tokens * PRICE_INPUT + usage.output_tokens * PRICE_OUTPUT
              + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * PRICE_CACHE_WRITE
              + (getattr(usage, "cache_read_input_tokens", 0) or 0) * PRICE_CACHE_READ) / 1_000_000
    tools = getattr(usage, "server_tool_use", None)
    searches = (getattr(tools, "web_search_requests", 0) or 0) if tools else 0
    return tokens + searches * PRICE_SEARCH


def _month_key():
    return f"ai_cost:{dt.date.today():%Y-%m}"


def month_spend(user):
    return user["store"].read(_month_key(), 0.0)


def add_cost(user, dollars):
    user["store"].write(_month_key(), round(month_spend(user) + (dollars or 0.0), 4))


# ---------------------------------------------------------------------------
# Who may use AI
# ---------------------------------------------------------------------------
def ai_access(user):
    """(True, "") if this user may run an AI request now, else (False, reason)."""
    if user.get("is_admin"):
        return True, ""
    if not (is_pro(user) or user.get("ai_allowed")):  # ai_allowed = a free pass the admin gave them
        return False, "locked"
    if month_spend(user) >= MONTHLY_AI_BUDGET:
        return False, "used_up"
    return True, ""


# ---------------------------------------------------------------------------
# Subscriptions (Stripe)
# ---------------------------------------------------------------------------
def stripe_ready():
    return bool(get_secret("STRIPE_SECRET_KEY") and get_secret("STRIPE_PRICE_ID"))


def _stripe():
    import stripe
    stripe.api_key = get_secret("STRIPE_SECRET_KEY")
    return stripe


def _row(user_id):
    with engine.connect() as db:
        return db.execute(select(subscriptions).where(subscriptions.c.user_id == user_id)).first()


def _save(user_id, **values):
    values["checked"] = dt.datetime.now().isoformat(timespec="seconds")
    with engine.begin() as db:
        if db.execute(update(subscriptions).where(subscriptions.c.user_id == user_id).values(**values)).rowcount == 0:
            db.execute(insert(subscriptions).values(user_id=user_id, **values))


def refresh(user):
    """Ask Stripe whether this user has an active subscription and remember the answer."""
    if not stripe_ready():
        return False
    found = _stripe().Subscription.search(query=f"metadata['krypton_user_id']:'{int(user['id'])}'", limit=10)
    best = None
    for sub in found.data:
        if sub.status in ("active", "trialing"):
            best = sub
            break
        best = best or sub
    if best is None:
        _save(user["id"], status="none")
        return False
    _save(user["id"], status=best.status, subscription_id=best.id, customer_id=best.customer)
    return best.status in ("active", "trialing")


def is_pro(user):
    """True if the user has a paid-up Krypton Pro subscription."""
    row = _row(user["id"])
    if row is None:
        return False
    stale = not row.checked or dt.datetime.now() - dt.datetime.fromisoformat(row.checked) > \
        dt.timedelta(hours=RECHECK_HOURS)
    if stale and stripe_ready() and row.status in ("active", "trialing", "past_due"):
        try:
            return refresh(user)
        except Exception:  # Stripe unreachable: keep the last known answer for now
            pass
    return row.status in ("active", "trialing")


def checkout_url(user):
    """A Stripe payment page for this user (only valid for this user's id)."""
    app = get_secret("APP_URL") or DEFAULT_APP_URL
    session = _stripe().checkout.Session.create(
        mode="subscription",
        line_items=[{"price": get_secret("STRIPE_PRICE_ID"), "quantity": 1}],
        client_reference_id=str(user["id"]),
        metadata={"krypton_user_id": str(user["id"])},
        subscription_data={"metadata": {"krypton_user_id": str(user["id"])}},
        success_url=app + "?paid=1",
        cancel_url=app,
    )
    return session.url


def cancel_subscription(user):
    """Stop charging this user (used when they delete their account). True if nothing is left running."""
    row = _row(user["id"])
    if not row or not row.subscription_id or row.status not in ("active", "trialing", "past_due"):
        return True
    try:
        _stripe().Subscription.cancel(row.subscription_id)
        _save(user["id"], status="canceled")
        return True
    except Exception:
        return False


def manage_url(user):
    """Stripe's page where a subscriber can update their card or cancel."""
    row = _row(user["id"])
    if not row or not row.customer_id:
        return None
    app = get_secret("APP_URL") or DEFAULT_APP_URL
    return _stripe().billing_portal.Session.create(customer=row.customer_id, return_url=app).url


# ---------------------------------------------------------------------------
# What the user sees
# ---------------------------------------------------------------------------
PRO_FEATURES = ("🧠 **Why it moved**: the real news behind each of your stocks\n"
                "- 🤖 **Ask the analyst**: chat with an AI that sees everything on Krypton\n"
                "- 🔬 **Deep research**: a full sourced report on any event")


def subscribe_button(user, key):
    """Subscribe button (or a 'coming soon' note before Stripe is set up)."""
    if not stripe_ready():
        st.caption("Subscriptions open soon.")
        return
    if st.button(f"⭐ Get Krypton Pro, {PRICE_TEXT}", key=f"sub_{key}", type="primary"):
        try:
            st.link_button("Continue to secure payment (Stripe) →", checkout_url(user))
            st.caption("After paying, come back, log in, and press **I've paid, unlock Pro** on the 👤 Account tab.")
        except Exception:
            st.error("Couldn't open the payment page right now. Please try again in a minute.")


def locked_message(user, reason, key):
    """Shown instead of an AI feature the user can't use."""
    if reason == "used_up":
        st.warning("You've used this month's AI allowance. It resets on the 1st of next month.")
        return
    st.info(f"🔒 **This is part of Krypton Pro ({PRICE_TEXT}).**\n\n- {PRO_FEATURES}\n\n"
            "Everything else on Krypton stays free.")
    subscribe_button(user, key)


def handle_return(user):
    """After Stripe sends the user back with ?paid=1, check their subscription straight away."""
    if st.query_params.get("paid") == "1":
        st.query_params.clear()
        try:
            if refresh(user):
                st.success("⭐ Welcome to Krypton Pro! AI features are unlocked.")
            else:
                st.info("Payment received? It can take a minute to show up. "
                        "Press **I've paid, unlock Pro** on the 👤 Account tab.")
        except Exception:
            st.info("Couldn't check your payment right now. Try the 👤 Account tab in a minute.")


def plan_section(user):
    """The 'Your plan' part of the Account tab."""
    st.markdown("#### ⭐ Your plan")
    if user.get("is_admin"):
        st.caption(f"Admin: AI unlimited. Spent this month: ${month_spend(user):.2f} of your API money.")
        return
    pro = is_pro(user)
    if pro or user.get("ai_allowed"):
        st.markdown("**Krypton Pro** ✅" if pro else "**Free Pro pass** (given by the admin) ✅")
        used = min(month_spend(user) / MONTHLY_AI_BUDGET, 1.0)
        st.progress(used, text=f"AI used this month: {used:.0%}")
        if pro:
            url = None
            try:
                url = manage_url(user)
            except Exception:
                pass
            if url:
                st.link_button("Manage or cancel subscription", url)
        return
    st.markdown("**Free plan**")
    locked_message(user, "locked", "account")
    if stripe_ready() and st.button("I've paid, unlock Pro"):
        try:
            if refresh(user):
                st.success("⭐ Krypton Pro is unlocked!")
                st.rerun()
            else:
                st.warning("No payment found yet. If you just paid, wait a minute and try again.")
        except Exception:
            st.error("Couldn't reach the payment system. Try again in a minute.")
