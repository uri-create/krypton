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
    if user.get("is_admin") and not previewing_as_free():
        return True, ""
    free_pass = user.get("ai_allowed") and not user.get("is_admin")  # a free Pro pass the admin gave someone
    if not (is_pro(user) or free_pass):
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
#   Locked AI features show a 🔒 button. Pressing it opens the Krypton Pro page (pro_page),
#   which app.py shows INSTEAD of the normal tabs until the user presses "Back".
# ---------------------------------------------------------------------------
PRO_FEATURES = ["🧠 **Why it moved**: the real news behind each of your stocks",
                "🤖 **Ask the analyst**: chat with an AI that sees everything on Krypton",
                "🔬 **Deep research**: a full sourced report on any event"]
FREE_FEATURES = "live map, event panels, portfolio prices, alerts, track record and the daily briefing"


def open_pro_page():
    st.session_state["pro_page"] = True


def close_pro_page():
    st.session_state["pro_page"] = False


def previewing_as_free():
    """The admin can switch on 'preview as a free user' to see exactly what non-paying users see."""
    return bool(st.session_state.get("preview_free"))


def locked_message(user, reason, key, label="Unlock with Krypton Pro"):
    """Shown instead of an AI feature the user can't use: a 🔒 button that opens the Krypton Pro page."""
    if reason == "used_up":
        st.warning("You've used this month's AI allowance. It resets on the 1st of next month.")
        return
    if st.button(f"🔒 {label}", key=f"lock_{key}", help=f"Needs Krypton Pro ({PRICE_TEXT})"):
        open_pro_page()
        st.rerun()  # the whole app, not just this tab, so the Krypton Pro page appears
    st.caption(f"🔒 Krypton Pro feature ({PRICE_TEXT}). Press the button to see the plan.")


def _checkout_link(user):
    """A Stripe payment page for this user, made once per visit (Stripe pages stay valid for 24 hours)."""
    if "checkout_url" not in st.session_state:
        st.session_state["checkout_url"] = checkout_url(user)
    return st.session_state["checkout_url"]


def check_payment_button(user, key):
    if stripe_ready() and st.button("I've paid, unlock Pro", key=f"paid_{key}"):
        try:
            if refresh(user):
                st.success("⭐ Krypton Pro is unlocked!")
                close_pro_page()
                st.rerun()
            else:
                st.warning("No payment found yet. If you just paid, wait a minute and try again.")
        except Exception:
            st.error("Couldn't reach the payment system. Try again in a minute.")


def pro_page(user):
    """The Krypton Pro subscription page."""
    st.button("← Back to Krypton", on_click=close_pro_page)
    st.markdown("## ⭐ Krypton Pro")
    st.markdown(f"<span style='font-size:2.2rem;font-weight:800;color:#ff2a3d'>{PRICE_TEXT.split('/')[0]}</span>"
                f" <span style='color:#77777f'>/ month · cancel any time</span>", unsafe_allow_html=True)
    st.markdown("**You get:**\n" + "\n".join(f"- {line}" for line in PRO_FEATURES))
    st.caption(f"Always free: {FREE_FEATURES}. Not financial advice.")

    if ai_access(user)[0] and not user.get("is_admin"):
        st.success("✅ You already have Krypton Pro.")
        return
    if not stripe_ready():
        st.info("🚧 Subscriptions open very soon. Check back shortly!")
        return
    try:
        st.link_button(f"⭐ Subscribe for {PRICE_TEXT}", _checkout_link(user), type="primary")
        st.caption("You'll pay on Stripe's secure page; Krypton never sees your card. "
                   "After paying you're sent back here and Pro unlocks.")
    except Exception:
        st.error("Couldn't open the payment page right now. Please try again in a minute.")
    check_payment_button(user, "pro_page")


def handle_return(user):
    """After Stripe sends the user back with ?paid=1, check their subscription straight away."""
    if st.query_params.get("paid") == "1":
        st.query_params.clear()
        st.session_state.pop("checkout_url", None)
        try:
            if refresh(user):
                close_pro_page()
                st.success("⭐ Welcome to Krypton Pro! AI features are unlocked.")
            else:
                st.info("Payment received? It can take a minute to show up. "
                        "Press **I've paid, unlock Pro** on the ⭐ Krypton Pro page.")
        except Exception:
            st.info("Couldn't check your payment right now. Try again in a minute.")


def plan_section(user):
    """The 'Your plan' part of the Account tab."""
    st.markdown("#### ⭐ Your plan")
    if user.get("is_admin"):
        st.caption(f"Owner: AI is always unlocked for you. AI spending this month: ${month_spend(user):.2f}.")
        now = st.toggle("👀 Preview as a free user (see what non-paying users see)", key="preview_free")
        if now != st.session_state.get("_preview_applied", False):
            st.session_state["_preview_applied"] = now
            st.rerun()  # the whole app, so every tab locks/unlocks (this tab runs on its own otherwise)
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
    if st.button(f"⭐ See Krypton Pro ({PRICE_TEXT})", type="primary", key="plan_pro"):
        open_pro_page()
        st.rerun()
