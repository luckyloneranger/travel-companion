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

**Current Cities:**
{cities_detail}

**Current Travel:**
{travel_detail}

**Step-by-step process:**
1. For each critical/major issue, determine the minimum change needed
2. Check if the fix introduces new problems (e.g., changing a city breaks the route)
3. Verify total days still equal {total_days}
4. Write a reasoning entry for each issue explaining your fix
5. Output the complete revised plan

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
      "days": 2,
      "why_visit": "Why visit — be specific to traveler interests",
      "best_time_to_visit": "When to visit",
      "highlights": [
        {{
          "name": "Name",
          "description": "Vivid 1-2 sentence description with insider tip", 
          "category": "culture|food|nature|history|shopping|nightlife|adventure|wellness|architecture|art|religious|markets|beach|entertainment|photography|local_life",
          "suggested_duration_hours": 2.0
        }}
      ]
    }}
  ],
  "travel_legs": [
    {{
      "from_city": "Origin",
      "to_city": "Destination",
      "mode": "bus|train|flight|drive|ferry",
      "duration_hours": 4.5,
      "distance_km": 250,
      "notes": "Specific service recommendations",
      "estimated_cost": "Cost in local currency",
      "booking_tip": "Booking info and timing"
    }}
  ]
}}
```

**STRICT RULES:**
- Include the `reasoning` array FIRST — explain each fix before the plan
- Total days across all cities MUST still equal {total_days}
- Do NOT remove or swap cities that have no issues
- Each city must have 3-5 highlights
- Return ONLY the JSON object — no markdown fences, no text before or after
