# Putting Krypton online (free)

When you're done, anyone in the world can open Krypton at a web address like
`https://krypton-yourname.streamlit.app`, create their own account, and get their own private
portfolio and briefings. Nobody can see anyone else's data.

You need 3 free accounts. **Some services require the account holder to be 18+**, so a parent
may need to create them (like the API key).

| Service | What it does | Cost |
|---|---|---|
| **GitHub** (github.com) | Stores Krypton's code | Free |
| **Neon** (neon.tech) | The database: accounts and everyone's private data | Free (0.5 GB) |
| **Streamlit Community Cloud** (share.streamlit.io) | Runs the website, with HTTPS | Free |

---

## 1. Neon: create the database (5 min)
1. Sign up at **neon.tech** → **New project** → name it `krypton` → pick the region closest to you.
2. On the project dashboard click **Connect** and copy the **connection string**
   (starts with `postgresql://`). This is a password: **never share it or put it in the code.**

## 2. Copy your admin account to the online database (1 min)
In PowerShell (paste your connection string between the quotes):
```powershell
cd C:\Users\uri\Projects\WorldWatch
$env:DATABASE_URL = "postgresql://...your connection string..."
python copy_to_cloud.py
```
It should say `Copied 1 account(s)...`. Now your username, password and portfolio work online too.

## 3. GitHub: upload the code (5 min)
1. Sign up at **github.com** → **New repository** → name `krypton` → **Public** → Create.
   (Public = people can read the code, which is fine: it contains **no** passwords, keys or user data.)
2. Ask Claude to push the code, or follow GitHub's "push an existing repository" instructions.
   The `.gitignore` file makes sure accounts, portfolios, backups and secrets are **never** uploaded.

## 4. Streamlit: put the website live (5 min)
1. Go to **share.streamlit.io** → sign in **with GitHub** → **Create app** → **Deploy a public app from GitHub**.
2. Repository: `yourname/krypton`, Branch: `main`, Main file: `app.py`.
3. **Advanced settings** → Python version **3.12** → **Secrets**: paste (with your real values):
   ```toml
   DATABASE_URL = "postgresql://...your Neon connection string..."
   ANTHROPIC_API_KEY = "sk-ant-...your API key..."
   ```
4. **Deploy.** After a few minutes you get your web address. Log in with your usual username and password.

---

## Good to know
- **Your AI money:** AI is OFF for new users. You switch it on per person in 👤 Account, and each
  of them gets max 25 AI requests a day. Set a monthly spending limit in the Anthropic console too.
- **Sleeping:** free Streamlit apps go to sleep after ~12 hours with no visitors. The next visitor
  wakes it up (about 30 seconds). Accounts and data are safe in Neon the whole time.
- **Some live data may be slower online:** free data sources sometimes limit requests from cloud
  servers (aircraft counts, prices). Krypton keeps working; that layer may show "no data" for a while.
- **Updating Krypton later:** change the code, push to GitHub, and the website updates itself.
- **Not financial advice:** Krypton says this on every page. Keep it that way.
