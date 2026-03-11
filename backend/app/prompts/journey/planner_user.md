Fix this journey plan based on the review feedback:

**Current Plan:**
- Route: {route}
- Total Days: {total_days}

**Issues to Fix (by priority):**
{issues}

**Original Request:**
- Origin: {origin}
- Region: {region}
- Interests: {interests}
- Pace: {pace}
- Travel Dates: {travel_dates}
- Travelers: {travelers_description}
- Budget: {budget_tier}

**Current Cities:**
{cities_detail}

**Current Travel:**
{travel_detail}

{landmarks_context}

{must_see_context}

**Step-by-step process:**
1. For each critical/major issue, determine the minimum change needed
2. Check if the fix introduces new problems (e.g., changing a city breaks the route)
3. Verify total days still equal {total_days}
4. Write a reasoning entry for each issue explaining your fix
5. Output the complete revised plan
6. When fixing TIME FEASIBILITY: reduce days in overcrowded cities, or convert far destinations to excursions. If excursion overload is flagged, remove the least iconic excursion and mention it in `why_visit` instead.
7. When fixing BUDGET issues: suggest cheaper accommodation or remove expensive excursions
8. Preserve seasonal_notes, visa_notes, altitude_meters, safety_notes from the original plan
9. When fixing INTEREST ALIGNMENT: check if major experience categories from the landscape data are missing from experience_themes and add appropriate themes
10. Preserve excursion metadata (excursion_type, excursion_days, distance_from_city_km) on existing themes

Return the COMPLETE fixed plan in JSON:
```json
{{
  "reasoning": [
    "Issue: [description] → Fix: [what you changed and why]"
  ],
  "theme": "Journey theme",
  "summary": "2-3 sentence summary reflecting any changes",
  "cities": [
    {{
      "name": "CityName",
      "country": "Country",
      "days": 3,
      "why_visit": "Why visit — be specific to traveler interests",
      "best_time_to_visit": "When to visit",
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
        "estimated_nightly_usd": 150
      }}
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
      "segments": [
        {{"mode": "drive", "from_place": "City1", "to_place": "Airport", "duration_hours": 0.5}},
        {{"mode": "flight", "from_place": "Airport A", "to_place": "Airport B", "duration_hours": 2.0}}
      ]
    }}
  ]
}}
```

**STRICT RULES:**
- Include the `reasoning` array FIRST — explain each fix before the plan
- Total days across all cities MUST still equal {total_days}
- Do NOT remove or swap cities that have no issues
- Use `experience_themes` ONLY — do NOT output a `highlights` array
- Each city must have 5-8 experience_themes with category and why fields
- Each city MUST include seasonal_notes, visa_notes, safety_notes, altitude_meters
- Excursion themes MUST preserve excursion_type, distance_from_city_km, and destination_name
- Return ONLY the JSON object — no markdown fences, no text before or after
