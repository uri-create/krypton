# layers.py
# The fixed "map knowledge" for Krypton: cargo airports, sea lanes, air cargo lanes,
# and the conflict zones we watch. The LIVE numbers (traffic, news, weather) come from
# data_sources.py; this file only says WHERE things are and WHY they matter.

# ---------------------------------------------------------------------------
# Map categories: icon (Font Awesome name), colour, and the label used in the filter
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Shipping":  {"emoji": "🚢", "icon": "fa-ship",          "colour": "#2ee59d"},
    "Air cargo": {"emoji": "✈️", "icon": "fa-plane",         "colour": "#00e0ff"},
    "Weather":   {"emoji": "☁️", "icon": "fa-cloud",         "colour": "#9ecbff"},
    "Military":  {"emoji": "🛡️", "icon": "fa-shield-halved", "colour": "#ff2d55"},
    "Quakes & volcanoes": {"emoji": "🌋", "icon": "fa-volcano", "colour": "#b388ff"},
}

# ---------------------------------------------------------------------------
# The world's key AIR CARGO hubs
# ---------------------------------------------------------------------------
AIR_HUBS = {
    "Hong Kong (HKG)": {
        "lat": 22.31, "lon": 113.92,
        "role": "For years the world's busiest cargo airport by tonnage. Ships electronics and "
                "e-commerce goods from southern China to the world.",
        "markets": ["FedEx", "UPS", "S&P 500"],
    },
    "Shanghai Pudong (PVG)": {
        "lat": 31.14, "lon": 121.81,
        "role": "China's largest air cargo airport: electronics, car parts and online-shopping parcels.",
        "markets": ["FedEx", "S&P 500"],
    },
    "Memphis (MEM)": {
        "lat": 35.04, "lon": -89.98,
        "role": "FedEx's global 'SuperHub'. Most FedEx Express parcels in the US pass through here overnight.",
        "markets": ["FedEx"],
    },
    "Louisville (SDF)": {
        "lat": 38.17, "lon": -85.74,
        "role": "UPS Worldport, the main sorting hub for UPS's global air network.",
        "markets": ["UPS"],
    },
    "Anchorage (ANC)": {
        "lat": 61.17, "lon": -150.0,
        "role": "The refuelling stop for cargo jets flying between Asia and North America. "
                "A slowdown here usually means trans-Pacific air trade is slowing.",
        "markets": ["FedEx", "UPS"],
    },
    "Incheon (ICN)": {
        "lat": 37.46, "lon": 126.44,
        "role": "South Korea's gateway. Ships semiconductors and electronics (Samsung, SK Hynix).",
        "markets": ["S&P 500"],
    },
    "Taipei Taoyuan (TPE)": {
        "lat": 25.08, "lon": 121.23,
        "role": "Taiwan's main cargo airport. Advanced computer chips are flown out from here.",
        "markets": ["S&P 500"],
    },
    "Tokyo Narita (NRT)": {
        "lat": 35.77, "lon": 140.39,
        "role": "Japan's main international cargo airport: machinery, car parts and electronics.",
        "markets": ["S&P 500"],
    },
    "Singapore (SIN)": {
        "lat": 1.36, "lon": 103.99,
        "role": "Southeast Asia's main air hub, linking Asian factories with Europe and Australia.",
        "markets": ["S&P 500"],
    },
    "Dubai (DXB)": {
        "lat": 25.25, "lon": 55.36,
        "role": "Emirates SkyCargo's base. Links Asia, Europe and Africa, close to the Strait of Hormuz.",
        "markets": ["Airlines fund", "Brent oil"],
    },
    "Doha (DOH)": {
        "lat": 25.27, "lon": 51.61,
        "role": "Home of Qatar Airways Cargo, one of the world's biggest cargo airlines.",
        "markets": ["Airlines fund", "Natural gas (US)"],
    },
    "Istanbul (IST)": {
        "lat": 41.26, "lon": 28.74,
        "role": "Turkish Cargo's hub, a fast-growing bridge between Europe, Asia and Africa.",
        "markets": ["Airlines fund"],
    },
    "Frankfurt (FRA)": {
        "lat": 50.04, "lon": 8.56,
        "role": "Europe's leading cargo airport and home of Lufthansa Cargo: pharma, machinery, cars.",
        "markets": ["Airlines fund", "S&P 500"],
    },
    "Leipzig (LEJ)": {
        "lat": 51.42, "lon": 12.24,
        "role": "DHL's main European hub. Busy all night sorting express parcels.",
        "markets": ["Airlines fund"],
    },
    "Chicago O'Hare (ORD)": {
        "lat": 41.98, "lon": -87.90,
        "role": "The busiest cargo gateway in the US Midwest, linking Asia and Europe to US factories.",
        "markets": ["FedEx", "UPS"],
    },
    "Los Angeles (LAX)": {
        "lat": 33.94, "lon": -118.41,
        "role": "Main US West Coast gateway for Asian air freight.",
        "markets": ["FedEx", "UPS"],
    },
    "Miami (MIA)": {
        "lat": 25.80, "lon": -80.29,
        "role": "The gateway for air trade with Latin America: flowers, fresh food, phones.",
        "markets": ["Airlines fund"],
    },
}

# Main air cargo lanes (pairs of hubs). Drawn as curved lines.
AIR_ROUTES = [
    ("Hong Kong (HKG)", "Anchorage (ANC)"), ("Shanghai Pudong (PVG)", "Anchorage (ANC)"),
    ("Incheon (ICN)", "Anchorage (ANC)"), ("Anchorage (ANC)", "Memphis (MEM)"),
    ("Anchorage (ANC)", "Louisville (SDF)"), ("Anchorage (ANC)", "Chicago O'Hare (ORD)"),
    ("Hong Kong (HKG)", "Los Angeles (LAX)"), ("Taipei Taoyuan (TPE)", "Los Angeles (LAX)"),
    ("Hong Kong (HKG)", "Frankfurt (FRA)"), ("Shanghai Pudong (PVG)", "Leipzig (LEJ)"),
    ("Hong Kong (HKG)", "Dubai (DXB)"), ("Dubai (DXB)", "Frankfurt (FRA)"),
    ("Singapore (SIN)", "Doha (DOH)"), ("Doha (DOH)", "Leipzig (LEJ)"),
    ("Istanbul (IST)", "Frankfurt (FRA)"), ("Frankfurt (FRA)", "Chicago O'Hare (ORD)"),
    ("Leipzig (LEJ)", "Louisville (SDF)"), ("Miami (MIA)", "Frankfurt (FRA)"),
    ("Tokyo Narita (NRT)", "Anchorage (ANC)"),
]

# ---------------------------------------------------------------------------
# Main SEA cargo lanes: a list of (lat, lon) waypoints, plus the chokepoints they pass.
# Longitudes past 180 are on purpose (so lines cross the Pacific instead of the whole map).
# ---------------------------------------------------------------------------
SEA_ROUTES = {
    "Asia–Europe via Suez": {
        "points": [(31.2, 122.5), (22, 115), (1.2, 104), (2.5, 101.5), (5.5, 80.5), (12, 52),
                   (12.6, 43.4), (20, 38.5), (27.5, 34), (30.6, 32.3), (33.5, 27), (37, 12),
                   (35.95, -5.6), (40, -10.5), (48.5, -5.5), (51.0, 1.45), (51.95, 4.0)],
        "chokepoints": ["Malacca Strait", "Bab el-Mandeb Strait", "Suez Canal", "Gibraltar Strait",
                        "Dover Strait"],
        "carries": "Containers of consumer goods from China to Europe, and European exports back.",
    },
    "Asia–Europe via Cape of Good Hope": {
        "points": [(1.2, 104), (-6, 95), (-20, 70), (-34.4, 18.5), (-20, 5), (5, -18), (30, -16),
                   (40, -10.5), (48.5, -5.5), (51.0, 1.45), (51.95, 4.0)],
        "chokepoints": ["Cape of Good Hope", "Dover Strait"],
        "carries": "The long way round, used when the Red Sea is too dangerous. Adds about 10–14 days.",
    },
    "Persian Gulf oil to East Asia": {
        "points": [(26.7, 50.2), (26.6, 56.3), (22, 62), (8, 77), (5.5, 80.5), (2.5, 101.5),
                   (1.2, 104), (10, 112), (22, 118), (30, 126), (35, 139)],
        "chokepoints": ["Strait of Hormuz", "Malacca Strait"],
        "carries": "Crude oil and LNG from Saudi Arabia, Iraq, the UAE and Qatar to China, Japan and Korea.",
    },
    "Persian Gulf oil to Europe": {
        "points": [(26.7, 50.2), (26.6, 56.3), (22, 62), (14, 52), (12.6, 43.4), (20, 38.5),
                   (27.5, 34), (30.6, 32.3), (33.5, 27), (36, 15)],
        "chokepoints": ["Strait of Hormuz", "Bab el-Mandeb Strait", "Suez Canal"],
        "carries": "Crude oil and fuel from the Gulf to Europe.",
    },
    "Trans-Pacific": {
        "points": [(31.2, 122.5), (34, 145), (42, 180), (40, 210), (33.7, 241.7)],
        "chokepoints": [],
        "carries": "The world's busiest container trade: Asian factories to US West Coast ports.",
    },
    "Trans-Atlantic": {
        "points": [(51.95, 4.0), (51.0, 1.45), (49.5, -6), (45, -30), (40.5, -73.8)],
        "chokepoints": ["Dover Strait"],
        "carries": "Machinery, cars, chemicals and energy between Europe and the US.",
    },
    "US Gulf to Asia via Panama": {
        "points": [(29, -89.5), (23, -86), (21.5, -85.5), (9.4, -79.9), (8.5, -79.6), (12, -100),
                   (25, -140), (32, -170), (33, -200), (31.2, -237.5)],
        "chokepoints": ["Panama Canal"],
        "carries": "US grain, soybeans and LNG heading to Asia.",
    },
    "Black Sea grain & oil": {
        "points": [(46.4, 30.8), (44.5, 31.5), (41.1, 29.05), (40.2, 26.4), (37.5, 25), (34, 25),
                   (31.5, 32.3)],
        "chokepoints": ["Bosporus Strait", "Suez Canal"],
        "carries": "Ukrainian and Russian wheat, corn and sunflower oil, plus Russian crude.",
    },
}

# ---------------------------------------------------------------------------
# CONFLICT watchlist. A zone only appears on the map when recent news shows military activity.
# "background" = the long-term story (what led to it). Live news provides the latest.
# "box" = (south, west, north, east) area used to count aircraft overhead.
# ---------------------------------------------------------------------------
CONFLICT_ZONES = {
    "Russia–Ukraine war": {
        "lat": 48.5, "lon": 37.5, "box": (44.4, 22.1, 52.4, 40.2),
        "news": "Ukraine Russia attack OR strike OR offensive",
        "background": "Russia launched a full-scale invasion of Ukraine in February 2022. Fighting is "
                      "concentrated in the east and south, with drone and missile strikes on cities, "
                      "power plants, ports and refineries on both sides.",
        "markets": ["Wheat", "Natural gas (US)", "Brent oil", "Defence stocks fund"],
    },
    "Black Sea shipping attacks": {
        "lat": 43.6, "lon": 33.5, "box": (41.0, 28.0, 46.5, 41.5),
        "news": "Black Sea drone attack ship",
        "background": "Since 2022 the Black Sea has been a war zone. Naval drones, missiles and mines "
                      "threaten tankers and grain ships leaving Ukrainian and Russian ports.",
        "markets": ["Wheat", "Brent oil"],
    },
    "Iran & the Gulf": {
        "lat": 32.0, "lon": 53.0, "box": (25.0, 44.0, 39.8, 63.3),
        "news": "Iran military attack OR strike",
        "background": "Iran borders the Strait of Hormuz. Its long-running confrontation with the US, "
                      "Israel and some Gulf states has repeatedly spilled into attacks on, or seizures "
                      "of, merchant ships, and strikes on military and energy targets.",
        "markets": ["Brent oil", "WTI oil", "Natural gas (US)", "Defence stocks fund"],
    },
    "Israel, Gaza & Lebanon": {
        "lat": 31.6, "lon": 34.9, "box": (29.5, 34.2, 33.4, 36.6),
        "news": "Israel Gaza Lebanon strike",
        "background": "A major war began after Hamas's attack on Israel on 7 October 2023. Related "
                      "fighting has involved Hezbollah in Lebanon, the Houthis in Yemen and Iran.",
        "markets": ["Brent oil", "Defence stocks fund", "Gold"],
    },
    "Red Sea & Yemen (Houthis)": {
        "lat": 15.3, "lon": 44.2, "box": (12.0, 41.0, 18.0, 46.0),
        "news": "Houthi Red Sea attack ship",
        "background": "Yemen's Houthi movement began attacking commercial ships in the Red Sea in late "
                      "2023. Many shipping companies now sail around Africa instead of using Suez.",
        "markets": ["Brent oil", "Dry bulk shipping rates"],
    },
    "Sudan civil war": {
        "lat": 15.6, "lon": 32.5, "box": (9.0, 22.0, 22.0, 38.5),
        "news": "Sudan RSF army fighting",
        "background": "Sudan's army and the Rapid Support Forces (RSF) have been at war since April 2023, "
                      "creating one of the world's largest humanitarian crises. Sudan borders the Red Sea.",
        "markets": ["Gold", "Wheat"],
    },
    "Taiwan Strait tensions": {
        "lat": 23.7, "lon": 120.9, "box": (21.5, 117.5, 26.5, 123.0),
        "news": "Taiwan China military drills",
        "background": "China claims Taiwan and regularly holds military drills around it. Taiwan makes most "
                      "of the world's advanced chips, and the strait is one of the busiest shipping lanes.",
        "markets": ["S&P 500", "Gold", "Defence stocks fund"],
    },
    "South China Sea": {
        "lat": 12.0, "lon": 114.5, "box": (5.0, 108.0, 20.0, 120.0),
        "news": "South China Sea Philippines China coast guard",
        "background": "China, the Philippines, Vietnam and others claim overlapping parts of the sea. "
                      "Clashes between coast guard and navy ships happen regularly. Trillions of dollars "
                      "of trade pass through every year.",
        "markets": ["S&P 500", "Dry bulk shipping rates"],
    },
    "Korean Peninsula": {
        "lat": 39.0, "lon": 125.75, "box": (37.7, 124.2, 43.0, 130.7),
        "news": "North Korea missile launch",
        "background": "North Korea regularly tests ballistic missiles. South Korea is a key supplier of "
                      "memory chips, ships and cars.",
        "markets": ["S&P 500", "Defence stocks fund"],
    },
    "India–Pakistan (Kashmir)": {
        "lat": 34.0, "lon": 74.5, "box": (32.0, 72.5, 36.5, 77.5),
        "news": "India Pakistan Kashmir military",
        "background": "Kashmir is disputed between two nuclear-armed neighbours that have fought several "
                      "wars and had military clashes as recently as 2025.",
        "markets": ["Gold", "Defence stocks fund"],
    },
    "Myanmar civil war": {
        "lat": 21.0, "lon": 96.0, "box": (10.0, 92.2, 28.5, 101.2),
        "news": "Myanmar junta resistance fighting",
        "background": "Fighting between the military government and resistance groups has spread across "
                      "the country since the 2021 coup.",
        "markets": ["Gold"],
    },
    "Eastern DR Congo": {
        "lat": -1.68, "lon": 29.22, "box": (-5.0, 26.0, 2.0, 31.0),
        "news": "Congo M23 fighting",
        "background": "Armed groups including M23 fight over territory rich in minerals used in phones "
                      "and batteries (cobalt, tin, tantalum, gold).",
        "markets": ["Gold"],
    },
    "Sahel insurgencies": {
        "lat": 14.0, "lon": -2.0, "box": (10.0, -12.0, 20.0, 16.0),
        "news": "Mali Burkina Faso Niger jihadist attack",
        "background": "Jihadist insurgencies and military coups across Mali, Burkina Faso and Niger. The "
                      "region produces gold and uranium.",
        "markets": ["Gold"],
    },
    "Venezuela & the Caribbean": {
        "lat": 8.0, "lon": -66.0, "box": (0.6, -73.4, 12.5, -59.8),
        "news": "Venezuela US military",
        "background": "Tensions between the US and Venezuela's government, including US naval deployments "
                      "in the Caribbean. Venezuela has the world's largest proven oil reserves.",
        "markets": ["Brent oil", "WTI oil"],
    },
}
