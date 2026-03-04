Create a {num_days}-day practical itinerary for **{destination}** that a tourist can follow.
Travel dates: {travel_dates}

USER INTERESTS: {interests}
PACE: {pace}
- {total} total stops per day
- {attractions} attractions/sights per day
- {dining} dining stops per day

**IMPORTANT — Activity count per pace (MUST follow):**
- "packed": MUST have 7-10 activities per day (maximize sightseeing, fill every time slot)
- "moderate": MUST have 5-7 activities per day (balanced exploration)
- "relaxed": MUST have 3-5 activities per day (slow, easy-going)
Failing to meet the activity count for the selected pace is a critical error.

=== ATTRACTIONS (pick from these for sightseeing) ===
{attractions_json}

=== RESTAURANTS/CAFES (pick from these for meals) ===
{dining_json}

{other_section}

{must_include_section}

## GEOGRAPHIC CLUSTERING GUIDE
Each place has coordinates (lat, lng). Group places that are close together on the SAME DAY.
- Places within ~2km of each other = great for same day
- Places 5km+ apart = prefer different days unless on a transit route

## MEAL PLACEMENT RULES
- Every day MUST have exactly 2 dining places: one for lunch, one for dinner. No exceptions.
- The FIRST dining place in each day's list = LUNCH (scheduled ~12:30)
- The LAST dining place in each day's list = DINNER (scheduled ~18:30)
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

## BUDGET & COST CONTEXT

Budget tier: {budget_tier}
{daily_budget_line}

**IMPORTANT: Total daily spend MUST stay within the daily budget target.** Select cheaper alternatives if needed to stay under budget.
- If budget tier is "budget": prefer free attractions, street food, budget-friendly cafes, and low-cost options. Avoid expensive restaurants and paid attractions when free alternatives exist.
- If budget tier is "moderate": balance cost and experience. Mix free and paid attractions.
- If budget tier is "luxury": prioritize premium experiences, fine dining, and exclusive venues.

For each selected place, estimate the cost per person in USD. Add a "cost_estimates" field to your JSON output:

```json
"cost_estimates": {{
    "place_id_1": 0,
    "place_id_2": 15.50,
    "place_id_3": 35.00
}}
```

Cost estimation guidelines:
- Free attractions (parks, plazas, temples with no entry): 0
- Budget meals (street food, cafes): $5-15
- Moderate meals (sit-down restaurants): $15-40
- Expensive dining: $40+
- Museum/attraction entry: varies by destination (typically $5-25)
- Use local knowledge to estimate accurately for {city_name}

Google Places price_level reference (0-4 scale):
- 0 = free, 1 = budget ($), 2 = moderate ($$), 3 = expensive ($$$), 4 = luxury ($$$$)

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
    }},
    "cost_estimates": {{
        "place_id_1": 0,
        "place_id_2": 15.50,
        "restaurant_id": 25.00
    }}
}}

## STRICT REQUIREMENTS
1. Each day's place_ids array MUST contain dining places — first dining = lunch, last dining = dinner
2. Include duration estimates (in minutes) for ALL selected places in the "durations" object
3. Keep each day geographically clustered (check lat/lng coordinates)
4. Select places that match the user's interests
5. Each day needs a descriptive, engaging theme
6. NEVER repeat the same place_id in multiple days or within the same day — each place should appear exactly once
7. Return ONLY valid JSON — no markdown fences, no text before or after
