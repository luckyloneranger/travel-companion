Create a {num_days}-day practical itinerary for **{destination}** that a tourist can follow.
Travel dates: {travel_dates}

USER INTERESTS: {interests}
PACE: {pace}
- {total} total stops per day
- {attractions} attractions/sights per day  
- {dining} dining stops per day

=== ATTRACTIONS (pick from these for sightseeing) ===
{attractions_json}

=== RESTAURANTS/CAFES (pick from these for meals) ===
{dining_json}

{other_section}

## GEOGRAPHIC CLUSTERING GUIDE
Each place has coordinates (lat, lng). Group places that are close together on the SAME DAY.
- Places within ~2km of each other = great for same day
- Places 5km+ apart = prefer different days unless on a transit route

## MEAL PLACEMENT RULES
- Place dining spots based on the pace:
  - Relaxed/Moderate: 2 dining per day (lunch + dinner)
  - Packed: 1-2 dining per day (at least dinner)
- The FIRST dining place in each day's list = LUNCH (scheduled ~12:30)
- The LAST dining place in each day's list = DINNER (scheduled ~19:00)
- Place lunch restaurant AFTER 2-3 morning attractions
- Place dinner restaurant LAST or second-to-last in the day

NOTE: Famous/historic restaurants (like Le Procope, Café de Flore) can BE an attraction!
If a restaurant is a destination in itself, it counts as both dining AND cultural experience.

## EXAMPLE OUTPUT (2-day Paris trip, moderate pace)
```json
{{
    "selected_place_ids": ["ChIJ_example1", "ChIJ_example2", "ChIJ_example3", "ChIJ_example4", "ChIJ_example5", "ChIJ_example6", "ChIJ_example7", "ChIJ_example8", "ChIJ_example9", "ChIJ_example10"],
    "day_groups": [
        {{
            "theme": "Historic Paris & the Seine",
            "place_ids": ["ChIJ_louvre", "ChIJ_tuileries", "ChIJ_cafe_marly", "ChIJ_orsay", "ChIJ_bistro_dinner"]
        }},
        {{
            "theme": "Montmartre & Local Charm",
            "place_ids": ["ChIJ_sacre_coeur", "ChIJ_moulin_rouge", "ChIJ_cafe_lunch", "ChIJ_place_tertre", "ChIJ_restaurant_dinner"]
        }}
    ],
    "durations": {{
        "ChIJ_louvre": 180,
        "ChIJ_tuileries": 45,
        "ChIJ_cafe_marly": 60,
        "ChIJ_orsay": 120,
        "ChIJ_bistro_dinner": 75,
        "ChIJ_sacre_coeur": 60,
        "ChIJ_moulin_rouge": 30,
        "ChIJ_cafe_lunch": 60,
        "ChIJ_place_tertre": 45,
        "ChIJ_restaurant_dinner": 75
    }}
}}
```

## DURATION GUIDELINES (estimate realistic visit times in minutes)
- Major museums: 90-180 (Louvre 180, smaller museums 90)
- Historical landmarks/monuments: 30-60
- Parks/gardens: 45-90
- Restaurants (lunch): 60-75
- Restaurants (dinner): 75-90
- Cafés: 30-45
- Churches/temples: 30-45
- Shopping areas: 60-90
- Markets: 45-75

## OUTPUT FORMAT
Respond with this JSON:
{{
    "selected_place_ids": ["id1", "id2", ...],
    "day_groups": [
        {{
            "theme": "Descriptive theme for the day",
            "place_ids": ["morning_attraction1", "attraction2", "LUNCH_restaurant", "afternoon_attraction", "DINNER_restaurant"]
        }}
    ],
    "durations": {{
        "place_id_1": 120,
        "place_id_2": 60,
        "restaurant_id": 75
    }}
}}

## STRICT REQUIREMENTS
1. Each day's place_ids array MUST contain dining places — first dining = lunch, last dining = dinner
2. Include duration estimates (in minutes) for ALL selected places in the "durations" object
3. Keep each day geographically clustered (check lat/lng coordinates)
4. Select places that match the user's interests
5. Each day needs a descriptive, engaging theme
6. Return ONLY valid JSON — no markdown fences, no text before or after
