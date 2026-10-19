# markets.py
# Every market Krypton tracks, grouped by SECTOR.
# name -> Yahoo Finance code. All are real, actively traded stocks, funds, indexes or futures.

SECTORS = {
    "🛢️ Energy": {
        "Brent oil": "BZ=F", "WTI oil": "CL=F", "Natural gas (US)": "NG=F", "Gasoline": "RB=F",
        "ExxonMobil": "XOM", "Chevron": "CVX", "Shell": "SHEL", "BP": "BP", "TotalEnergies": "TTE",
        "Occidental": "OXY", "Cheniere (LNG exports)": "LNG", "SLB (oil services)": "SLB",
        "Halliburton": "HAL", "Valero (refiner)": "VLO", "European natural gas (TTF)": "TTF=F",
        "Suncor (Canadian oil sands)": "SU", "Canadian Natural Resources": "CNQ",
    },
    "🚢 Shipping": {
        "Dry bulk shipping rates": "BDRY", "ZIM (containers)": "ZIM", "Matson (Pacific containers)": "MATX",
        "Danaos (container ships)": "DAC", "Frontline (oil tankers)": "FRO", "Scorpio Tankers": "STNG",
        "International Seaways": "INSW", "Star Bulk (dry bulk)": "SBLK",
    },
    "✈️ Airlines & logistics": {
        "FedEx": "FDX", "UPS": "UPS", "Delta": "DAL", "United": "UAL", "American Airlines": "AAL",
        "Southwest": "LUV", "Airlines fund": "JETS", "Expeditors (freight)": "EXPD",
        "C.H. Robinson (freight)": "CHRW", "Carnival (cruises)": "CCL", "Royal Caribbean (cruises)": "RCL",
    },
    "🚗 Autos": {
        "Toyota": "TM", "Honda": "HMC", "Tesla": "TSLA", "Ford": "F", "General Motors": "GM",
        "Volkswagen": "VOW3.DE",
    },
    "🛡️ Defence & aerospace": {
        "Defence stocks fund": "ITA", "Lockheed Martin": "LMT", "RTX (Raytheon)": "RTX",
        "Northrop Grumman": "NOC", "General Dynamics": "GD", "L3Harris": "LHX", "Boeing": "BA",
        "Rheinmetall": "RHM.DE", "BAE Systems": "BA.L",
    },
    "🏠 Insurance & rebuilding": {
        "Allstate": "ALL", "Progressive": "PGR", "Travelers": "TRV", "Chubb": "CB",
        "Universal Insurance (Florida)": "UVE", "HCI Group (Florida)": "HCI", "Home Depot": "HD",
        "Lowe's": "LOW", "Generac (generators)": "GNRC",
    },
    "🌾 Agriculture & food": {
        "Wheat": "ZW=F", "Corn": "ZC=F", "Soybeans": "ZS=F", "Coffee": "KC=F", "Sugar": "SB=F",
        "Cocoa": "CC=F", "Orange juice": "OJ=F", "Archer-Daniels-Midland": "ADM", "Bunge": "BG",
        "Deere (farm machinery)": "DE", "Nutrien (fertiliser)": "NTR", "Mosaic (fertiliser)": "MOS",
    },
    "⛏️ Metals & mining": {
        "Gold": "GC=F", "Silver": "SI=F", "Copper": "HG=F", "Freeport-McMoRan (copper)": "FCX",
        "Newmont (gold)": "NEM", "BHP": "BHP", "Rio Tinto": "RIO", "Vale (iron ore)": "VALE",
        "Albemarle (lithium)": "ALB", "MP Materials (rare earths)": "MP", "SQM (Chilean lithium)": "SQM",
    },
    "💻 Semiconductors & tech": {
        "TSMC": "TSM", "Nvidia": "NVDA", "ASML": "ASML", "Intel": "INTC", "Micron": "MU", "AMD": "AMD",
        "Applied Materials": "AMAT", "Chip stocks fund": "SOXX", "Apple": "AAPL",
        "Texas Instruments": "TXN", "Analog Devices": "ADI", "Western Digital (hard drives)": "WDC",
        "Seagate (hard drives)": "STX",
    },
    "⚡ Utilities": {
        "NextEra Energy (Florida)": "NEE", "Duke Energy": "DUK", "Southern Company": "SO",
        "PG&E (California)": "PCG", "Edison International (California)": "EIX",
    },
    "🌍 Countries & indexes": {
        "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Euro Stoxx 50": "^STOXX50E", "Japan (Nikkei)": "^N225",
        "Hong Kong (Hang Seng)": "^HSI", "South Korea (KOSPI)": "^KS11", "Taiwan (TAIEX)": "^TWII",
        "India (Nifty 50)": "^NSEI", "Emerging markets fund": "EEM", "Philippines fund": "EPHE",
        "Indonesia fund": "EIDO", "Mexico fund": "EWW", "Brazil fund": "EWZ", "Chile fund": "ECH",
        "Turkey fund": "TUR", "Israel fund": "EIS", "Saudi Arabia fund": "KSA",
    },
    "📉 Fear & safe havens": {
        "Volatility index (VIX)": "^VIX", "US dollar index": "DX-Y.NYB", "US 10-year yield": "^TNX",
        "Japanese yen (per $)": "JPY=X", "Swiss franc (per $)": "CHF=X",
    },
}

# Flat lookups
ALL_MARKETS = {name: code for group in SECTORS.values() for name, code in group.items()}
SECTOR_OF = {name: sector for sector, group in SECTORS.items() for name in group}
