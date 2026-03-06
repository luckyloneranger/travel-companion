Plan a {total_days}-day journey starting from {origin}, exploring {region}.
Travel dates: {travel_dates}

**Traveler Profile:**
- Interests: {interests}
- Pace: {pace}
- Group: {travelers_description}
- Places to include (if any): {must_include}
- Places to avoid (if any): {avoid}

{transport_guidance}

**Your Task:**
1. Decide the optimal number of destinations (you choose based on days, pace, and regional distances)
2. Select destinations that best match the interests — include iconic landmarks, natural wonders, and cultural hubs, not just major cities
3. Allocate days to each destination (total must equal {total_days}, minimum 2 days per destination)
4. Create logical travel connections between destinations (no backtracking)
5. Suggest 3-5 highlights per destination using ONLY the allowed categories

**EXAMPLE OUTPUT** (for a 7-day Japan trip — adapt structure to your region):
```json
{{
  "theme": "Cultural Wonders of Kansai",
  "summary": "A week exploring Japan's cultural heartland, from ancient temples in Kyoto to street food paradise in Osaka and sacred deer in Nara.",
  "cities": [
    {{
      "name": "Kyoto",
      "country": "Japan",
      "days": 3,
      "why_visit": "Japan's cultural capital with 2000+ temples, traditional geisha districts, and world-class gardens",
      "best_time_to_visit": "Morning for temples (avoid crowds), evening for Gion district",
      "highlights": [
        {{
          "name": "Fushimi Inari Shrine",
          "description": "Thousands of vermillion torii gates winding up Mount Inari — arrive at dawn for an ethereal, crowd-free experience",
          "category": "religious",
          "suggested_duration_hours": 2.5
        }},
        {{
          "name": "Nishiki Market",
          "description": "Kyoto's 400-year-old kitchen — sample pickles, matcha sweets, and fresh seafood across 100+ stalls",
          "category": "markets",
          "suggested_duration_hours": 1.5
        }},
        {{
          "name": "Arashiyama Bamboo Grove",
          "description": "Towering bamboo stalks create an otherworldly green corridor — best at sunrise",
          "category": "nature",
          "suggested_duration_hours": 2.0
        }}
      ],
      "accommodation": {{
        "name": "Hotel Granvia Kyoto",
        "why": "Connected to Kyoto Station, perfect base for day trips with excellent access to all rail lines"
      }}
    }}
  ],
  "travel_legs": [
    {{
      "from_city": "Osaka",
      "to_city": "Kyoto",
      "mode": "train",
      "duration_hours": 0.5,
      "distance_km": 43,
      "notes": "JR Special Rapid train, runs every 15 minutes. Covered by JR Pass.",
      "estimated_cost": "560 yen (or free with JR Pass)",
      "booking_tip": "No reservation needed. Just tap your IC card or show JR Pass."
    }}
  ]
}}
```

**JSON Output Format:**
Note: Use the key "cities" for the destinations array, but destinations CAN be non-city locations (bays, islands, national parks, etc.).
```json
{{
  "theme": "A catchy 3-6 word theme for this journey",
  "summary": "2-3 sentence engaging summary of the journey, mentioning what makes it special",
  "cities": [
    {{
      "name": "Destination Name (city, bay, island, region, etc.)",
      "country": "Country",
      "days": 2,
      "why_visit": "Why this destination fits the traveler's interests — be specific",
      "best_time_to_visit": "Morning/Evening recommendations for this destination",
      "highlights": [
        {{
          "name": "Attraction or Experience Name",
          "description": "Vivid 1-2 sentence description with an insider tip",
          "category": "culture|food|nature|history|shopping|nightlife|adventure|wellness|architecture|art|religious|markets|beach|entertainment|photography|local_life",
          "suggested_duration_hours": 2.0
        }}
      ],
      "accommodation": {{
        "name": "Specific Hotel, Resort, or Guesthouse Name",
        "why": "Brief reason — location advantage, style match, or value",
        "estimated_nightly_usd": 120
      }}
    }}
  ],
  "travel_legs": [
    {{
      "from_city": "FirstDestination",
      "to_city": "SecondDestination",
      "mode": "bus|train|flight|drive|ferry",
      "duration_hours": 4.5,
      "distance_km": 250,
      "notes": "Specific service name, departure recommendations, comfort level",
      "estimated_cost": "Local currency estimate",
      "fare_usd": 85,
      "booking_tip": "How/where to book, how far in advance"
    }}
  ]
}}
```

**STRICT RULES:**
- Total days across all destinations MUST equal {total_days}
- Each destination MUST have minimum 2 days
- Each destination MUST have 3-5 highlights with vivid descriptions
- The origin ({origin}) is the departure point — only include it in destinations if it matches the destination type AND has tourist value for day activities
- Travel legs connect destination1 to destination2 to destination3 and so on (first leg is from first destination to second destination)
- Choose transport modes that are ACTUALLY available and popular in {region} — include ferries/boats for coastal and island destinations
- Every destination MUST have an accommodation with a specific, real property name and estimated_nightly_usd. Missing accommodation is a validation failure.
- Each accommodation MUST include `estimated_nightly_usd` — your best estimate for a typical nightly rate in USD for this property
- Each travel leg MUST include `fare_usd` — your best estimate for a one-way fare per person in USD
- Return ONLY the JSON object — no markdown fences, no text before or after
