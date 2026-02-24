"""Regional transport configuration for journey planning.

Contains transport profiles for different regions worldwide,
including popular transport modes, notes, and booking tips.
"""

# Regional transport intelligence - what modes are popular/reliable in different regions
REGIONAL_TRANSPORT_PROFILES = {
    # Southeast Asia
    "vietnam": {
        "popular": ["bus", "train", "flight"],
        "notes": "Sleeper buses are very popular for long distances (8-12h overnight). Limited train network (Hanoi-HCMC main line). Domestic flights cheap.",
        "tips": "Futa, The Sinh Tourist for buses. Vietnam Railways for trains. VietJet, Bamboo for budget flights."
    },
    "thailand": {
        "popular": ["bus", "train", "flight"],
        "notes": "Excellent overnight buses and trains. BTS/MRT in Bangkok. Budget flights via AirAsia, Nok Air. Train scenic but slow.",
        "tips": "12go.asia for bookings. VIP buses are comfortable. Southern beaches often require bus+ferry."
    },
    "indonesia": {
        "popular": ["flight", "ferry", "bus"],
        "notes": "Island hopping requires flights or ferries. Road travel limited except Java/Sumatra. Many budget airlines.",
        "tips": "Lion Air, Garuda for flights. Pelni ferries for adventure. Java has good train network."
    },
    
    # South Asia  
    "india": {
        "popular": ["train", "flight", "bus"],
        "notes": "Trains are king - extensive network, Shatabdi/Rajdhani for speed. Flights for >6 hour journeys. Volvo buses for shorter routes.",
        "tips": "IRCTC for trains (book 30+ days ahead). Redbus for buses. IndiGo, Vistara for flights."
    },
    "india_south": {
        "popular": ["train", "bus", "flight"],
        "notes": "Good train connectivity. KSRTC, TNSTC buses reliable and frequent. Hill stations often bus-only.",
        "tips": "Shatabdi trains excellent. Volvo sleepers overnight. Flights for Bangalore-Chennai-Hyderabad triangle."
    },
    "india_north": {
        "popular": ["train", "flight", "drive"],
        "notes": "Golden Triangle (Delhi-Agra-Jaipur) best by train/drive. Himalayan regions require driving. Varanasi-Lucknow has good trains.",
        "tips": "Gatimaan Express to Agra. Hire car+driver for Rajasthan flexibility."
    },
    "sri_lanka": {
        "popular": ["train", "bus", "drive"],
        "notes": "Scenic train journeys (Kandy-Ella famous). Good bus network. Car+driver popular for flexibility.",
        "tips": "Train Colombo-Kandy-Ella is spectacular. Buses frequent but slow. Hiring driver very affordable."
    },
    
    # East Asia
    "japan": {
        "popular": ["train", "bus", "flight"],
        "notes": "Shinkansen (bullet trains) are world-class. JR Pass economical for multi-city. Highway buses budget-friendly.",
        "tips": "JR Pass for 7/14/21 days. Willer Express for overnight buses. Domestic flights for Okinawa, Hokkaido."
    },
    "china": {
        "popular": ["train", "flight", "bus"],
        "notes": "High-speed rail network extensive and excellent. Flights for distant regions. Buses for rural/mountain areas.",
        "tips": "G/D trains high-speed. Get seats via Trip.com. Flights cheap domestically."
    },
    "south_korea": {
        "popular": ["train", "bus"],
        "notes": "KTX high-speed trains excellent. Express buses comfortable and frequent. Country is compact.",
        "tips": "Korail pass available. T-money card works on buses too. Most trips <3 hours."
    },
    
    # Europe
    "europe_west": {
        "popular": ["train", "flight", "bus"],
        "notes": "Excellent high-speed trains (TGV, Eurostar, ICE). Budget flights Ryanair/EasyJet. Flixbus budget option.",
        "tips": "Eurail Pass for multi-country. Book TGV/Eurostar early. Flixbus for tight budgets."
    },
    "europe_east": {
        "popular": ["bus", "train", "flight"],
        "notes": "Trains less reliable than Western Europe. Excellent bus networks (FlixBus, RegioJet). Budget flights plentiful.",
        "tips": "RegioJet for comfort. Trains scenic but slow. Wizz Air, Ryanair for flights."
    },
    "uk_ireland": {
        "popular": ["train", "bus", "drive"],
        "notes": "Trains expensive but convenient. National Express/Megabus budget. Driving easy (left-hand remember!).",
        "tips": "Book trains in advance for savings. Megabus from £1. Rent cars outside London."
    },
    "scandinavia": {
        "popular": ["flight", "train", "ferry"],
        "notes": "Distances large - flights often practical. Excellent train networks (Sweden, Norway). Ferries between countries.",
        "tips": "Norwegian, SAS for flights. Inter-rail popular. Hurtigruten for coastal Norway experience."
    },
    
    # Americas
    "usa_east": {
        "popular": ["flight", "train", "drive"],
        "notes": "Amtrak along Northeast Corridor good. Flights for longer distances. Driving common but consider traffic.",
        "tips": "Acela for NYC-DC-Boston. Rent cars for flexibility. Megabus/Greyhound budget option."
    },
    "usa_west": {
        "popular": ["flight", "drive"],
        "notes": "Distances huge - flights or driving. Train options limited. Road trips iconic (Pacific Coast Highway!).",
        "tips": "Southwest, Alaska Airlines for flights. Rent cars - it's the American way. Amtrak Coast Starlight scenic."
    },
    "mexico": {
        "popular": ["bus", "flight"],
        "notes": "Excellent luxury bus network (ADO, ETN, Primera Plus). Affordable flights. No passenger trains.",
        "tips": "ADO for Yucatan. ETN for comfort. Volaris, VivaAerobus for cheap flights. Book buses at terminal."
    },
    "peru": {
        "popular": ["bus", "flight"],
        "notes": "Cruz del Sur excellent buses. Flights for Lima-Cusco (or acclimatize slowly). Train to Machu Picchu.",
        "tips": "Cruz del Sur VIP worth it. LATAM for domestic flights. PeruRail/IncaRail for Machu Picchu."
    },
    
    # Middle East
    "turkey": {
        "popular": ["flight", "bus", "train"],
        "notes": "Domestic flights cheap and efficient. Bus network excellent. Train improving but limited.",
        "tips": "Pegasus, Turkish for flights. Metro, Kamil Koç for buses. High-speed train Ankara-Istanbul."
    },
    "morocco": {
        "popular": ["train", "bus", "drive"],
        "notes": "ONCF trains connect major cities. CTM/Supratours buses excellent. Grand taxis for shorter routes.",
        "tips": "Train Casablanca-Marrakech-Tangier. CTM buses comfortable. Negotiate grand taxi prices."
    },
    
    # Oceania  
    "australia": {
        "popular": ["flight", "drive"],
        "notes": "Huge distances - flying essential between cities. Road trips amazing for coastlines. Limited trains.",
        "tips": "Jetstar, Virgin for budget flights. Rent campervan for Great Ocean Road/outback. Indian Pacific for adventure."
    },
    "new_zealand": {
        "popular": ["drive", "bus", "flight"],
        "notes": "Compact enough to drive. InterCity buses connect everywhere. Scenic flights quick option.",
        "tips": "Rent car/campervan for freedom. InterCity FlexiPass. Air NZ for island hopping."
    },
}


def detect_region(origin: str, region: str) -> str:
    """Detect the transport region based on origin and region strings.
    
    Args:
        origin: Origin city/location
        region: Region or country name
        
    Returns:
        Region key for REGIONAL_TRANSPORT_PROFILES lookup
    """
    text = f"{origin} {region}".lower()
    
    # Direct country matches
    for key in REGIONAL_TRANSPORT_PROFILES.keys():
        if key.replace("_", " ") in text:
            return key
    
    # Regional groupings
    se_asia = ["vietnam", "thailand", "indonesia", "malaysia", "cambodia", "laos", "myanmar", "philippines"]
    if any(c in text for c in se_asia):
        for c in se_asia:
            if c in text and c in REGIONAL_TRANSPORT_PROFILES:
                return c
        return "thailand"  # Default SE Asia
    
    if "japan" in text:
        return "japan"
    if "china" in text:
        return "china"
    if "korea" in text:
        return "south_korea"
    
    # India regions
    if "india" in text:
        if any(c in text for c in ["bangalore", "chennai", "hyderabad", "kerala", "tamil", "karnataka"]):
            return "india_south"
        if any(c in text for c in ["delhi", "agra", "jaipur", "rajasthan", "varanasi", "himalaya"]):
            return "india_north"
        return "india"
    
    # Europe
    if any(c in text for c in ["france", "germany", "italy", "spain", "netherlands", "belgium", "switzerland", "austria"]):
        return "europe_west"
    if any(c in text for c in ["poland", "czech", "hungary", "romania", "bulgaria", "croatia", "serbia"]):
        return "europe_east"
    if any(c in text for c in ["uk", "england", "scotland", "ireland", "wales", "britain"]):
        return "uk_ireland"
    if any(c in text for c in ["norway", "sweden", "denmark", "finland", "iceland"]):
        return "scandinavia"
    
    # Americas
    if any(c in text for c in ["new york", "boston", "dc", "washington", "philadelphia", "east coast"]):
        return "usa_east"
    if any(c in text for c in ["california", "los angeles", "san francisco", "seattle", "west coast", "pacific"]):
        return "usa_west"
    if "mexico" in text:
        return "mexico"
    if "peru" in text:
        return "peru"
    
    # Oceania
    if "australia" in text:
        return "australia"
    if "new zealand" in text or "nz" in text:
        return "new_zealand"
    
    # Middle East
    if "turkey" in text or "türkiye" in text:
        return "turkey"
    if "morocco" in text:
        return "morocco"
    
    return "unknown"


def get_transport_guidance(origin: str, region: str, user_prefs: list | None = None) -> str:
    """Build transport guidance based on regional intelligence and user preferences.
    
    Args:
        origin: Origin city/location
        region: Region or country name
        user_prefs: Optional list of TransportMode preferences
        
    Returns:
        Formatted transport guidance string for the prompt
    """
    detected_region = detect_region(origin, region)
    profile = REGIONAL_TRANSPORT_PROFILES.get(detected_region)
    
    if user_prefs:
        # User has preferences - mention them but also include regional context
        prefs = ", ".join([t.value if hasattr(t, 'value') else str(t) for t in user_prefs])
        guidance = f"""**TRANSPORT GUIDANCE:**
Your preferred modes: {prefs}

"""
        if profile:
            guidance += f"""Regional context for {region}:
- Popular modes: {', '.join(profile['popular'])}
- {profile['notes']}
- Tips: {profile['tips']}

Use your preferred modes when available, but consider the regional alternatives if they make more sense."""
        return guidance
    
    if profile:
        # No user preference - give full regional intelligence
        return f"""**REGIONAL TRANSPORT INTELLIGENCE for {region}:**
Popular transport modes: {', '.join(profile['popular'])}

{profile['notes']}

Booking tips: {profile['tips']}

**IMPORTANT:** Choose transport modes that are ACTUALLY POPULAR and AVAILABLE in this region. 
Don't default to trains if buses are the norm. Consider:
- What locals and travelers actually use
- What's reliable and comfortable for tourists
- Realistic booking options"""
    
    # Unknown region - generic guidance
    return """**TRANSPORT GUIDANCE:**
Choose appropriate transport for this region:
- FLIGHT: For distances >500km or when ground travel >8 hours
- TRAIN: When good rail network exists (Europe, Japan, India)
- BUS: Often most practical in SE Asia, South America, developing regions
- DRIVE: For scenic routes, remote areas, or when flexibility needed

Research what's actually popular and reliable in this specific region."""
