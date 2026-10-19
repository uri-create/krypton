# Can Krypton use its data in a paid app?

Checked on 19 October 2026 by reading each provider's own terms pages (links below).
This is research, not legal advice. Terms change, so check again before you launch or sell.

## The big thing to know first

**Once you charge for Krypton Pro, the whole app counts as commercial, including the free parts.**
It doesn't help that only the AI features are paid. Open-Meteo, for example, says any app with
subscriptions or ads is commercial. A company buying Krypton will also check this, because it
inherits any licence problems.

## The table

| Source | OK for paid use? | What to do | Cost |
|---|---|---|---|
| **IMF PortWatch** (ship counts) | **With conditions.** Ask first. | The IMF allows reuse with credit, but for any commercial reuse it says to email copyright@imf.org for permission. Send a short email explaining Krypton and keep the reply. Show "Source: International Monetary Fund, PortWatch" with a link. | Free (permission email) |
| **GDACS** (disasters) | **Yes, with credit** (probably) | It's run by the European Commission, whose content is CC BY 4.0, which allows commercial use with credit. Show "Disaster alerts: GDACS (European Commission / UN)" with a link. Don't use the GDACS logo. GDACS also says its alerts aren't for making decisions, so keep a note saying so. | Free |
| **OpenSky Network** (live planes) | **No** | This is the strictest one. Using the REST API in **any live product** needs a written licence, even for non-profits, and so does any for-profit business. Either ask OpenSky for a licence (no public price) or switch to **adsb.lol**, whose data is open (ODbL), which allows commercial use with credit. Check adsb.lol's API rules first, since it may start requiring a key. | OpenSky: ask for a quote. adsb.lol: free |
| **Open-Meteo** forecast + marine | **No** on the free API | The free API is for non-commercial use only. Buy **API Standard**, about **$29/month** (1M calls/month), and credit "Weather data by Open-Meteo.com" (CC BY 4.0). | ~$29/month |
| **Open-Meteo** archive (climate history) | **No** on the free API | Historical/climate data needs the **API Professional** plan, about **$99/month**, which includes everything in Standard. One Professional plan covers all of Open-Meteo. Or drop or cache the archive feature and stay on Standard. | ~$99/month (replaces the $29 plan) |
| **Google News RSS** | **No** | The feed itself says it's only for "personal, non-commercial use" in a feed reader, and any other use is prohibited. Switch to **GDELT**, which is free for commercial use if you cite GDELT and link to its site. | GDELT: free |
| **Yahoo Finance / yfinance** | **No** | yfinance says it's "for personal use only", and Yahoo's API terms ban earning money from it without written permission. Switch to a paid data provider that allows showing data to your users. Most low-cost plans (e.g. Alpha Vantage from **$49.99/month**, Twelve Data from **$79/month**) are only for personal or internal use. You must ask them for a "display" or "commercial" licence, which usually costs more. If not, remove the market panel from the public app. | Ask vendors; expect $50+/month |
| **Esri World_Imagery + World_Boundaries_and_Places** tiles | **With conditions.** Get an account. | Krypton currently loads these tiles with no account, which Esri's terms don't cover. Make a free **ArcGIS Location Platform** account and use its access key. That plan allows unlimited commercial apps and includes **2 million tiles/month free**, then $0.15 per 1,000. You must show "Powered by Esri" plus the data credits (Esri, Vantor, Earthstar Geographics, GIS User Community). | Free up to 2M tiles/month |
| **globe.gl + three-globe** code | **Yes** | Both use the MIT licence, so commercial use is fine. Keep the licence notice and add a credit on an "About" page. | Free |
| **three-globe textures** (earth-blue-marble, earth-topology, night-sky) | **Probably yes, but unclear** | They come with an MIT package, and Blue Marble is NASA imagery, which is public domain. But where `night-sky.png` comes from isn't documented. To be safe, download NASA Blue Marble and NASA star-map images yourself and host them in the app. | Free |
| **jsDelivr** (CDN) | **Yes** | jsDelivr says it's free for anyone, including big production sites. It only delivers the files, so the licences above still apply. | Free |
| **Font Awesome Free** icons | **Yes, with credit** | Icons are CC BY 4.0, fonts SIL OFL 1.1, code MIT. Commercial use is fine. The credit inside the CSS file counts, so just don't remove it. Don't use Pro-only icons. | Free |
| *(also in app.py)* **Google Fonts**: Inter, Space Grotesk | **Yes** | Both use the open SIL OFL font licence. | Free |

## Rough monthly bill to go legal

- **Must-pay:** Open-Meteo Professional ~$99 (or Standard ~$29 if you drop the climate archive).
- **Free swaps:** Google News → GDELT, OpenSky → adsb.lol, Esri → free Location Platform account.
- **Market data:** the big unknown. Budget $50–$100+/month and ask for a written display licence,
  or remove the market panel.
- **Free with an email:** IMF PortWatch.

So roughly **$30–$200/month**, depending on the weather archive and market data.
At $14.99 each, that's about 2–14 subscribers just to cover data.

## Before selling Krypton to a company

Keep a folder with: this file, the IMF permission email, your Open-Meteo invoice, your Esri
account, and any market-data licence. Buyers check this, and it makes the app worth more.

## Sources

- IMF data terms (commercial reuse: email copyright@imf.org): https://www.imf.org/en/About/copyright-and-terms
- PortWatch: https://portwatch.imf.org
- GDACS terms of use: https://www.gdacs.org/About/termofuse.aspx
- European Commission reuse notice (CC BY 4.0): https://commission.europa.eu/legal-notice_en
- OpenSky terms & data licence: https://opensky-network.org/about/terms-of-use
- OpenSky API docs ("research and non-commercial purposes"): https://openskynetwork.github.io/opensky-api/
- adsb.lol (ODbL open data): https://www.adsb.lol/docs/open-data/api/
- Open-Meteo terms: https://open-meteo.com/en/terms
- Open-Meteo pricing: https://open-meteo.com/en/pricing
- Open-Meteo plan prices ($29 / $99): https://openmeteo.substack.com/p/api-subscriptions-for-commercial
- Google News feed notice: inside the feed itself, e.g. https://news.google.com/rss/search?q=shipping
- Google News terms: https://www.google.com/intl/en_us/terms_google_news.html
- GDELT terms (free commercial use with citation): https://www.gdeltproject.org/about.html
- yfinance ("personal use only"): https://pypi.org/project/yfinance/
- Yahoo API terms: https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html
- Alpha Vantage prices: https://www.alphavantage.co/premium/
- Twelve Data prices: https://twelvedata.com/pricing
- Esri World Imagery item (Esri Master License Agreement): https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9
- Esri attribution rules: https://developers.arcgis.com/documentation/esri-and-data-attribution/
- ArcGIS Location Platform pricing (2M free tiles): https://location.arcgis.com/pricing/
- ArcGIS Location Platform deployment (commercial apps): https://location.arcgis.com/help/deployment/
- three-globe licence (MIT): https://github.com/vasturiano/three-globe/blob/master/LICENSE
- globe.gl: https://github.com/vasturiano/globe.gl
- NASA Blue Marble: https://visibleearth.nasa.gov/collection/1484/blue-marble
- jsDelivr: https://www.jsdelivr.com/about
- Font Awesome Free licence: https://fontawesome.com/license/free
