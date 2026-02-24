Plan a {total_days}-day journey starting from {origin}, exploring {region}.
Travel dates: {travel_dates}

**Traveler Profile:**
- Interests: {interests}
- Pace: {pace}
- Places to include (if any): {must_include}
- Places to avoid (if any): {avoid}

{transport_guidance}

**Your Task:**
1. Decide the optimal number of cities (you choose based on days, pace, and regional distances)
2. Select cities that best match the interests — ensure variety across the journey
3. Allocate days to each city (total must equal {total_days}, minimum 2 days per city)
4. Create logical travel connections between cities (no backtracking)
5. Suggest 3-5 highlights per city using ONLY the allowed categories

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
      "notes": "JR Special Rapid train, runs every 15 minutes. Covered by JR Pass.",
      "estimated_cost": "¥580 (or free with JR Pass)",
      "booking_tip": "No reservation needed. Just tap your IC card or show JR Pass."
    }}
  ]
}}
```

**JSON Output Format:**
```json
{{
  "theme": "A catchy 3-6 word theme for this journey",
  "summary": "2-3 sentence engaging summary of the journey, mentioning what makes it special",
  "cities": [
    {{
      "name": "CityName",
      "country": "Country",
      "days": 2,
      "why_visit": "Why this city fits the traveler's interests — be specific",
      "best_time_to_visit": "Morning/Evening recommendations for this city",
      "highlights": [
        {{
          "name": "Attraction or Experience Name",
          "description": "Vivid 1-2 sentence description with an insider tip",
          "category": "culture|food|nature|history|shopping|nightlife|adventure|wellness|architecture|art|religious|markets|beach|entertainment|photography|local_life",
          "suggested_duration_hours": 2.0
        }}
      ]
    }}
  ],
  "travel_legs": [
    {{
      "from_city": "{origin}",
      "to_city": "FirstCity",
      "mode": "bus|train|flight|drive|ferry",
      "duration_hours": 4.5,
      "distance_km": 250,
      "notes": "Specific service name, departure recommendations, comfort level",
      "estimated_cost": "Local currency estimate",
      "booking_tip": "How/where to book, how far in advance"
    }}
  ]
}}
```

**STRICT RULES:**
- Total days across all cities MUST equal {total_days}
- Each city MUST have minimum 2 days
- Each city MUST have 3-5 highlights with vivid descriptions
- Travel legs connect origin → city1 → city2 → ... in geographic order
- Choose transport modes that are ACTUALLY available and popular in {region}
- Return ONLY the JSON object — no markdown fences, no text before or after
