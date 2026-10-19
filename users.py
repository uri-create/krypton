# users.py
# Accounts for Krypton: sign up, log in, and private storage for every user.
#
# Security basics:
#   - Passwords are never stored. Only a bcrypt "hash" is kept (a one-way scramble that can be
#     checked but not reversed), so nobody, including the admin, can see anyone's password.
#   - 5 wrong passwords in a row lock that account for 5 minutes (stops password-guessing).
#   - Anyone can sign up, but bots are slowed down: max 3 new accounts per internet address per
#     hour, and max 30 new accounts per hour in total.
#   - Each user's data is reached only through their own UserStore (see storage.py).
#   - The FIRST account ever created becomes the admin. New users have AI features OFF until an
#     admin turns them on (AI costs money on the admin's API key).

import datetime as dt
import re

import bcrypt
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError

from storage import MISCONFIGURED, UserStore, count_recent_signups, engine, now_text, record_signup, users

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 5
SIGNUPS_PER_IP_PER_HOUR = 3
SIGNUPS_PER_HOUR_TOTAL = 30


def _public(row):
    """The safe-to-use parts of a user record (never the password hash)."""
    return {"id": row.id, "username": row.username, "is_admin": bool(row.is_admin),
            "ai_allowed": bool(row.is_admin or row.ai_allowed), "created": row.created,
            "store": UserStore(row.id)}


def validate_new_account(username, password):
    """Returns an error message, or None if the username and password are acceptable."""
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username or ""):
        return "Username must be 3–20 characters: letters, numbers or _ only."
    if not 8 <= len(password or "") <= 128:
        return "Password must be 8–128 characters."
    if password.lower() in ("password", "12345678", "krypton1", "qwertyui", "password1") or password.isdigit():
        return "That password is too easy to guess. Mix letters and numbers."
    if password.lower() == username.lower():
        return "Your password can't be your username."
    return None


def create_account(username, password, ip=None):
    """Create an account. Returns (user, None) on success or (None, error message)."""
    problem = validate_new_account(username, password)
    if problem:
        return None, problem
    if MISCONFIGURED:  # never let anyone sign up (and become admin) on a temporary database
        return None, "Krypton is being set up. Sign-ups are closed for a moment."
    if ip and count_recent_signups(60, ip) >= SIGNUPS_PER_IP_PER_HOUR:
        return None, "Too many new accounts from your connection. Try again in an hour."
    if count_recent_signups(60) >= SIGNUPS_PER_HOUR_TOTAL:
        return None, "Lots of people are signing up right now. Please try again a bit later."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    with engine.begin() as db:
        is_first = db.execute(select(func.count()).select_from(users)).scalar() == 0
        try:
            new_id = db.execute(insert(users).values(
                username=username, username_lower=username.lower(), password_hash=hashed,
                is_admin=is_first, ai_allowed=is_first, created=now_text(), failed_logins=0)).inserted_primary_key[0]
        except IntegrityError:
            return None, "That username is taken."
        row = db.execute(select(users).where(users.c.id == new_id)).first()
    record_signup(ip)
    return _public(row), None


def log_in(username, password):
    """Check a username and password. Returns (user, None) or (None, error message)."""
    with engine.begin() as db:
        row = db.execute(select(users).where(users.c.username_lower == (username or "").lower())).first()
        if row is None:
            bcrypt.checkpw(b"x", bcrypt.hashpw(b"y", bcrypt.gensalt()))  # same delay as a real check
            return None, "Wrong username or password."
        if row.locked_until and dt.datetime.now() < dt.datetime.fromisoformat(row.locked_until):
            return None, f"Too many wrong passwords. Try again after {row.locked_until[11:16]}."
        if not bcrypt.checkpw((password or "").encode("utf-8")[:128], bytes(row.password_hash)):
            failed = row.failed_logins + 1
            locked = (dt.datetime.now() + dt.timedelta(minutes=LOCK_MINUTES)).isoformat(timespec="seconds") \
                if failed >= MAX_FAILED_LOGINS else None
            db.execute(update(users).where(users.c.id == row.id).values(
                failed_logins=0 if locked else failed, locked_until=locked))
            return None, "Wrong username or password."
        db.execute(update(users).where(users.c.id == row.id).values(failed_logins=0, locked_until=None))
    return _public(row), None


def change_password(user_id, old_password, new_password):
    with engine.begin() as db:
        row = db.execute(select(users).where(users.c.id == user_id)).first()
        if not row or not bcrypt.checkpw(old_password.encode("utf-8"), bytes(row.password_hash)):
            return "Current password is wrong."
        problem = validate_new_account(row.username, new_password)
        if problem:
            return problem
        db.execute(update(users).where(users.c.id == user_id).values(
            password_hash=bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())))
    return None


def get_user(user_id):
    with engine.connect() as db:
        row = db.execute(select(users).where(users.c.id == user_id)).first()
    return _public(row) if row else None


def all_users():
    with engine.connect() as db:
        return [_public(row) for row in db.execute(select(users).order_by(users.c.id))]


def any_users():
    with engine.connect() as db:
        return db.execute(select(func.count()).select_from(users)).scalar() > 0


def set_ai_allowed(user_id, allowed):
    with engine.begin() as db:
        db.execute(update(users).where(users.c.id == user_id, users.c.is_admin.is_(False)).values(
            ai_allowed=bool(allowed)))


def delete_account(user_id):
    """Delete a user and ALL their data. Admin accounts can't be deleted this way."""
    user = get_user(user_id)
    if not user or user["is_admin"]:
        return "Admin accounts can't be deleted here."
    user["store"].delete_all()
    with engine.begin() as db:
        db.execute(users.delete().where(users.c.id == user_id))
    return None


# ---------------------------------------------------------------------------
# AI spending limit: AI runs on the admin's API key, so non-admin users get a daily allowance.
# ---------------------------------------------------------------------------
AI_DAILY_LIMIT = 25


def ai_uses_today(user):
    return user["store"].read(f"ai_uses:{dt.date.today():%Y-%m-%d}", 0)


def use_ai(user):
    """Call before every AI request. Returns True (and counts it) if the user may use AI now."""
    if not user.get("ai_allowed"):
        return False
    if user.get("is_admin"):
        return True
    used = ai_uses_today(user)
    if used >= AI_DAILY_LIMIT:
        return False
    user["store"].write(f"ai_uses:{dt.date.today():%Y-%m-%d}", used + 1)
    return True
