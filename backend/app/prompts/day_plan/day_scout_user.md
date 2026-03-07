Plan activities for days {batch_day_numbers} in **{destination}**.

ASSIGNED THEMES (each day MUST cover its assigned theme):
{batch_themes}

PACE: {pace} ({activities_per_day} total stops per day)

**CRITICAL: Each day MUST have at least {activities_per_day} activities. Fewer is a failure.**

{landmarks_section}

ALREADY PLANNED on other days (do NOT reuse these place_ids):
{already_used_ids}

=== ATTRACTIONS (pick from these for sightseeing — you MUST select from landmarks above) ===
{attractions_json}

=== RESTAURANTS/CAFES (pick from these for meals) ===
{dining_json}

{meal_time_guidance}

## OUTPUT FORMAT
Respond with this JSON (all place_id values MUST come from the candidate lists above):
{{
    "selected_place_ids": ["id1", "id2", ...],
    "day_groups": [
        {{
            "theme": "Theme matching the assigned theme for this day",
            "place_ids": ["morning_attraction", "attraction2", "LUNCH_restaurant", "afternoon_attraction", "DINNER_restaurant"]
        }}
    ],
    "durations": {{
        "place_id_1": 120,
        "restaurant_id": 75
    }},
    "cost_estimates": {{
        "place_id_1": 0,
        "restaurant_id": 25.00
    }}
}}

## STRICT REQUIREMENTS
1. Each day's place_ids MUST contain 2 dining places — first dining = lunch, last dining = dinner
2. Include duration and cost estimates for ALL selected places
3. Each day's theme MUST match the assigned theme above
4. NEVER use a place_id from the already-planned list
5. Return ONLY valid JSON
