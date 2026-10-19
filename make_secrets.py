# make_secrets.py
# Builds the 2 lines for Streamlit's "Secrets" box and puts them on your clipboard, ready to paste.
#   - Takes your Neon connection string FROM YOUR CLIPBOARD (click "Copy snippet" on Neon first)
#   - Uses the Anthropic API key already saved on this PC (by set_api_key.sh)
#   - Checks the lines against Streamlit's exact format rules (TOML) before copying
# It NEVER prints the secrets, only READY / NOT READY.
#
# Run it with:   python make_secrets.py

import os
import subprocess
import tomllib
import winreg


def saved_api_key():
    """The API key saved in your Windows user settings (or None)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as settings:
            return winreg.QueryValueEx(settings, "ANTHROPIC_API_KEY")[0].strip()
    except OSError:
        return None


def neon_from_clipboard():
    """The Neon connection string on the clipboard (or None). Copes with extra spaces, quotes or a 'psql' in front."""
    clip = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                          capture_output=True, text=True).stdout or ""
    clip = "".join(clip.split())
    start = clip.find("postgres")
    if start == -1:
        return None
    return clip[start:].strip("'\"")


neon = neon_from_clipboard()
key = saved_api_key()

if not neon:
    print("NOT READY: your clipboard doesn't have the Neon string. On Neon click 'Copy snippet', then run this again.")
elif not key or not key.startswith("sk-ant-"):
    print("NOT READY: no Anthropic API key is saved on this PC (run set_api_key.sh first).")
elif "'" in neon or "'" in key:
    print("NOT READY: unexpected character in a secret. Copy the Neon string again.")
else:
    # Single quotes = TOML "literal strings": nothing inside them is treated specially
    block = f"DATABASE_URL = '{neon}'\nANTHROPIC_API_KEY = '{key}'\n"
    parsed = tomllib.loads(block)  # the same format check Streamlit does
    if parsed.get("DATABASE_URL") == neon and parsed.get("ANTHROPIC_API_KEY") == key:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $env:KRYPTON_BLOCK"],
                       env={**os.environ, "KRYPTON_BLOCK": block}, check=True)
        print("READY: 2 lines are on your clipboard. Paste them into Streamlit -> Settings -> Secrets.")
    else:
        print("NOT READY: the format check failed. Copy the Neon string again and re-run.")
