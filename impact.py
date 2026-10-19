# impact.py
# WHICH markets an event moves depends on WHERE it happens and WHAT it is.
# A typhoon over Taiwan's chip fabs, a hurricane in Florida and a volcano in the Philippines
# hit completely different companies. This file is the research behind that.
#
# Each impact = (market name from markets.py, expected direction, why)
#   "▲" = tends to rise, "▼" = tends to fall, "◆" = mixed / depends on details
# The app then checks what the market ACTUALLY did, so you can see if the pattern held.

UP, DOWN, MIXED = "▲", "▼", "◆"

# ---------------------------------------------------------------------------
# REGIONS: boxes are (south, west, north, east). First match wins, so small regions come first.
# ---------------------------------------------------------------------------
REGIONS = [
    ("Florida", [(24.3, -87.7, 31.0, -79.8)]),
    ("US Gulf Coast", [(25.0, -98.0, 31.5, -87.7)]),
    ("US East Coast", [(31.0, -82.0, 45.5, -66.0)]),
    ("US West Coast", [(31.0, -125.0, 49.5, -114.0)]),
    ("Alaska & Aleutians", [(50.0, -180.0, 72.0, -129.0), (50.0, 165.0, 60.0, 180.0)]),
    ("Canada", [(49.5, -141.0, 70.0, -52.0)]),
    ("Caribbean", [(10.0, -86.0, 24.0, -59.0)]),
    ("Panama & Central America", [(7.0, -92.5, 18.5, -77.0)]),
    ("Mexico", [(14.5, -118.0, 32.7, -86.5)]),
    ("Taiwan", [(21.5, 119.0, 25.6, 122.5)]),
    ("Japan", [(24.0, 122.5, 46.0, 146.0)]),
    ("South Korea", [(33.0, 124.5, 38.7, 131.0)]),
    ("Philippines", [(4.5, 116.0, 21.2, 127.5)]),
    ("Western Pacific islands (Guam & Micronesia)", [(0.0, 130.0, 24.0, 175.0)]),
    ("Indonesia", [(-11.0, 95.0, 6.0, 141.5)]),
    ("Southeast Asia mainland", [(1.0, 92.0, 23.5, 110.0)]),
    ("China", [(18.0, 97.0, 45.0, 123.0)]),
    ("India & South Asia", [(5.0, 60.5, 36.5, 97.5)]),
    ("Australia", [(-44.0, 112.0, -10.0, 154.0)]),
    ("New Zealand & Pacific islands", [(-48.0, 160.0, -5.0, 180.0), (-48.0, -180.0, -5.0, -170.0)]),
    ("Chile & Peru", [(-56.0, -82.0, -2.0, -66.0)]),
    ("Brazil", [(-34.0, -74.0, 5.5, -34.0)]),
    ("Argentina", [(-55.0, -74.0, -21.0, -53.0)]),
    ("Iceland", [(62.5, -25.0, 67.0, -13.0)]),
    ("Turkey", [(35.8, 25.5, 42.2, 45.0)]),
    ("Ukraine & Black Sea", [(43.0, 22.0, 52.5, 41.0)]),
    ("Middle East & Gulf", [(12.0, 34.0, 38.0, 63.5)]),
    ("Southern Europe & Mediterranean", [(34.5, -10.0, 45.0, 28.0)]),
    ("Northern & Central Europe", [(45.0, -11.0, 71.0, 32.0)]),
    ("West Africa", [(-5.0, -18.0, 16.0, 15.0)]),
    ("East Africa & Horn", [(-12.0, 28.0, 18.0, 52.0)]),
]


def find_region(lat, lon):
    for name, boxes in REGIONS:
        for s, w, n, e in boxes:
            if s <= lat <= n and w <= lon <= e:
                return name
    return None


# ---------------------------------------------------------------------------
# PLATE TECTONICS: the specific geological cause of earthquakes and volcanoes, by region
# ---------------------------------------------------------------------------
TECTONICS = {
    "Japan": "Japan sits where four plates meet. The Pacific Plate and the Philippine Sea Plate dive "
             "(subduct) beneath the plates Japan stands on, building stress that is released as earthquakes "
             "and feeding magma to its volcanoes.",
    "Taiwan": "Taiwan is being crushed between the Philippine Sea Plate and the Eurasian Plate. The collision "
              "is still pushing up its mountains, which is why strong quakes (like Hualien 2024) are common.",
    "Philippines": "The islands sit between two subduction zones: the Philippine Sea Plate sinking along the "
                   "Philippine Trench in the east, and the Eurasian side sinking along the Manila and Negros "
                   "trenches in the west. Melting rock from these sinking plates feeds volcanoes such as Kanlaon, "
                   "Mayon and Taal.",
    "Indonesia": "The Indo-Australian Plate is sinking beneath the Sunda Plate along the Sunda (Java) Trench. "
                 "This builds one of the world's longest volcanic chains (well over 100 active volcanoes) and "
                 "caused the 2004 Indian Ocean earthquake and tsunami.",
    "Chile & Peru": "The Nazca Plate is sinking beneath South America by several centimetres a year. This "
                    "subduction produced the strongest earthquake ever recorded (Chile, 1960, magnitude 9.5) and "
                    "feeds the Andes' volcanoes.",
    "Panama & Central America": "The Cocos Plate sinks beneath Central America along the Middle America Trench. "
                                "Panama itself sits on a small 'Panama microplate', squeezed between the Caribbean, "
                                "Cocos, Nazca and South American plates; the Panama Fracture Zone to its south is a "
                                "frequent source of quakes.",
    "Mexico": "The Cocos Plate sinks beneath Mexico along the Middle America Trench (the cause of the 1985 and "
              "2017 Mexico City earthquakes).",
    "US West Coast": "California straddles the San Andreas Fault, where the Pacific Plate slides north-west past "
                     "the North American Plate. Further north, the Juan de Fuca Plate sinks under Oregon and "
                     "Washington (the Cascadia subduction zone).",
    "Alaska & Aleutians": "The Pacific Plate sinks beneath North America along the Aleutian Trench, causing large "
                          "quakes (1964, magnitude 9.2) and a chain of active volcanoes.",
    "Turkey": "The Arabian Plate pushes north, squeezing the Anatolian Plate westwards along the North and East "
              "Anatolian faults (the East Anatolian Fault caused the 2023 earthquake that killed over 50,000 people).",
    "Southern Europe & Mediterranean": "The African Plate is slowly sinking beneath the Eurasian Plate under Greece "
                                       "and southern Italy, which feeds Etna and Vesuvius and causes regular quakes.",
    "Middle East & Gulf": "The Arabian Plate is colliding with the Eurasian Plate, folding up Iran's Zagros "
                          "Mountains and making Iran one of the most earthquake-prone countries.",
    "India & South Asia": "The Indian Plate is ramming into Asia at about 4–5 cm a year, pushing up the Himalayas "
                          "and causing major quakes from Pakistan to Nepal and Myanmar.",
    "Iceland": "Iceland sits on the Mid-Atlantic Ridge, where the North American and Eurasian plates pull apart, "
               "on top of a mantle hotspot. That combination makes eruptions frequent.",
    "New Zealand & Pacific islands": "The Pacific and Australian plates grind past and beneath each other here, "
                                     "producing frequent quakes and volcanoes from New Zealand to Tonga.",
    "Caribbean": "The Caribbean Plate grinds past the North American Plate along its northern edge (the cause of "
                 "the 2010 Haiti earthquake), and the Atlantic sinks beneath the Lesser Antilles' volcanoes.",
}


# ---------------------------------------------------------------------------
# DISASTER IMPACTS by region and type
# ---------------------------------------------------------------------------
IMPACTS = {
    # ---------------- North America ----------------
    ("Florida", "Cyclone"): [
        ("Universal Insurance (Florida)", DOWN, "One of Florida's biggest home insurers: claims come straight out of profits."),
        ("HCI Group (Florida)", DOWN, "Florida-focused home insurer; very exposed to hurricane claims."),
        ("Allstate", DOWN, "Large US home and car insurer with significant Florida/Southeast exposure."),
        ("Progressive", DOWN, "Large car and home insurer; storm damage raises claims."),
        ("Home Depot", UP, "Rebuilding demand: plywood, generators, roofing and repairs."),
        ("Lowe's", UP, "Same rebuilding demand as Home Depot."),
        ("Generac (generators)", UP, "Power cuts drive generator sales before and after storms."),
        ("NextEra Energy (Florida)", MIXED, "Owns Florida Power & Light: repair costs short-term, usually recovered later through rates."),
        ("Orange juice", UP, "Florida is a major US orange grower; wind and flooding destroy fruit and trees."),
        ("Southwest", DOWN, "Southwest has a large Florida network; airports close and flights are cancelled."),
        ("Royal Caribbean (cruises)", DOWN, "Miami and Port Canaveral are major cruise ports; itineraries get cancelled."),
    ],
    ("US Gulf Coast", "Cyclone"): [
        ("Gasoline", UP, "Texas and Louisiana hold roughly half of US refining capacity; refineries shut before storms."),
        ("WTI oil", MIXED, "Offshore Gulf platforms shut in production (bullish), but closed refineries buy less crude (bearish)."),
        ("Valero (refiner)", MIXED, "Big Gulf Coast refiner: outages cut output, but higher fuel margins can offset."),
        ("Cheniere (LNG exports)", DOWN, "Its Sabine Pass and Corpus Christi LNG terminals sit on the Gulf Coast and pause in storms."),
        ("Natural gas (US)", MIXED, "Fewer LNG exports leave more gas at home (bearish), offshore output shut-ins (bullish)."),
        ("Allstate", DOWN, "Home and car insurance claims in Texas and Louisiana."),
        ("Travelers", DOWN, "Commercial and home insurer exposed to Gulf property damage."),
        ("Home Depot", UP, "Rebuilding demand."),
        ("Generac (generators)", UP, "Power outages drive generator demand."),
        ("Corn", MIXED, "Gulf ports export a large share of US grain; delays can briefly back up shipments."),
    ],
    ("US East Coast", "Cyclone"): [
        ("Duke Energy", DOWN, "Major utility in the Carolinas: storm repair costs and outages."),
        ("Travelers", DOWN, "Property and commercial insurance claims."),
        ("Allstate", DOWN, "Home insurance claims."),
        ("Home Depot", UP, "Rebuilding demand."),
        ("Lowe's", UP, "Rebuilding demand."),
        ("Generac (generators)", UP, "Power outages drive generator demand."),
    ],
    ("US West Coast", "Wildfire"): [
        ("PG&E (California)", DOWN, "Its power lines have been blamed for major fires (e.g. Camp Fire 2018); liability fears hit the stock."),
        ("Edison International (California)", DOWN, "Southern California utility; liability risk if its equipment started a fire."),
        ("Allstate", DOWN, "Home insurance losses in California."),
        ("Travelers", DOWN, "Property insurance losses."),
        ("Home Depot", UP, "Rebuilding demand."),
    ],
    ("US West Coast", "Earthquake"): [
        ("Apple", DOWN, "Headquartered in Silicon Valley; a major Bay Area quake would disrupt operations."),
        ("Nvidia", DOWN, "Silicon Valley headquarters and design teams."),
        ("Matson (Pacific containers)", DOWN, "Relies on West Coast ports (Long Beach, Oakland) that could be damaged."),
        ("Travelers", DOWN, "Commercial property claims (most homeowners lack quake cover)."),
        ("PG&E (California)", DOWN, "Gas and power network damage in Northern California."),
    ],
    ("US West Coast", "Drought"): [
        ("PG&E (California)", MIXED, "Less hydro-power and higher wildfire risk."),
        ("Edison International (California)", MIXED, "Higher wildfire risk on its network."),
        ("Deere (farm machinery)", DOWN, "California farmers cut planting and spending in dry years."),
    ],
    ("Canada", "Wildfire"): [
        ("Suncor (Canadian oil sands)", DOWN, "Oil sands sites in Alberta can be evacuated (as in Fort McMurray, 2016)."),
        ("Canadian Natural Resources", DOWN, "Same Alberta oil sands exposure."),
        ("WTI oil", UP, "Lost Canadian supply tightens the North American oil market."),
    ],
    ("Alaska & Aleutians", "Volcano"): [
        ("FedEx", DOWN, "Ash can close Anchorage, the refuelling stop for trans-Pacific cargo flights."),
        ("UPS", DOWN, "Same Anchorage dependence for Asia–America cargo."),
    ],
    # ---------------- Latin America ----------------
    ("Caribbean", "Cyclone"): [
        ("Carnival (cruises)", DOWN, "The Caribbean is the world's biggest cruise market; ports close and trips get rerouted."),
        ("Royal Caribbean (cruises)", DOWN, "Same Caribbean cruise exposure."),
        ("Sugar", UP, "Cuba, the Dominican Republic and Central America grow sugar cane."),
    ],
    ("Mexico", "Cyclone"): [
        ("Mexico fund", DOWN, "Damage to towns, ports and tourism (Cancún, Los Cabos, Acapulco)."),
        ("WTI oil", UP, "Mexico's offshore oil platforms in the Bay of Campeche shut in storms."),
    ],
    ("Mexico", "Earthquake"): [
        ("Mexico fund", DOWN, "Damage to Mexico City, the economic centre."),
        ("General Motors", DOWN, "GM and other carmakers have large plants in Mexico."),
    ],
    ("Panama & Central America", "Drought"): [
        ("Dry bulk shipping rates", UP, "Low water in Gatún Lake forces the Panama Canal to cut daily ship slots (as in 2023), pushing ships onto longer routes."),
        ("Cheniere (LNG exports)", DOWN, "US LNG to Asia uses the canal; restrictions add cost and travel time."),
        ("Soybeans", MIXED, "US Gulf grain exports to Asia get slower and pricier."),
        ("Coffee", UP, "Central America grows high-quality arabica coffee."),
    ],
    ("Panama & Central America", "Earthquake"): [
        ("Dry bulk shipping rates", MIXED, "Any damage to the Panama Canal would force ships onto longer routes."),
        ("Coffee", UP, "Central American coffee farms and roads can be damaged."),
    ],
    ("Chile & Peru", "Earthquake"): [
        ("Copper", UP, "Chile and Peru are the world's #1 and #2 copper producers; mines and ports pause for checks."),
        ("Freeport-McMoRan (copper)", MIXED, "Owns big Peruvian/Chilean mines (output risk) but benefits from higher copper prices."),
        ("SQM (Chilean lithium)", DOWN, "Chilean lithium producer; operations disrupted."),
        ("Chile fund", DOWN, "Damage to the Chilean economy."),
    ],
    ("Chile & Peru", "Volcano"): [
        ("Copper", UP, "Ash and evacuations can disrupt Andean mines."),
        ("Chile fund", DOWN, "Local disruption."),
    ],
    ("Chile & Peru", "Drought"): [
        ("Copper", UP, "Copper mining uses huge amounts of water; shortages cut output."),
        ("SQM (Chilean lithium)", MIXED, "Lithium brine operations in the Atacama depend on scarce water."),
    ],
    ("Brazil", "Drought"): [
        ("Coffee", UP, "Brazil is the world's largest coffee grower; drought shrinks the harvest."),
        ("Sugar", UP, "Brazil is the largest sugar exporter."),
        ("Orange juice", UP, "Brazil dominates world orange juice exports."),
        ("Soybeans", UP, "Brazil is the top soybean exporter."),
        ("Brazil fund", DOWN, "Brazil gets most of its electricity from hydro dams; drought raises power costs."),
        ("Vale (iron ore)", MIXED, "Low rivers can slow shipments from inland mines."),
    ],
    ("Brazil", "Flood"): [
        ("Soybeans", UP, "Floods (e.g. Rio Grande do Sul, 2024) destroy crops and block roads to ports."),
        ("Brazil fund", DOWN, "Economic damage."),
        ("Vale (iron ore)", MIXED, "Heavy rain can disrupt mining and dam safety."),
    ],
    ("Argentina", "Drought"): [
        ("Soybeans", UP, "Argentina is the largest exporter of soybean meal and oil."),
        ("Corn", UP, "Argentina is a top-3 corn exporter."),
        ("Wheat", UP, "Major wheat exporter."),
        ("Bunge", MIXED, "Big South American crop trader: less volume, but higher prices."),
    ],
    # ---------------- Asia ----------------
    ("Taiwan", "Earthquake"): [
        ("TSMC", DOWN, "Makes about 90% of the world's most advanced chips; fabs halt to inspect machines and lose wafers."),
        ("Taiwan (TAIEX)", DOWN, "TSMC alone is a huge share of Taiwan's stock market."),
        ("Nvidia", DOWN, "Nearly all its GPUs are made by TSMC."),
        ("Apple", DOWN, "iPhone and Mac chips come from TSMC."),
        ("AMD", DOWN, "Relies on TSMC for its processors."),
        ("Micron", UP, "Memory rival: when the 1999 Chi-Chi quake hit Taiwan's chip plants, memory prices jumped."),
    ],
    ("Taiwan", "Cyclone"): [
        ("TSMC", MIXED, "Fabs are built to cope, but power cuts and staff absence can slow output."),
        ("Taiwan (TAIEX)", DOWN, "Typhoon days close offices and the stock exchange."),
        ("Chip stocks fund", MIXED, "Any hit to TSMC ripples through the chip industry."),
    ],
    ("Taiwan", "Drought"): [
        ("TSMC", DOWN, "Chip-making uses huge volumes of ultra-pure water; in 2021 Taiwan trucked in water to keep fabs running."),
        ("Chip stocks fund", DOWN, "Global chip supply depends on Taiwan."),
    ],
    ("Japan", "Earthquake"): [
        ("Japan (Nikkei)", DOWN, "Damage to factories, power plants and supply chains."),
        ("Japanese yen (per $)", DOWN, "The yen often STRENGTHENS after big Japanese quakes (fewer yen per dollar) as money returns home, as in 2011."),
        ("Toyota", DOWN, "Japanese factories halt; 2011 shut its production for weeks."),
        ("Honda", DOWN, "Same Japanese factory exposure."),
        ("Micron", UP, "Japanese chip and materials plants (e.g. Kioxia flash memory) can go offline, lifting memory prices."),
    ],
    ("Japan", "Cyclone"): [
        ("Japan (Nikkei)", DOWN, "Factories, ports and transport close."),
        ("Toyota", DOWN, "Typhoons regularly halt Japanese car plants for a day or two."),
        ("Honda", DOWN, "Same factory disruption."),
    ],
    ("Japan", "Volcano"): [
        ("Japan (Nikkei)", MIXED, "Usually local, unless ash reaches Tokyo or major airports."),
    ],
    ("South Korea", "Cyclone"): [
        ("South Korea (KOSPI)", DOWN, "Ports, shipyards and factories close."),
        ("Micron", UP, "Rival memory makers Samsung and SK hynix are Korean; their disruption helps Micron."),
    ],
    ("China", "Cyclone"): [
        ("ZIM (containers)", UP, "Closing Shanghai, Ningbo or Shenzhen ports backs up container ships and lifts freight rates."),
        ("Danaos (container ships)", UP, "Owns container ships leased out; tight capacity helps."),
        ("Hong Kong (Hang Seng)", DOWN, "Typhoon signals close Hong Kong's stock exchange and businesses."),
        ("Apple", DOWN, "Many of its suppliers are in southern China."),
    ],
    ("China", "Flood"): [
        ("Copper", MIXED, "China uses about half the world's copper; floods slow construction (bearish) but can hit mines (bullish)."),
        ("BHP", DOWN, "Floods slow Chinese steel and construction, cutting iron ore demand."),
        ("Rio Tinto", DOWN, "Same iron ore demand risk."),
        ("Corn", UP, "Can damage crops in China's farming regions."),
    ],
    ("China", "Drought"): [
        ("Copper", MIXED, "Drought cuts hydropower in Sichuan/Yunnan, forcing factories and smelters to close (2022)."),
        ("Albemarle (lithium)", UP, "Power cuts in Sichuan hit lithium processing."),
        ("Corn", UP, "Lower Chinese harvests mean more imports."),
    ],
    ("China", "Earthquake"): [
        ("Hong Kong (Hang Seng)", DOWN, "Economic damage in China."),
        ("Copper", MIXED, "Can hit mines in western China."),
    ],
    ("Philippines", "Cyclone"): [
        ("Philippines fund", DOWN, "Typhoons damage homes, farms and infrastructure; the Philippines is hit by about 20 a year."),
        ("Texas Instruments", MIXED, "Has chip assembly and test plants in the Philippines."),
        ("Analog Devices", MIXED, "Runs a big chip test/assembly plant near Manila."),
    ],
    ("Philippines", "Volcano"): [
        ("Philippines fund", DOWN, "Evacuations and ash disrupt local towns, farms and flights (mostly a LOCAL economic effect)."),
        ("Analog Devices", MIXED, "Only affected if ash reaches the Manila area, where it has chip plants; Kanlaon (on Negros) is far from it."),
        ("Sugar", UP, "Negros island, home to Kanlaon, grows over half of the Philippines' sugar cane."),
    ],
    ("Philippines", "Earthquake"): [
        ("Philippines fund", DOWN, "Damage to the local economy."),
        ("Texas Instruments", MIXED, "Chip test/assembly plants in the Philippines."),
    ],
    ("Western Pacific islands (Guam & Micronesia)", "Cyclone"): [
        ("Defence stocks fund", MIXED, "Guam hosts major US air and naval bases (Andersen Air Force Base, Naval Base Guam); "
                                       "storm damage means repair work but also disrupted operations."),
        ("Japan (Nikkei)", MIXED, "Typhoons forming here often track north-west toward Japan, Taiwan or the "
                                  "Philippines; the market impact depends on where it goes next."),
        ("Taiwan (TAIEX)", MIXED, "Same: watch whether the storm's track turns toward Taiwan."),
    ],
    ("Indonesia", "Volcano"): [
        ("Indonesia fund", DOWN, "Evacuations and closed airports (Bali eruptions strand tourists)."),
        ("Airlines fund", DOWN, "Volcanic ash can ground flights across a wide area."),
        ("Vale (iron ore)", MIXED, "Vale has nickel operations in Indonesia (battery metals)."),
    ],
    ("Indonesia", "Earthquake"): [
        ("Indonesia fund", DOWN, "Economic damage and tsunami risk."),
        ("Vale (iron ore)", MIXED, "Nickel operations on Sulawesi."),
    ],
    ("Indonesia", "Flood"): [
        ("Indonesia fund", DOWN, "Jakarta floods disrupt the capital's economy."),
    ],
    ("Southeast Asia mainland", "Flood"): [
        ("Western Digital (hard drives)", MIXED, "2011 Thailand floods drowned hard-drive factories and doubled drive prices; rivals with dry plants profited."),
        ("Seagate (hard drives)", MIXED, "Same hard-drive supply chain in Thailand."),
        ("Toyota", DOWN, "Big car plants in Thailand (the 'Detroit of Asia')."),
        ("Honda", DOWN, "Honda's Thai factory was flooded in 2011."),
    ],
    ("Southeast Asia mainland", "Drought"): [
        ("Coffee", UP, "Vietnam is the world's largest robusta coffee producer."),
        ("Sugar", UP, "Thailand is a top-3 sugar exporter."),
    ],
    ("Southeast Asia mainland", "Cyclone"): [
        ("Coffee", UP, "Vietnam's coffee-growing highlands can be hit."),
        ("Western Digital (hard drives)", MIXED, "Thai and Malaysian drive factories."),
    ],
    ("India & South Asia", "Cyclone"): [
        ("India (Nifty 50)", DOWN, "Ports, refineries (Gujarat) and coastal towns close."),
        ("Sugar", UP, "India is the world's #2 sugar producer; storms damage cane."),
    ],
    ("India & South Asia", "Flood"): [
        ("India (Nifty 50)", DOWN, "Disrupts transport and farms."),
        ("Sugar", UP, "Damages the cane crop."),
        ("Wheat", MIXED, "India is a huge wheat grower; floods at planting or harvest time matter most."),
    ],
    ("India & South Asia", "Drought"): [
        ("Sugar", UP, "A weak monsoon cuts India's cane crop and can trigger sugar export bans."),
        ("Wheat", UP, "India may restrict wheat exports (it did in 2022)."),
        ("India (Nifty 50)", DOWN, "Farming employs a large share of Indians; weak harvests hurt spending."),
        ("Nutrien (fertiliser)", MIXED, "Less planting, but governments often boost fertiliser support."),
    ],
    ("India & South Asia", "Earthquake"): [
        ("India (Nifty 50)", DOWN, "Damage in northern India/Nepal."),
    ],
    ("Australia", "Cyclone"): [
        ("BHP", DOWN, "Cyclones close Port Hedland in the Pilbara, the world's biggest iron ore export port."),
        ("Rio Tinto", DOWN, "Same Pilbara iron ore exposure."),
        ("Vale (iron ore)", UP, "Brazilian rival gains when Australian supply is cut."),
    ],
    ("Australia", "Drought"): [
        ("Wheat", UP, "Australia is a top-5 wheat exporter."),
    ],
    ("Australia", "Wildfire"): [
        ("Wheat", MIXED, "Fires usually hit forests more than wheat belts."),
    ],
    # ---------------- Europe & Middle East ----------------
    ("Iceland", "Volcano"): [
        ("Airlines fund", DOWN, "In 2010 Eyjafjallajökull's ash closed most European airspace for about a week."),
        ("Delta", DOWN, "Transatlantic flights cancelled or rerouted."),
        ("United", DOWN, "Transatlantic flights cancelled or rerouted."),
    ],
    ("Turkey", "Earthquake"): [
        ("Turkey fund", DOWN, "Damage to the economy (2023's quake cost over $100 billion)."),
        ("Dry bulk shipping rates", MIXED, "Could disrupt Bosporus shipping and Turkish ports."),
        ("Wheat", MIXED, "Turkey is a large wheat importer and flour exporter."),
    ],
    ("Southern Europe & Mediterranean", "Wildfire"): [
        ("Euro Stoxx 50", MIXED, "Mostly local damage to tourism and farms (Greece, Spain, Portugal)."),
        ("Chubb", DOWN, "Global property insurer with European exposure."),
    ],
    ("Southern Europe & Mediterranean", "Drought"): [
        ("Wheat", UP, "Spain, Italy and southern France grow wheat."),
        ("European natural gas (TTF)", UP, "Less hydropower means more gas burned for electricity."),
    ],
    ("Southern Europe & Mediterranean", "Earthquake"): [
        ("Euro Stoxx 50", MIXED, "Usually a local economic effect (Italy, Greece)."),
    ],
    ("Northern & Central Europe", "Drought"): [
        ("European natural gas (TTF)", UP, "Low rivers cut hydropower and limit cooling water for French nuclear plants, so more gas is burned."),
        ("Wheat", UP, "France and Germany are among the world's largest wheat exporters."),
        ("Euro Stoxx 50", DOWN, "Low Rhine water (as in 2018 and 2022) stops barges carrying chemicals, coal and fuel to German industry."),
        ("Volkswagen", DOWN, "German industry relies on Rhine shipping for parts and fuel."),
    ],
    ("Northern & Central Europe", "Flood"): [
        ("Euro Stoxx 50", DOWN, "Floods (Germany 2021, Central Europe 2024) damage towns and factories."),
        ("Chubb", DOWN, "Insurance claims."),
        ("Volkswagen", DOWN, "German supplier factories can be flooded."),
    ],
    ("Northern & Central Europe", "Wildfire"): [
        ("Euro Stoxx 50", MIXED, "Usually local."),
    ],
    ("Middle East & Gulf", "Earthquake"): [
        ("Brent oil", MIXED, "Only matters if it hits oil facilities."),
    ],
    ("Middle East & Gulf", "Flood"): [
        ("Brent oil", MIXED, "Rare desert floods (Dubai 2024) disrupt airports more than oil."),
        ("Airlines fund", DOWN, "Dubai and Doha are huge transit hubs."),
    ],
    # ---------------- Africa ----------------
    ("West Africa", "Drought"): [
        ("Cocoa", UP, "Ivory Coast and Ghana grow about 60% of the world's cocoa; dry weather (2024) sent prices to records."),
        ("Coffee", UP, "Ivory Coast and Uganda grow robusta."),
    ],
    ("West Africa", "Flood"): [
        ("Cocoa", UP, "Too much rain spreads black pod disease in cocoa trees."),
    ],
    ("East Africa & Horn", "Drought"): [
        ("Coffee", UP, "Ethiopia (arabica) and Uganda (robusta) are major growers."),
        ("Wheat", MIXED, "The region imports wheat; drought increases demand for imports."),
    ],
    ("East Africa & Horn", "Flood"): [
        ("Coffee", MIXED, "Floods can damage coffee areas and roads."),
    ],
}

# What applies when no region-specific research exists (shown clearly as "general").
GENERAL_IMPACTS = {
    "Cyclone": [("Travelers", DOWN, "Global property insurers pay storm claims."),
                ("Home Depot", UP, "Rebuilding demand (if the storm hits the US).")],
    "Flood": [("Chubb", DOWN, "Global property insurer.")],
    "Drought": [("Wheat", UP, "Droughts in farm regions cut grain harvests."),
                ("Corn", UP, "Same harvest risk.")],
    "Earthquake": [("Gold", UP, "Big disasters push some investors into safe havens.")],
    "Volcano": [("Airlines fund", DOWN, "Ash clouds can ground flights.")],
    "Wildfire": [("Chubb", DOWN, "Property insurance losses.")],
}


def disaster_impacts(disaster):
    """Returns (region name, list of impacts, is_region_specific)."""
    region = find_region(disaster["lat"], disaster["lon"])
    specific = IMPACTS.get((region, disaster["type"]))
    if specific:
        return region, specific, True
    return region, GENERAL_IMPACTS.get(disaster["type"], []), False


# ---------------------------------------------------------------------------
# SHIPPING CHOKEPOINTS: who wins and who loses when traffic drops
# ---------------------------------------------------------------------------
CHOKEPOINT_IMPACTS = {
    "Strait of Hormuz": [
        ("Brent oil", UP, "About a fifth of world oil passes here; fewer tankers means less supply reaching buyers."),
        ("WTI oil", UP, "US oil rises with world prices, and US exports become more valuable."),
        ("Frontline (oil tankers)", UP, "Tanker rental rates spike when routes are dangerous and ships must sail further."),
        ("Scorpio Tankers", UP, "Fuel-product tankers earn more when refined fuel has to come from further away."),
        ("International Seaways", UP, "Same tanker-rate boost."),
        ("Cheniere (LNG exports)", UP, "Qatar ships ~20% of world LNG through Hormuz; buyers turn to US LNG instead."),
        ("European natural gas (TTF)", UP, "Europe and Asia compete for replacement gas."),
        ("Airlines fund", DOWN, "Jet fuel is airlines' biggest cost; it rises with oil."),
        ("Saudi Arabia fund", MIXED, "Higher prices, but Saudi exports through Hormuz are at risk (it has a pipeline to the Red Sea)."),
        ("Defence stocks fund", UP, "Military escorts and conflict raise defence spending."),
        ("Gold", UP, "Safe-haven buying during Gulf crises."),
        ("Japan (Nikkei)", DOWN, "Japan imports nearly all its oil, most of it through Hormuz."),
        ("India (Nifty 50)", DOWN, "India imports most of its oil, much of it from the Gulf."),
    ],
    "Bab el-Mandeb Strait": [
        ("ZIM (containers)", UP, "Ships sailing round Africa take ~2 weeks longer, soaking up capacity and lifting container rates."),
        ("Danaos (container ships)", UP, "Tight ship capacity lets owners charge more."),
        ("Brent oil", UP, "Middle East oil to Europe takes longer and costs more to insure."),
        ("Frontline (oil tankers)", UP, "Longer tanker voyages raise rates."),
        ("Euro Stoxx 50", DOWN, "European importers face delays and higher shipping costs."),
        ("Expeditors (freight)", MIXED, "Freight forwarders earn more per shipment but face customer delays."),
    ],
    "Suez Canal": [
        ("ZIM (containers)", UP, "Avoiding Suez absorbs ship capacity and lifts container rates."),
        ("Matson (Pacific containers)", MIXED, "Mostly Pacific routes; benefits indirectly from tighter global capacity."),
        ("Brent oil", UP, "Oil and fuel to Europe take the long route."),
        ("Euro Stoxx 50", DOWN, "Europe relies on the Asia–Europe route through Suez."),
        ("Volkswagen", DOWN, "Car parts from Asia arrive late (2024 Red Sea crisis paused some European car plants)."),
    ],
    "Cape of Good Hope": [
        ("ZIM (containers)", MIXED, "Busier Cape = ships avoiding the Red Sea = higher rates; quieter Cape = Red Sea reopening."),
        ("Dry bulk shipping rates", MIXED, "Longer routes raise rates."),
        ("Brent oil", MIXED, "Indicates how much oil is taking the long route."),
    ],
    "Panama Canal": [
        ("Cheniere (LNG exports)", DOWN, "US LNG to Asia goes through the canal; restrictions add ~10–20 days via other routes."),
        ("Soybeans", MIXED, "US Gulf grain exports to Asia get slower and pricier, helping Brazilian exporters."),
        ("Dry bulk shipping rates", UP, "Longer routes absorb ship capacity."),
        ("Corn", MIXED, "Same Gulf grain-export issue."),
    ],
    "Malacca Strait": [
        ("Brent oil", UP, "Main route for oil to China, Japan and Korea."),
        ("Hong Kong (Hang Seng)", DOWN, "Chinese trade depends on it."),
        ("South Korea (KOSPI)", DOWN, "Korean energy imports and exports pass through."),
        ("Frontline (oil tankers)", UP, "Detours via the Lombok/Sunda straits lengthen tanker voyages."),
    ],
    "Taiwan Strait": [
        ("TSMC", DOWN, "Any blockade or military pressure threatens Taiwan's chip exports."),
        ("Taiwan (TAIEX)", DOWN, "Direct risk to Taiwan's economy."),
        ("Nvidia", DOWN, "Relies on TSMC."),
        ("Apple", DOWN, "Relies on TSMC and Chinese assembly."),
        ("Defence stocks fund", UP, "Rising tension lifts defence spending."),
        ("Gold", UP, "Safe-haven buying."),
    ],
    "Bosporus Strait": [
        ("Wheat", UP, "Ukrainian and Russian grain exports leave the Black Sea through here."),
        ("Corn", UP, "Ukraine is a top-5 corn exporter."),
        ("Brent oil", UP, "Russian and Kazakh crude (CPC pipeline) is shipped out this way."),
        ("Turkey fund", MIXED, "Turkey controls the strait; trade disruption hurts, but transit role grows."),
    ],
    "Gibraltar Strait": [
        ("Euro Stoxx 50", DOWN, "Mediterranean trade and Asia–Europe ships pass here."),
    ],
    "Dover Strait": [
        ("Euro Stoxx 50", DOWN, "Northern Europe's ports (Rotterdam, Antwerp, Hamburg) depend on it."),
    ],
}

# ---------------------------------------------------------------------------
# CONFLICT ZONES: who wins and who loses when fighting escalates
# ---------------------------------------------------------------------------
CONFLICT_IMPACTS = {
    "Russia–Ukraine war": [
        ("Wheat", UP, "Ukraine and Russia together export roughly a quarter of the world's wheat."),
        ("Corn", UP, "Ukraine is a top-5 corn exporter."),
        ("European natural gas (TTF)", UP, "Strikes on gas infrastructure and lost Russian supply keep European gas tight."),
        ("Rheinmetall", UP, "Germany's biggest arms maker; huge orders for artillery shells and vehicles."),
        ("BAE Systems", UP, "European defence demand."),
        ("Lockheed Martin", UP, "Missiles and air defence for Ukraine and NATO restocking."),
        ("Nutrien (fertiliser)", UP, "Russia and Belarus are huge potash and fertiliser exporters; disruption helps rivals."),
        ("Mosaic (fertiliser)", UP, "Same fertiliser effect."),
        ("Euro Stoxx 50", DOWN, "War risk and energy costs weigh on European companies."),
    ],
    "Black Sea shipping attacks": [
        ("Wheat", UP, "Attacks threaten grain ships leaving Odesa and Russian ports."),
        ("Corn", UP, "Same grain-shipping risk."),
        ("Brent oil", UP, "Russian and Kazakh oil exports cross the Black Sea."),
        ("Frontline (oil tankers)", UP, "War-risk insurance and fewer willing ships raise tanker rates."),
    ],
    "Iran & the Gulf": [
        ("Brent oil", UP, "Risk to Gulf production and the Strait of Hormuz."),
        ("WTI oil", UP, "US oil rises with world prices."),
        ("Frontline (oil tankers)", UP, "Tanker rates spike on danger and longer routes."),
        ("Cheniere (LNG exports)", UP, "Qatari LNG at risk; US LNG becomes the alternative."),
        ("Lockheed Martin", UP, "Missile-defence demand (Patriot/THAAD interceptors)."),
        ("RTX (Raytheon)", UP, "Makes interceptor missiles used against drones and missiles."),
        ("Northrop Grumman", UP, "Defence spending rises."),
        ("Gold", UP, "Safe-haven buying."),
        ("Airlines fund", DOWN, "Higher jet fuel costs and closed airspace over Iran and Iraq."),
        ("Israel fund", DOWN, "Direct conflict risk."),
        ("Saudi Arabia fund", MIXED, "Higher oil prices, but facilities are within range of attacks (2019 Abqaiq strike)."),
    ],
    "Israel, Gaza & Lebanon": [
        ("Israel fund", DOWN, "Direct economic cost: reservists called up, tourism and investment fall."),
        ("Lockheed Martin", UP, "Supplies F-35 jets and munitions to Israel."),
        ("RTX (Raytheon)", UP, "Co-produces Iron Dome interceptors."),
        ("Brent oil", UP, "Risk of wider war involving Iran."),
        ("Gold", UP, "Safe-haven buying."),
    ],
    "Red Sea & Yemen (Houthis)": [
        ("ZIM (containers)", UP, "Attacks force ships round Africa, lifting container rates."),
        ("Danaos (container ships)", UP, "Ship owners benefit from tight capacity."),
        ("Brent oil", UP, "Tankers avoid the Red Sea."),
        ("Euro Stoxx 50", DOWN, "European importers face delays and higher costs."),
        ("RTX (Raytheon)", UP, "Navies fire costly interceptor missiles at Houthi drones."),
    ],
    "Sudan civil war": [
        ("Gold", MIXED, "Sudan is a significant gold producer; fighting disrupts output and smuggling routes."),
        ("Wheat", MIXED, "Famine increases aid demand for imported grain."),
    ],
    "Taiwan Strait tensions": [
        ("TSMC", DOWN, "Military pressure threatens the world's most important chip maker."),
        ("Taiwan (TAIEX)", DOWN, "Direct risk to Taiwan's economy."),
        ("Nvidia", DOWN, "Depends on TSMC for nearly all its chips."),
        ("Apple", DOWN, "Depends on TSMC and Chinese assembly."),
        ("Intel", UP, "US-based chip factories become more valuable as an alternative."),
        ("Lockheed Martin", UP, "Arms sales to Taiwan and Pacific defence spending."),
        ("Gold", UP, "Safe-haven buying."),
    ],
    "South China Sea": [
        ("Philippines fund", DOWN, "Clashes with Chinese vessels raise risk for the Philippines."),
        ("Dry bulk shipping rates", MIXED, "A huge share of Asian trade crosses this sea."),
        ("Defence stocks fund", UP, "Rising regional defence budgets."),
    ],
    "Korean Peninsula": [
        ("South Korea (KOSPI)", DOWN, "Korean stocks dip on North Korean escalation (the 'Korea discount')."),
        ("Micron", UP, "Any threat to Samsung or SK hynix helps the US memory maker."),
        ("Lockheed Martin", UP, "Missile-defence demand in Korea and Japan."),
        ("Japanese yen (per $)", DOWN, "The yen is a safe haven: it often strengthens (fewer yen per dollar) on regional scares."),
    ],
    "India–Pakistan (Kashmir)": [
        ("India (Nifty 50)", DOWN, "War risk hits Indian stocks."),
        ("Gold", UP, "Safe-haven buying; India is also a huge gold buyer."),
        ("Defence stocks fund", UP, "Both countries buy arms."),
    ],
    "Myanmar civil war": [
        ("Gold", MIXED, "Limited global market effect; regional instability."),
        ("MP Materials (rare earths)", UP, "Myanmar mines a large share of heavy rare earths used in magnets; fighting disrupts supply to China."),
    ],
    "Eastern DR Congo": [
        ("Albemarle (lithium)", MIXED, "Battery-metal supply chains are watched closely."),
        ("Freeport-McMoRan (copper)", MIXED, "Congo is a major copper and cobalt producer (mines are mostly in the south, away from the fighting)."),
        ("Copper", UP, "Any spread of fighting toward mining regions threatens supply."),
    ],
    "Sahel insurgencies": [
        ("Gold", UP, "Mali, Burkina Faso and Niger mine gold; attacks and coups disrupt mines."),
        ("Newmont (gold)", MIXED, "Western miners face nationalisation and security risks in the region."),
    ],
    "Venezuela & the Caribbean": [
        ("WTI oil", MIXED, "Venezuela has the world's largest oil reserves; sanctions or conflict change supply."),
        ("Chevron", MIXED, "The main US oil company with operations in Venezuela."),
        ("Valero (refiner)", MIXED, "US Gulf refiners are built to process heavy Venezuelan-type crude."),
    ],
}

# ---------------------------------------------------------------------------
# AIR CARGO HUBS
# ---------------------------------------------------------------------------
HUB_IMPACTS = {
    "Memphis (MEM)": [("FedEx", DOWN, "Its global SuperHub; any shutdown delays millions of overnight parcels.")],
    "Louisville (SDF)": [("UPS", DOWN, "UPS Worldport sorts most of its US air parcels.")],
    "Anchorage (ANC)": [("FedEx", DOWN, "Trans-Pacific cargo jets refuel here."), ("UPS", DOWN, "Same Asia–America route.")],
    "Hong Kong (HKG)": [("Hong Kong (Hang Seng)", DOWN, "Air cargo is a key part of Hong Kong's economy."),
                        ("Apple", DOWN, "Electronics from southern China fly out via Hong Kong.")],
    "Shanghai Pudong (PVG)": [("Tesla", DOWN, "Tesla's Shanghai Gigafactory relies on the region's logistics."),
                              ("Hong Kong (Hang Seng)", DOWN, "Chinese trade disruption.")],
    "Taipei Taoyuan (TPE)": [("TSMC", DOWN, "Finished chips are flown out from Taiwan."),
                             ("Nvidia", DOWN, "GPUs made by TSMC ship by air.")],
    "Incheon (ICN)": [("South Korea (KOSPI)", DOWN, "Memory chips and phones ship by air.")],
    "Tokyo Narita (NRT)": [("Japan (Nikkei)", DOWN, "Japanese exports of high-value parts.")],
    "Singapore (SIN)": [("Chip stocks fund", DOWN, "Singapore is a big chip-equipment and testing hub.")],
    "Dubai (DXB)": [("Airlines fund", DOWN, "One of the world's busiest transit hubs.")],
    "Doha (DOH)": [("Airlines fund", DOWN, "Qatar Airways is one of the biggest cargo carriers.")],
    "Istanbul (IST)": [("Turkey fund", DOWN, "Turkish Cargo is a major Europe–Asia carrier.")],
    "Frankfurt (FRA)": [("Euro Stoxx 50", DOWN, "Europe's main cargo gateway (pharma, machinery).")],
    "Leipzig (LEJ)": [("Euro Stoxx 50", DOWN, "DHL's European express hub.")],
    "Chicago O'Hare (ORD)": [("FedEx", DOWN, "Midwest cargo gateway."), ("UPS", DOWN, "Midwest cargo gateway.")],
    "Los Angeles (LAX)": [("FedEx", DOWN, "West Coast gateway for Asian freight.")],
    "Miami (MIA)": [("Airlines fund", DOWN, "Latin America cargo gateway (flowers, fruit, phones).")],
}


def check_direction(expected, move):
    """Did the market move the way the research expects? Returns match, opposite or a dot (no call)."""
    if move is None or expected == MIXED or abs(move) < 1:
        return "·"
    if (expected == UP and move > 0) or (expected == DOWN and move < 0):
        return "match"
    return "opposite"
