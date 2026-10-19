# storage.py
# Where Krypton keeps accounts and every user's private data.
#
#   - On your PC: a local database file, data/krypton.db (SQLite).
#   - Online: a real database server (e.g. a free Neon Postgres). Set DATABASE_URL in the
#     environment or in Streamlit's secrets and the SAME code uses it instead.
#
# Two tables:
#   users      - username, bcrypt password hash, admin/AI flags (see users.py)
#   user_data  - each user's private items (portfolio, alert settings, alert history,
#                briefings, "why it moved" answers), stored as JSON, keyed by (user_id, name).
# Every read and write goes through a UserStore that is locked to ONE user id, so one user's
# code path can never touch another user's rows.

import datetime as dt
import json
import os
import re

from sqlalchemy import (Boolean, Column, Integer, LargeBinary, MetaData, String, Table, Text, create_engine, delete,
                        func, insert, select, text, update)
from sqlalchemy.exc import IntegrityError

KRYPTON_DIR = os.path.dirname(__file__)


def get_secret(name):
    """A private setting (database address, API key, bot token). Looked up in the environment first,
    then in Streamlit's secrets (how the online version gets them). Never written in the code."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:  # no secrets file (normal on your PC)
        return None


# Streamlit Community Cloud runs apps from /mount/src/. There, the local-file fallback would be an
# EMPTY, TEMPORARY database (wiped on every restart, and the first sign-up would become admin).
ONLINE = os.path.abspath(__file__).replace("\\", "/").startswith("/mount/src/")
MISCONFIGURED = ONLINE and not get_secret("DATABASE_URL")  # online but the real database isn't set up


def _database_url():
    """DATABASE_URL from the environment or Streamlit secrets, else the local file."""
    url = get_secret("DATABASE_URL")
    if MISCONFIGURED:
        return "sqlite://"  # throw-away in-memory database; the app refuses to run anyway (see app.py)
    if url:
        # Neon adds "channel_binding=require", which the database driver here rejects; the connection
        # is still encrypted by "sslmode=require", so we just drop it.
        url = re.sub(r"[?&]channel_binding=[^&]*", "", url.strip())
        if "?" not in url and "&" in url:
            url = url.replace("&", "?", 1)
        # Neon/Supabase give "postgres://..." or "postgresql://..."; tell SQLAlchemy to use psycopg 3
        return url.replace("postgres://", "postgresql+psycopg://", 1).replace(
            "postgresql://", "postgresql+psycopg://", 1)
    folder = os.environ.get("KRYPTON_USERS_DIR") or os.path.join(KRYPTON_DIR, "data")  # test copies use their own
    os.makedirs(folder, exist_ok=True)
    return "sqlite:///" + os.path.join(folder, "krypton.db").replace("\\", "/")


engine = create_engine(_database_url(), pool_pre_ping=True)
metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(20), unique=True, nullable=False),
    Column("username_lower", String(20), unique=True, nullable=False),  # makes "Bob" and "bob" the same
    Column("password_hash", LargeBinary, nullable=False),
    Column("is_admin", Boolean, nullable=False, default=False),
    Column("ai_allowed", Boolean, nullable=False, default=False),
    Column("created", String(20), nullable=False),
    Column("failed_logins", Integer, nullable=False, default=0),
    Column("locked_until", String(25)),
)

user_data = Table(
    "user_data", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("name", String(80), primary_key=True),
    Column("content", Text, nullable=False),
    Column("updated", String(20), nullable=False),
)

signups = Table(  # used to slow down bots creating lots of accounts
    "signups", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("time", String(25), nullable=False),
    Column("ip", String(64)),
)

subscriptions = Table(  # Krypton Pro: who pays (the payment itself happens on Stripe, see billing.py)
    "subscriptions", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("customer_id", String(64)),       # Stripe's id for this payer
    Column("subscription_id", String(64)),   # Stripe's id for this subscription
    Column("status", String(20)),            # "active" = paid up
    Column("checked", String(25)),           # when we last asked Stripe
)

metadata.create_all(engine)


def now_text():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


class UserStore:
    """Private storage for ONE user. Everything it reads or writes is filtered by that user's id."""

    def __init__(self, user_id):
        self.user_id = int(user_id)

    def read(self, name, default=None):
        with engine.connect() as db:
            row = db.execute(select(user_data.c.content).where(
                user_data.c.user_id == self.user_id, user_data.c.name == name)).first()
        return json.loads(row[0]) if row else default

    def write(self, name, value):
        content = json.dumps(value, ensure_ascii=False, default=str)
        with engine.begin() as db:
            changed = db.execute(update(user_data).where(
                user_data.c.user_id == self.user_id, user_data.c.name == name).values(
                content=content, updated=now_text())).rowcount
            if not changed:
                try:
                    db.execute(insert(user_data).values(user_id=self.user_id, name=name, content=content,
                                                        updated=now_text()))
                except IntegrityError:  # written by someone else a split second earlier
                    db.execute(update(user_data).where(user_data.c.user_id == self.user_id,
                                                       user_data.c.name == name).values(content=content))

    def exists(self, name):
        return self.read(name) is not None

    def names(self, prefix=""):
        with engine.connect() as db:
            rows = db.execute(select(user_data.c.name).where(
                user_data.c.user_id == self.user_id, user_data.c.name.like(prefix.replace("%", "") + "%")))
            return [row[0] for row in rows]

    def delete_all(self):
        with engine.begin() as db:
            db.execute(delete(user_data).where(user_data.c.user_id == self.user_id))


def count_recent_signups(minutes, ip=None):
    since = (dt.datetime.now() - dt.timedelta(minutes=minutes)).isoformat(timespec="seconds")
    query = select(func.count()).select_from(signups).where(signups.c.time >= since)
    if ip:
        query = query.where(signups.c.ip == ip)
    with engine.connect() as db:
        return db.execute(query).scalar()


def record_signup(ip=None):
    with engine.begin() as db:
        db.execute(insert(signups).values(time=dt.datetime.now().isoformat(timespec="seconds"), ip=ip))
