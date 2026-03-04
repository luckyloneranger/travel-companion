"""Regional transport configuration for journey planning.

Contains transport profiles for different regions worldwide, including
popular transport modes, notes, and booking tips. Used by the journey
planner to steer the LLM toward region-appropriate transport choices.
"""

REGIONAL_TRANSPORT_PROFILES: dict[str, dict] = {
    # Southeast Asia
    "vietnam": {
        "popular": ["bus", "train", "flight", "ferry"],
        "notes": "Sleeper buses are very popular for long distances (8-12h overnight). Limited train network (Hanoi-HCMC main line). Domestic flights cheap. Ferries and cruise boats for Ha Long Bay and coastal/island destinations (Cat Ba, Phu Quoc).",
        "tips": "Futa, The Sinh Tourist for buses. Vietnam Railways for trains. VietJet, Bamboo for budget flights. Ha Long Bay cruise operators for overnight bay experiences.",
    },
    "thailand": {
        "popular": ["bus", "train", "flight"],
        "notes": "Excellent overnight buses and trains. BTS/MRT in Bangkok. Budget flights via AirAsia, Nok Air. Train scenic but slow.",
        "tips": "12go.asia for bookings. VIP buses are comfortable. Southern beaches often require bus+ferry.",
    },
    "indonesia": {
        "popular": ["flight", "ferry", "bus"],
        "notes": "Island hopping requires flights or ferries. Road travel limited except Java/Sumatra. Many budget airlines.",
        "tips": "Lion Air, Garuda for flights. Pelni ferries for adventure. Java has good train network.",
    },
    "malaysia": {
        "popular": ["bus", "train", "flight"],
        "notes": "Good bus network. KTM trains connect peninsular cities. Flights for Borneo. KLIA Express for airport.",
        "tips": "AirAsia hub. ETS trains for KL-Penang. Buses comfortable and affordable.",
    },
    "cambodia": {
        "popular": ["bus", "flight"],
        "notes": "Buses are the main transport. Road quality improving. Flights Phnom Penh-Siem Reap common.",
        "tips": "Giant Ibis, Mekong Express for premium buses. Boat Phnom Penh-Siem Reap scenic but slow.",
    },
    # South Asia
    "india": {
        "popular": ["train", "flight", "bus"],
        "notes": "Trains are king - extensive network, Shatabdi/Rajdhani for speed. Flights for >6 hour journeys. Volvo buses for shorter routes.",
        "tips": "IRCTC for trains (book 30+ days ahead). Redbus for buses. IndiGo, Vistara for flights.",
    },
    "india_south": {
        "popular": ["train", "bus", "flight"],
        "notes": "Good train connectivity. KSRTC, TNSTC buses reliable and frequent. Hill stations often bus-only.",
        "tips": "Shatabdi trains excellent. Volvo sleepers overnight. Flights for Bangalore-Chennai-Hyderabad triangle.",
    },
    "india_north": {
        "popular": ["train", "flight", "drive"],
        "notes": "Golden Triangle (Delhi-Agra-Jaipur) best by train/drive. Himalayan regions require driving. Varanasi-Lucknow has good trains.",
        "tips": "Gatimaan Express to Agra. Hire car+driver for Rajasthan flexibility.",
    },
    "sri_lanka": {
        "popular": ["train", "bus", "drive"],
        "notes": "Scenic train journeys (Kandy-Ella famous). Good bus network. Car+driver popular for flexibility.",
        "tips": "Train Colombo-Kandy-Ella is spectacular. Buses frequent but slow. Hiring driver very affordable.",
    },
    # East Asia
    "japan": {
        "popular": ["train", "bus", "flight"],
        "notes": "Shinkansen (bullet trains) are world-class. JR Pass economical for multi-city. Highway buses budget-friendly.",
        "tips": "JR Pass for 7/14/21 days. Willer Express for overnight buses. Domestic flights for Okinawa, Hokkaido.",
    },
    "china": {
        "popular": ["train", "flight", "bus"],
        "notes": "High-speed rail network extensive and excellent. Flights for distant regions. Buses for rural/mountain areas.",
        "tips": "G/D trains high-speed. Get seats via Trip.com. Flights cheap domestically.",
    },
    "south_korea": {
        "popular": ["train", "bus"],
        "notes": "KTX high-speed trains excellent. Express buses comfortable and frequent. Country is compact.",
        "tips": "Korail pass available. T-money card works on buses too. Most trips <3 hours.",
    },
    "taiwan": {
        "popular": ["train", "bus"],
        "notes": "THSR high-speed rail along west coast. TRA trains island-wide. Excellent intercity buses.",
        "tips": "THSR early bird discounts. Kuo-Kuang buses affordable. EasyCard for local transit.",
    },
    # Europe
    "europe_west": {
        "popular": ["train", "flight", "bus"],
        "notes": "Excellent high-speed trains (TGV, Eurostar, ICE). Budget flights Ryanair/EasyJet. Flixbus budget option.",
        "tips": "Eurail Pass for multi-country. Book TGV/Eurostar early. Flixbus for tight budgets.",
    },
    "europe_east": {
        "popular": ["bus", "train", "flight"],
        "notes": "Trains less reliable than Western Europe. Excellent bus networks (FlixBus, RegioJet). Budget flights plentiful.",
        "tips": "RegioJet for comfort. Trains scenic but slow. Wizz Air, Ryanair for flights.",
    },
    "uk_ireland": {
        "popular": ["train", "bus", "drive"],
        "notes": "Trains expensive but convenient. National Express/Megabus budget. Driving easy (left-hand remember!).",
        "tips": "Book trains in advance for savings. Megabus from 1 GBP. Rent cars outside London.",
    },
    "scandinavia": {
        "popular": ["flight", "train", "ferry"],
        "notes": "Distances large - flights often practical. Excellent train networks (Sweden, Norway). Ferries between countries.",
        "tips": "Norwegian, SAS for flights. Inter-rail popular. Hurtigruten for coastal Norway experience.",
    },
    # Americas
    "usa_east": {
        "popular": ["flight", "train", "drive"],
        "notes": "Amtrak along Northeast Corridor good. Flights for longer distances. Driving common but consider traffic.",
        "tips": "Acela for NYC-DC-Boston. Rent cars for flexibility. Megabus/Greyhound budget option.",
    },
    "usa_west": {
        "popular": ["flight", "drive"],
        "notes": "Distances huge - flights or driving. Train options limited. Road trips iconic (Pacific Coast Highway!).",
        "tips": "Southwest, Alaska Airlines for flights. Rent cars - essential for flexibility. Amtrak Coast Starlight scenic.",
    },
    "mexico": {
        "popular": ["bus", "flight"],
        "notes": "Excellent luxury bus network (ADO, ETN, Primera Plus). Affordable flights. No passenger trains.",
        "tips": "ADO for Yucatan. ETN for comfort. Volaris, VivaAerobus for cheap flights. Book buses at terminal.",
    },
    "brazil": {
        "popular": ["flight", "bus"],
        "notes": "Huge country - flights essential for long distances. Comfortable long-distance buses. No intercity rail.",
        "tips": "GOL, LATAM, Azul for flights. Leito buses for overnight comfort.",
    },
    "argentina": {
        "popular": ["flight", "bus"],
        "notes": "Long distances require flights. Excellent cama/semi-cama buses. Limited train outside Buenos Aires.",
        "tips": "Aerolineas Argentinas, LATAM for flights. Andesmar, Via Bariloche for quality buses.",
    },
    "peru": {
        "popular": ["bus", "flight"],
        "notes": "Cruz del Sur excellent buses. Flights for Lima-Cusco (or acclimatize slowly). Train to Machu Picchu.",
        "tips": "Cruz del Sur VIP worth it. LATAM for domestic flights. PeruRail/IncaRail for Machu Picchu.",
    },
    "colombia": {
        "popular": ["flight", "bus"],
        "notes": "Mountains make driving slow. Flights between major cities fast and cheap. Buses for shorter routes.",
        "tips": "Avianca, Viva Air for flights. Bolivariano for quality buses.",
    },
    # Middle East
    "turkey": {
        "popular": ["flight", "bus", "train"],
        "notes": "Domestic flights cheap and efficient. Bus network excellent. Train improving but limited.",
        "tips": "Pegasus, Turkish for flights. Metro, Kamil Koc for buses. High-speed train Ankara-Istanbul.",
    },
    "morocco": {
        "popular": ["train", "bus", "drive"],
        "notes": "ONCF trains connect major cities. CTM/Supratours buses excellent. Grand taxis for shorter routes.",
        "tips": "Train Casablanca-Marrakech-Tangier. CTM buses comfortable. Negotiate grand taxi prices.",
    },
    "uae": {
        "popular": ["drive", "flight"],
        "notes": "Car rental common. Metro in Dubai. Flights between emirates quick. Inter-city buses available.",
        "tips": "Rent cars for flexibility. Dubai Metro excellent. Etihad/Emirates for domestic.",
    },
    "jordan": {
        "popular": ["drive", "bus"],
        "notes": "Compact country, driving convenient. JETT buses for main routes. No rail network.",
        "tips": "Rent car for Dead Sea, Wadi Rum. JETT for Amman-Aqaba. Taxis for short trips.",
    },
    "israel": {
        "popular": ["train", "bus", "drive"],
        "notes": "Israel Railways improving. Egged buses extensive. Very compact country.",
        "tips": "Rav-Kav card for transit. Trains for Tel Aviv-Haifa. Sherut shared taxis available.",
    },
    # Oceania
    "australia": {
        "popular": ["flight", "drive"],
        "notes": "Huge distances - flying essential between cities. Road trips amazing for coastlines. Limited trains.",
        "tips": "Jetstar, Virgin for budget flights. Rent campervan for Great Ocean Road/outback. Indian Pacific for adventure.",
    },
    "new_zealand": {
        "popular": ["drive", "bus", "flight"],
        "notes": "Compact enough to drive. InterCity buses connect everywhere. Scenic flights quick option.",
        "tips": "Rent car/campervan for freedom. InterCity FlexiPass. Air NZ for island hopping.",
    },
    # Africa
    "egypt": {
        "popular": ["train", "flight", "bus"],
        "notes": "Trains connect Cairo-Luxor-Aswan. Flights for longer distances. Buses for Red Sea coast.",
        "tips": "Sleeper train Cairo-Luxor. EgyptAir for domestic. Go Bus for intercity.",
    },
    "south_africa": {
        "popular": ["flight", "drive"],
        "notes": "Distances large - flights between cities. Car rental common. Gautrain in Johannesburg. Baz Bus for backpackers.",
        "tips": "FlySafair, Kulula for budget flights. Rent cars for Garden Route.",
    },
    "kenya": {
        "popular": ["flight", "bus"],
        "notes": "SGR train Nairobi-Mombasa. Flights for safari destinations. Matatus for local travel.",
        "tips": "SGR excellent value. Safari flights via Wilson Airport. Easy Coach for buses.",
    },
    "tanzania": {
        "popular": ["flight", "bus"],
        "notes": "Flights essential for safari parks. Buses between major cities. Ferry to Zanzibar.",
        "tips": "Precision Air, Fastjet for domestic. Dar Express for buses. Azam Marine for Zanzibar ferry.",
    },
}


def detect_region(origin: str, region: str) -> str:
    """Detect the transport region based on origin and region strings.

    Args:
        origin: Origin city or location name.
        region: Region or country name.

    Returns:
        Region key for REGIONAL_TRANSPORT_PROFILES lookup, or "unknown".
    """
    text = f"{origin} {region}".lower()

    # India sub-regions (check before direct match to avoid "india" short-circuiting)
    if "india" in text:
        south = ["bangalore", "bengaluru", "chennai", "hyderabad", "kerala", "tamil", "karnataka", "kochi", "trivandrum"]
        north = ["delhi", "agra", "jaipur", "rajasthan", "varanasi", "himalaya", "lucknow", "amritsar"]
        if any(c in text for c in south):
            return "india_south"
        if any(c in text for c in north):
            return "india_north"
        return "india"

    # Direct country matches (sorted longest-first to prefer specific keys)
    for key in sorted(REGIONAL_TRANSPORT_PROFILES, key=len, reverse=True):
        if key.replace("_", " ") in text:
            return key

    # Regional groupings - Southeast Asia
    se_asia = ["vietnam", "thailand", "indonesia", "malaysia", "cambodia", "laos", "myanmar", "philippines"]
    if any(c in text for c in se_asia):
        for c in se_asia:
            if c in text and c in REGIONAL_TRANSPORT_PROFILES:
                return c
        return "thailand"  # Default SE Asia

    # East Asia
    if "japan" in text:
        return "japan"
    if "china" in text:
        return "china"
    if "korea" in text:
        return "south_korea"
    if "taiwan" in text:
        return "taiwan"

    # Europe
    west_eu = ["france", "germany", "italy", "spain", "netherlands", "belgium", "switzerland", "austria", "portugal"]
    east_eu = ["poland", "czech", "hungary", "romania", "bulgaria", "croatia", "serbia", "slovakia", "slovenia"]
    if any(c in text for c in west_eu):
        return "europe_west"
    if any(c in text for c in east_eu):
        return "europe_east"
    if any(c in text for c in ["uk", "england", "scotland", "ireland", "wales", "britain"]):
        return "uk_ireland"
    if any(c in text for c in ["norway", "sweden", "denmark", "finland", "iceland"]):
        return "scandinavia"

    # Americas
    if any(c in text for c in ["new york", "boston", "dc", "washington", "philadelphia", "east coast", "miami", "atlanta"]):
        return "usa_east"
    if any(c in text for c in ["california", "los angeles", "san francisco", "seattle", "west coast", "pacific", "las vegas", "portland"]):
        return "usa_west"
    if "mexico" in text:
        return "mexico"
    if "brazil" in text:
        return "brazil"
    if "argentina" in text:
        return "argentina"
    if "peru" in text:
        return "peru"
    if "colombia" in text:
        return "colombia"

    # Middle East
    if "turkey" in text or "turkiye" in text:
        return "turkey"
    if "morocco" in text:
        return "morocco"
    if any(c in text for c in ["uae", "dubai", "abu dhabi"]):
        return "uae"
    if "jordan" in text:
        return "jordan"
    if "israel" in text:
        return "israel"

    # Oceania
    if "australia" in text:
        return "australia"
    if "new zealand" in text or "nz" in text:
        return "new_zealand"

    # Africa
    if "egypt" in text:
        return "egypt"
    if "south africa" in text:
        return "south_africa"
    if "kenya" in text:
        return "kenya"
    if "tanzania" in text:
        return "tanzania"

    return "unknown"


def get_transport_guidance(origin: str, region: str, user_prefs: list | None = None) -> str:
    """Build transport guidance based on regional intelligence and user preferences.

    Args:
        origin: Origin city or location name.
        region: Region or country name.
        user_prefs: Optional list of transport mode preferences.

    Returns:
        Formatted transport guidance string for use in LLM prompts.
    """
    detected_region = detect_region(origin, region)
    profile = REGIONAL_TRANSPORT_PROFILES.get(detected_region)

    if user_prefs:
        prefs = ", ".join(
            [t.value if hasattr(t, "value") else str(t) for t in user_prefs]
        )
        guidance = f"**TRANSPORT GUIDANCE:**\nYour preferred modes: {prefs}\n\n"
        if profile:
            guidance += (
                f"Regional context for {region}:\n"
                f"- Popular modes: {', '.join(profile['popular'])}\n"
                f"- {profile['notes']}\n"
                f"- Tips: {profile['tips']}\n\n"
                "Use your preferred modes when available, but consider the regional "
                "alternatives if they make more sense."
            )
        return guidance

    if profile:
        return (
            f"**REGIONAL TRANSPORT INTELLIGENCE for {region}:**\n"
            f"Popular transport modes: {', '.join(profile['popular'])}\n\n"
            f"{profile['notes']}\n\n"
            f"Booking tips: {profile['tips']}\n\n"
            "**IMPORTANT:** Choose transport modes that are ACTUALLY POPULAR and "
            "AVAILABLE in this region.\n"
            "Don't default to trains if buses are the norm. Consider:\n"
            "- What locals and travelers actually use\n"
            "- What's reliable and comfortable for tourists\n"
            "- Realistic booking options"
        )

    # Unknown region - generic guidance
    return (
        "**TRANSPORT GUIDANCE:**\n"
        "Choose appropriate transport for this region:\n"
        "- FLIGHT: For distances >500km or when ground travel >8 hours\n"
        "- TRAIN: When good rail network exists (Europe, Japan, India)\n"
        "- BUS: Often most practical in SE Asia, South America, developing regions\n"
        "- DRIVE: For scenic routes, remote areas, or when flexibility needed\n\n"
        "Research what's actually popular and reliable in this specific region."
    )
