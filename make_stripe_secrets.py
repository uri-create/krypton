# make_stripe_secrets.py
# Builds the 2 Stripe lines for Streamlit's "Secrets" box and puts them on your clipboard.
#   1. In Stripe, copy your SECRET key (Developers -> API keys). Don't paste it anywhere.
#   2. Run:   python make_stripe_secrets.py price_XXXXXXXX     (your Krypton Pro price ID)
#   3. It reads the key from your clipboard, checks with Stripe that the price is right,
#      and puts 2 ready lines on your clipboard. Paste them at the END of Streamlit's Secrets box.
# It NEVER prints the key, only facts like "test mode: yes".

import os
import re
import subprocess
import sys
import tomllib

import stripe

if len(sys.argv) != 2 or not re.fullmatch(r"price_[A-Za-z0-9]+", sys.argv[1]):
    sys.exit("Run it like this:  python make_stripe_secrets.py price_XXXXXXXX   (your price ID from Stripe)")
price_id = sys.argv[1]

clip = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                      capture_output=True, text=True).stdout or ""
key = "".join(clip.split())
if not re.fullmatch(r"(sk|rk)_(test|live)_[A-Za-z0-9]+", key):
    sys.exit("NOT READY: your clipboard doesn't have a Stripe secret key (it starts with sk_test_ or sk_live_). "
             "Copy it in Stripe (Developers -> API keys -> Secret key) and run this again.")

stripe.api_key = key
try:
    price = stripe.Price.retrieve(price_id)
except stripe.AuthenticationError:
    sys.exit("NOT READY: Stripe says that key isn't valid. Copy the secret key again.")
except stripe.InvalidRequestError:
    sys.exit("NOT READY: Stripe can't find that price ID with this key. Check the price ID, and that the key "
             "and the price are both in the same mode (both test, or both live).")
except Exception:
    sys.exit("NOT READY: couldn't reach Stripe. Check your internet and try again.")

amount = (price.unit_amount or 0) / 100
interval = price.recurring.interval if price.recurring else None
print(f"Test mode (fake money): {'yes' if key.split('_')[1] == 'test' else 'NO, this is LIVE (real money)'}")
print(f"Price: {amount:.2f} {price.currency.upper()} every {interval or 'once (NOT a subscription!)'}")
if interval != "month" or not price.active:
    sys.exit("NOT READY: the price must be an ACTIVE, RECURRING, MONTHLY price. Fix it in Stripe and run again.")

block = f"STRIPE_SECRET_KEY = '{key}'\nSTRIPE_PRICE_ID = '{price_id}'\n"
parsed = tomllib.loads(block)  # the same format check Streamlit does
assert parsed["STRIPE_SECRET_KEY"] == key and parsed["STRIPE_PRICE_ID"] == price_id
subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $env:KRYPTON_BLOCK"],
               env={**os.environ, "KRYPTON_BLOCK": block}, check=True)
print("READY: 2 lines are on your clipboard. Paste them at the END of Streamlit -> Settings -> Secrets "
      "(keep the lines already there), Save, then Reboot.")
