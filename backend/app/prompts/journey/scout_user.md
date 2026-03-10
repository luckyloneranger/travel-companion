Plan a {total_days}-day journey starting from {origin}, exploring {region}.
Travel dates: {travel_dates}

**Traveler Profile:**
- Interests: {interests}
- Pace: {pace}
- Group: {travelers_description}
- Budget: {budget}
- Places to include (if any): {must_include}
- Places to avoid (if any): {avoid}

{transport_guidance}

{landmarks_context}

**Your Task:**
1. Decide the optimal number of **base cities** — fewer is better, use excursions for nearby attractions
2. Select destinations matching the interests — include iconic landmarks, not just major cities
3. Allocate days **weighted by attraction density** (total must equal {total_days}, minimum 2 per base)
4. For nearby attractions (<2h from a base city): add as `excursion_type` themes on the base, NOT as separate cities
5. Create logical travel connections (no backtracking)
6. Provide 5-8 experience_themes per destination (categories, NOT specific place names)

**EXAMPLE OUTPUT** (7-day Japan trip):
```json
{{
  "theme": "Cultural Wonders of Kansai",
  "summary": "A week exploring Japan's cultural heartland, from ancient temples in Kyoto to street food paradise in Osaka.",
  "cities": [
    {{
      "name": "Kyoto",
      "country": "Japan",
      "days": 3,
      "why_visit": "Japan's cultural capital with 2000+ temples and traditional geisha districts",
      "best_time_to_visit": "Morning for temples, evening for Gion district",
      "seasonal_notes": "Cherry blossom late Mar-Apr; autumn colors Nov",
      "visa_notes": "Visa-free for most nationalities up to 90 days",
      "altitude_meters": 50,
      "safety_notes": "Very safe for all travelers",
      "experience_themes": [
        {{
          "theme": "Shrine and temple circuit",
          "category": "religious",
          "why": "Thousands of torii gates, golden pavilions, and zen gardens"
        }},
        {{
          "theme": "Traditional food markets",
          "category": "food",
          "why": "400-year-old market with matcha sweets and fresh seafood"
        }},
        {{
          "theme": "Bamboo forests and zen gardens",
          "category": "nature",
          "why": "Serene bamboo groves and world-class landscaped gardens"
        }}
      ],
      "accommodation": {{
        "name": "Hotel Granvia Kyoto",
        "why": "Connected to Kyoto Station, perfect base for day trips",
        "estimated_nightly_usd": 150,
        "budget_range_usd": [120, 200],
        "booking_hint": "Search Booking.com or Agoda for hotels near Kyoto Station, ¥18,000-30,000/night"
      }},
      "accommodation_alternatives": [
        {{
          "name": "Daiwa Roynet Hotel Kyoto-Shijo Karasuma",
          "why": "Central Shijo location near Nishiki Market, great value",
          "estimated_nightly_usd": 130
        }},
        {{
          "name": "The Thousand Kyoto",
          "why": "Premium hotel with onsen, opposite Kyoto Station",
          "estimated_nightly_usd": 200
        }}
      ]
    }}
  ],
  "travel_legs": [
    {{
      "from_city": "Osaka",
      "to_city": "Kyoto",
      "mode": "train",
      "duration_hours": 0.5,
      "distance_km": 43,
      "notes": "JR Special Rapid train, runs every 15 minutes",
      "fare_usd": 5,
      "booking_tip": "No reservation needed, tap IC card"
    }}
  ]
}}
```

**JSON Output Format:**
```json
{{
  "theme": "Catchy 3-6 word journey theme",
  "summary": "2-3 sentence engaging summary",
  "cities": [
    {{
      "name": "Destination Name",
      "country": "Country",
      "days": 3,
      "why_visit": "Why this destination fits the interests",
      "best_time_to_visit": "Timing advice",
      "seasonal_notes": "Seasonal guidance for travel dates",
      "visa_notes": "Entry requirements",
      "altitude_meters": 50,
      "safety_notes": "Safety context",
      "experience_themes": [
        {{
          "theme": "Experience category name",
          "category": "food|culture|nature|adventure|excursion|shopping|nightlife|entertainment|beach|wellness|religious",
          "why": "Brief description of the experience"
        }},
        {{
          "theme": "Far excursion name",
          "category": "excursion",
          "excursion_type": "full_day|half_day_morning|half_day_afternoon|multi_day|evening",
          "excursion_days": 2,
          "distance_from_city_km": 170,
          "destination_name": "Nikko",
          "why": "Why this excursion is worth dedicating time to"
        }}
      ],
      "accommodation": {{
        "name": "Real Hotel Name",
        "why": "Location advantage or value reason",
        "estimated_nightly_usd": 150,
        "budget_range_usd": [100, 200],
        "booking_hint": "Search Booking.com or Agoda for hotels in [area], [local_currency_range]/night"
      }},
      "accommodation_alternatives": [
        {{
          "name": "Alternative Hotel 1",
          "why": "Why this is a good alternative",
          "estimated_nightly_usd": 120
        }},
        {{
          "name": "Alternative Hotel 2",
          "why": "Why this is a good alternative",
          "estimated_nightly_usd": 180
        }}
      ]
    }}
  ],
  "travel_legs": [
    {{
      "from_city": "City1",
      "to_city": "City2",
      "mode": "train|bus|flight|drive|ferry",
      "duration_hours": 4.5,
      "distance_km": 250,
      "notes": "Service name, details",
      "fare_usd": 45,
      "booking_tip": "How to book",
      "visa_requirement": "Entry requirement (cross-country only)",
      "segments": [
        {{"mode": "drive", "from_place": "City2", "to_place": "City2 Airport", "duration_hours": 0.5}},
        {{"mode": "flight", "from_place": "City2 Airport", "to_place": "City3 Airport", "duration_hours": 2.0}},
        {{"mode": "drive", "from_place": "City3 Airport", "to_place": "City3", "duration_hours": 0.5}}
      ]
    }}
  ]
}}
```

**STRICT RULES:**
- Total days across all destinations MUST equal {total_days}
- Each base destination: minimum 2 days, 5-8 experience_themes, 1 accommodation with name + why + estimated_nightly_usd + budget_range_usd + booking_hint, plus 2 accommodation_alternatives
- Destinations commonly visited as day trips from a base MUST be excursion themes, NOT separate cities
- Allocate days proportionally to attraction density — NOT equal splits
- Use `experience_themes` ONLY — do NOT output a `highlights` array
- Each city MUST include seasonal_notes, visa_notes, safety_notes, altitude_meters
- Cross-country travel legs MUST include visa_requirement
- Multi-modal legs MUST include segments array
- Out-of-city excursion themes MUST set excursion_type and distance_from_city_km
- Excursion themes MUST include destination_name with a geocodable place name
- Return ONLY valid JSON — no markdown fences, no text
