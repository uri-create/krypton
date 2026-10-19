# copy_to_cloud.py
# Copies the accounts and private data from your PC's database (data/krypton.db) into the online
# database, so your admin account, password and portfolio work on the website too.
# Run it ONCE, before anyone signs up online:
#
#   PowerShell:  $env:DATABASE_URL = "<the Neon connection string>"; python copy_to_cloud.py
#
# It refuses to run if the online database already has accounts (so it can't overwrite anything).
# Your password stays a one-way hash the whole time; it is never readable.

import os
import sys

from sqlalchemy import create_engine, func, insert, select

import storage  # creates the tables in whichever database DATABASE_URL points to

if not os.environ.get("DATABASE_URL"):
    sys.exit("Set DATABASE_URL to the online database first (see the comment at the top of this file).")

local = create_engine("sqlite:///" + os.path.join(os.path.dirname(__file__), "data", "krypton.db").replace("\\", "/"))
cloud = storage.engine

with cloud.connect() as db:
    if db.execute(select(func.count()).select_from(storage.users)).scalar():
        sys.exit("The online database already has accounts. Nothing was copied.")

with local.connect() as source, cloud.begin() as target:
    accounts = source.execute(select(storage.users)).mappings().all()
    items = source.execute(select(storage.user_data)).mappings().all()
    for row in accounts:
        target.execute(insert(storage.users).values(**row))
    for row in items:
        target.execute(insert(storage.user_data).values(**row))
    if cloud.dialect.name == "postgresql":  # make new sign-ups get the next free id number
        target.execute(storage.text("SELECT setval(pg_get_serial_sequence('users', 'id'), "
                                    "(SELECT MAX(id) FROM users))"))

print(f"Copied {len(accounts)} account(s) and {len(items)} private item(s) to the online database.")
