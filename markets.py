# markets.py
# Every market Krypton tracks, grouped into broad sectors.
#
# Each row: internal name (used throughout Krypton's research links), Yahoo Finance ticker, official
# full name (what people see), and sector. Company sectors follow the usual industry groupings;
# commodities, indices and currencies get their own groups because they aren't company shares.

MARKET_TABLE = [
    # ---- Energy
    ("ExxonMobil", "XOM", "Exxon Mobil Corporation", "Energy"),
    ("Chevron", "CVX", "Chevron Corporation", "Energy"),
    ("Shell", "SHEL", "Shell plc", "Energy"),
    ("BP", "BP", "BP p.l.c.", "Energy"),
    ("TotalEnergies", "TTE", "TotalEnergies SE", "Energy"),
    ("Occidental", "OXY", "Occidental Petroleum Corporation", "Energy"),
    ("Cheniere (LNG exports)", "LNG", "Cheniere Energy, Inc.", "Energy"),
    ("SLB (oil services)", "SLB", "SLB N.V. (Schlumberger)", "Energy"),
    ("Halliburton", "HAL", "Halliburton Company", "Energy"),
    ("Valero (refiner)", "VLO", "Valero Energy Corporation", "Energy"),
    ("Suncor (Canadian oil sands)", "SU", "Suncor Energy Inc.", "Energy"),
    ("Canadian Natural Resources", "CNQ", "Canadian Natural Resources Limited", "Energy"),
    # ---- Materials & Mining
    ("Freeport-McMoRan (copper)", "FCX", "Freeport-McMoRan Inc.", "Materials & Mining"),
    ("Newmont (gold)", "NEM", "Newmont Corporation", "Materials & Mining"),
    ("BHP", "BHP", "BHP Group Limited", "Materials & Mining"),
    ("Rio Tinto", "RIO", "Rio Tinto Group", "Materials & Mining"),
    ("Vale (iron ore)", "VALE", "Vale S.A.", "Materials & Mining"),
    ("Albemarle (lithium)", "ALB", "Albemarle Corporation", "Materials & Mining"),
    ("MP Materials (rare earths)", "MP", "MP Materials Corp.", "Materials & Mining"),
    ("SQM (Chilean lithium)", "SQM", "Sociedad Química y Minera de Chile S.A.", "Materials & Mining"),
    # ---- Transportation & Logistics
    ("ZIM (containers)", "ZIM", "ZIM Integrated Shipping Services Ltd.", "Transportation & Logistics"),
    ("Matson (Pacific containers)", "MATX", "Matson, Inc.", "Transportation & Logistics"),
    ("Danaos (container ships)", "DAC", "Danaos Corporation", "Transportation & Logistics"),
    ("Frontline (oil tankers)", "FRO", "Frontline plc", "Transportation & Logistics"),
    ("Scorpio Tankers", "STNG", "Scorpio Tankers Inc.", "Transportation & Logistics"),
    ("International Seaways", "INSW", "International Seaways, Inc.", "Transportation & Logistics"),
    ("Star Bulk (dry bulk)", "SBLK", "Star Bulk Carriers Corp.", "Transportation & Logistics"),
    ("Dry bulk shipping rates", "BDRY", "Breakwave Dry Bulk Shipping ETF", "Transportation & Logistics"),
    ("FedEx", "FDX", "FedEx Corporation", "Transportation & Logistics"),
    ("UPS", "UPS", "United Parcel Service, Inc.", "Transportation & Logistics"),
    ("Expeditors (freight)", "EXPD", "Expeditors International of Washington, Inc.", "Transportation & Logistics"),
    ("C.H. Robinson (freight)", "CHRW", "C.H. Robinson Worldwide, Inc.", "Transportation & Logistics"),
    ("Delta", "DAL", "Delta Air Lines, Inc.", "Transportation & Logistics"),
    ("United", "UAL", "United Airlines Holdings, Inc.", "Transportation & Logistics"),
    ("American Airlines", "AAL", "American Airlines Group Inc.", "Transportation & Logistics"),
    ("Southwest", "LUV", "Southwest Airlines Co.", "Transportation & Logistics"),
    ("Airlines fund", "JETS", "U.S. Global Jets ETF", "Transportation & Logistics"),
    # ---- Aerospace & Defense
    ("Lockheed Martin", "LMT", "Lockheed Martin Corporation", "Aerospace & Defense"),
    ("RTX (Raytheon)", "RTX", "RTX Corporation", "Aerospace & Defense"),
    ("Northrop Grumman", "NOC", "Northrop Grumman Corporation", "Aerospace & Defense"),
    ("General Dynamics", "GD", "General Dynamics Corporation", "Aerospace & Defense"),
    ("L3Harris", "LHX", "L3Harris Technologies, Inc.", "Aerospace & Defense"),
    ("Boeing", "BA", "The Boeing Company", "Aerospace & Defense"),
    ("Rheinmetall", "RHM.DE", "Rheinmetall AG", "Aerospace & Defense"),
    ("BAE Systems", "BA.L", "BAE Systems plc", "Aerospace & Defense"),
    ("Defence stocks fund", "ITA", "iShares U.S. Aerospace & Defense ETF", "Aerospace & Defense"),
    # ---- Consumer Discretionary
    ("Toyota", "TM", "Toyota Motor Corporation", "Consumer Discretionary"),
    ("Honda", "HMC", "Honda Motor Co., Ltd.", "Consumer Discretionary"),
    ("Tesla", "TSLA", "Tesla, Inc.", "Consumer Discretionary"),
    ("Ford", "F", "Ford Motor Company", "Consumer Discretionary"),
    ("General Motors", "GM", "General Motors Company", "Consumer Discretionary"),
    ("Volkswagen", "VOW3.DE", "Volkswagen AG", "Consumer Discretionary"),
    ("Carnival (cruises)", "CCL", "Carnival Corporation & plc", "Consumer Discretionary"),
    ("Royal Caribbean (cruises)", "RCL", "Royal Caribbean Cruises Ltd.", "Consumer Discretionary"),
    ("Home Depot", "HD", "The Home Depot, Inc.", "Consumer Discretionary"),
    ("Lowe's", "LOW", "Lowe's Companies, Inc.", "Consumer Discretionary"),
    # ---- Financials
    ("Allstate", "ALL", "The Allstate Corporation", "Financials"),
    ("Progressive", "PGR", "The Progressive Corporation", "Financials"),
    ("Travelers", "TRV", "The Travelers Companies, Inc.", "Financials"),
    ("Chubb", "CB", "Chubb Limited", "Financials"),
    ("Universal Insurance (Florida)", "UVE", "Universal Insurance Holdings, Inc.", "Financials"),
    ("HCI Group (Florida)", "HCI", "HCI Group, Inc.", "Financials"),
    # ---- Agriculture & Food
    ("Archer-Daniels-Midland", "ADM", "Archer-Daniels-Midland Company", "Agriculture & Food"),
    ("Bunge", "BG", "Bunge Global SA", "Agriculture & Food"),
    ("Deere (farm machinery)", "DE", "Deere & Company", "Agriculture & Food"),
    ("Nutrien (fertiliser)", "NTR", "Nutrien Ltd.", "Agriculture & Food"),
    ("Mosaic (fertiliser)", "MOS", "The Mosaic Company", "Agriculture & Food"),
    # ---- Technology
    ("TSMC", "TSM", "Taiwan Semiconductor Manufacturing Company Limited", "Technology"),
    ("Nvidia", "NVDA", "NVIDIA Corporation", "Technology"),
    ("ASML", "ASML", "ASML Holding N.V.", "Technology"),
    ("Intel", "INTC", "Intel Corporation", "Technology"),
    ("Micron", "MU", "Micron Technology, Inc.", "Technology"),
    ("AMD", "AMD", "Advanced Micro Devices, Inc.", "Technology"),
    ("Applied Materials", "AMAT", "Applied Materials, Inc.", "Technology"),
    ("Apple", "AAPL", "Apple Inc.", "Technology"),
    ("Texas Instruments", "TXN", "Texas Instruments Incorporated", "Technology"),
    ("Analog Devices", "ADI", "Analog Devices, Inc.", "Technology"),
    ("Western Digital (hard drives)", "WDC", "Western Digital Corporation", "Technology"),
    ("Seagate (hard drives)", "STX", "Seagate Technology Holdings plc", "Technology"),
    ("Chip stocks fund", "SOXX", "iShares Semiconductor ETF", "Technology"),
    # ---- Utilities & Power
    ("NextEra Energy (Florida)", "NEE", "NextEra Energy, Inc.", "Utilities & Power"),
    ("Duke Energy", "DUK", "Duke Energy Corporation", "Utilities & Power"),
    ("Southern Company", "SO", "The Southern Company", "Utilities & Power"),
    ("PG&E (California)", "PCG", "PG&E Corporation", "Utilities & Power"),
    ("Edison International (California)", "EIX", "Edison International", "Utilities & Power"),
    ("Generac (generators)", "GNRC", "Generac Holdings Inc.", "Utilities & Power"),
    # ---- Commodities (futures prices, not companies)
    ("Brent oil", "BZ=F", "Brent Crude Oil Futures", "Commodities"),
    ("WTI oil", "CL=F", "WTI Crude Oil Futures", "Commodities"),
    ("Natural gas (US)", "NG=F", "Henry Hub Natural Gas Futures", "Commodities"),
    ("European natural gas (TTF)", "TTF=F", "Dutch TTF Natural Gas Futures", "Commodities"),
    ("Gasoline", "RB=F", "RBOB Gasoline Futures", "Commodities"),
    ("Gold", "GC=F", "Gold Futures", "Commodities"),
    ("Silver", "SI=F", "Silver Futures", "Commodities"),
    ("Copper", "HG=F", "Copper Futures", "Commodities"),
    ("Wheat", "ZW=F", "Wheat Futures", "Commodities"),
    ("Corn", "ZC=F", "Corn Futures", "Commodities"),
    ("Soybeans", "ZS=F", "Soybean Futures", "Commodities"),
    ("Coffee", "KC=F", "Coffee Futures", "Commodities"),
    ("Sugar", "SB=F", "Sugar No. 11 Futures", "Commodities"),
    ("Cocoa", "CC=F", "Cocoa Futures", "Commodities"),
    ("Orange juice", "OJ=F", "Orange Juice Futures", "Commodities"),
    # ---- Global Indices & Country Funds
    ("S&P 500", "^GSPC", "S&P 500 Index", "Global Indices"),
    ("Nasdaq", "^IXIC", "Nasdaq Composite Index", "Global Indices"),
    ("Euro Stoxx 50", "^STOXX50E", "Euro Stoxx 50 Index", "Global Indices"),
    ("Japan (Nikkei)", "^N225", "Nikkei 225 Index", "Global Indices"),
    ("Hong Kong (Hang Seng)", "^HSI", "Hang Seng Index", "Global Indices"),
    ("South Korea (KOSPI)", "^KS11", "KOSPI Composite Index", "Global Indices"),
    ("Taiwan (TAIEX)", "^TWII", "Taiwan Capitalization Weighted Stock Index", "Global Indices"),
    ("India (Nifty 50)", "^NSEI", "NIFTY 50 Index", "Global Indices"),
    ("Emerging markets fund", "EEM", "iShares MSCI Emerging Markets ETF", "Global Indices"),
    ("Philippines fund", "EPHE", "iShares MSCI Philippines ETF", "Global Indices"),
    ("Indonesia fund", "EIDO", "iShares MSCI Indonesia ETF", "Global Indices"),
    ("Mexico fund", "EWW", "iShares MSCI Mexico ETF", "Global Indices"),
    ("Brazil fund", "EWZ", "iShares MSCI Brazil ETF", "Global Indices"),
    ("Chile fund", "ECH", "iShares MSCI Chile ETF", "Global Indices"),
    ("Turkey fund", "TUR", "iShares MSCI Turkey ETF", "Global Indices"),
    ("Israel fund", "EIS", "iShares MSCI Israel ETF", "Global Indices"),
    ("Saudi Arabia fund", "KSA", "iShares MSCI Saudi Arabia ETF", "Global Indices"),
    # ---- Rates, Currencies & Volatility
    ("Volatility index (VIX)", "^VIX", "CBOE Volatility Index", "Rates, Currencies & Volatility"),
    ("US dollar index", "DX-Y.NYB", "U.S. Dollar Index", "Rates, Currencies & Volatility"),
    ("US 10-year yield", "^TNX", "U.S. 10-Year Treasury Yield", "Rates, Currencies & Volatility"),
    ("Japanese yen (per $)", "JPY=X", "U.S. Dollar / Japanese Yen", "Rates, Currencies & Volatility"),
    ("Swiss franc (per $)", "CHF=X", "U.S. Dollar / Swiss Franc", "Rates, Currencies & Volatility"),
]

# Sectors made of company shares (shown first) vs. other kinds of markets
EQUITY_SECTORS = ["Energy", "Materials & Mining", "Transportation & Logistics", "Aerospace & Defense",
                  "Consumer Discretionary", "Financials", "Agriculture & Food", "Technology", "Utilities & Power"]
OTHER_GROUPS = ["Commodities", "Global Indices", "Rates, Currencies & Volatility"]

SECTORS = {sector: {name: code for name, code, _, s in MARKET_TABLE if s == sector}
           for sector in EQUITY_SECTORS + OTHER_GROUPS}

# Flat lookups
ALL_MARKETS = {name: code for name, code, _, _ in MARKET_TABLE}
SECTOR_OF = {name: sector for name, _, _, sector in MARKET_TABLE}
FULL_NAME = {name: full for name, _, full, _ in MARKET_TABLE}


def label(name):
    """How a market is shown to people: official name with its ticker, e.g. 'Exxon Mobil Corporation (XOM)'."""
    if name not in ALL_MARKETS:
        return name
    return f"{FULL_NAME[name]} ({ALL_MARKETS[name]})"


def ticker(name):
    return ALL_MARKETS.get(name, "")
