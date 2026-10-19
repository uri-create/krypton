<p align="center"><img src="assets/icon.png" width="88" alt="Krypton"></p>

<h1 align="center">Krypton</h1>
<p align="center"><b>Market intelligence, in plain words.</b><br>
A live stock market guide that connects what's happening in the world to what's happening in the markets.</p>

<p align="center"><a href="https://0krypton0.streamlit.app">Open Krypton</a></p>

---

## What it does

| | |
|---|---|
| **Market Compass** | Is the US stock market bullish, neutral or bearish right now? Six well-known signals (trend, momentum, breadth, fear, credit, growth) combined into one reading, with the real odds for the next month from 18 years of history. |
| **Universal search** | Any stock: market cap, float and total shares, what the company does in plain language, and its price history. |
| **World map** | A live 3D globe of shipping chokepoints, air cargo hubs, conflicts, storms and disasters, and the stocks each one affects. |
| **Markets** | Every US-listed company (about 5,300) by GICS sector, largest first, coloured by today's move, with live prices for the 1,000+ largest. |
| **Clusters** | Which markets move together, measured from a year of daily prices, so you can see when several holdings are really one bet. |
| **Portfolio, analyst and briefing** | Your holdings and the world events that touch them, an AI analyst (Krypton Pro), and a daily briefing written from the live data. |

## Honest by design

Krypton tests itself and shows the results, good and bad. For example, the Market Compass is good at
warning about rough months (big drops were about 7 times more common after bearish readings) but it
**cannot** reliably call whether the market will go up or down, and the app says so. Nothing in Krypton
is financial advice, and it never tells anyone to buy or sell.

## How it's built

- **Python** and **Streamlit**, with Plotly charts and a custom 3D globe (globe.gl)
- **Live data** from Nasdaq, Yahoo Finance, IMF PortWatch, GDACS, Open-Meteo, OpenSky, Google News and
  Wikipedia, refreshed in the background on a schedule (see the "Live data status" panel in the app)
- **Accounts** with hashed passwords, a 9-day remember-me login, and per-user private storage
  (PostgreSQL on Neon online, SQLite locally)
- **Krypton Pro** subscription via Stripe for the features that cost money to run (AI)
- **Claude** (Anthropic) for the AI analyst, deep research and plain-English company profiles

## Run it yourself

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

It works locally without any accounts or keys (AI features need an Anthropic API key). To put it online,
see [DEPLOY.md](DEPLOY.md). Data licences for each source are summarised in [DATA_LICENCES.md](DATA_LICENCES.md).

---

<p align="center"><sub>For learning and research only. Not financial advice.</sub></p>
