Review and fix this travel itinerary for **{destination}**.

**Traveler Context:**
- Interests: {interests}
- Pace: {pace}
- Dates: {travel_dates}

**Rules to check:**
1. Each day has at least 1 dining place (ideally 2: lunch + dinner)
2. No consecutive restaurants (must have attraction between them)
3. Each day has at least 1 attraction
4. Heavy activities are earlier in the day
5. Dinner restaurant is at or near the end of each day
6. Geographic clustering is maintained (places on same day are close together)

**Current plan:**
{plan_json}

**Available restaurants (unused, can swap in):**
{dining_json}

**Available attractions (unused, can swap in):**
{attractions_json}

**Step-by-step process:**
1. Check each day against the rules above
2. List every violation found
3. For each violation, determine the minimum fix (swap, move, reorder, add, or remove)
4. Apply fixes and produce the refined plan
5. Verify the refined plan passes all rules

**EXAMPLE OUTPUT:**
```json
{{
  "issues_found": [
    "Day 1 has no restaurant — added ChIJ_cafe_123 as lunch",
    "Day 2 has two consecutive restaurants — moved ChIJ_park_456 between them"
  ],
  "changes_made": [
    "Added ChIJ_cafe_123 to Day 1 position 3",
    "Reordered Day 2: swapped positions 3 and 4"
  ],
  "refined_plan": {{
    "selected_place_ids": ["id1", "id2", "id3"],
    "day_groups": [
      {{
        "theme": "Cultural Morning & Local Lunch",
        "place_ids": ["attraction1", "attraction2", "restaurant_lunch", "attraction3", "restaurant_dinner"]
      }}
    ]
  }}
}}
```

Return JSON:
```json
{{
  "issues_found": ["description of each issue"],
  "changes_made": ["description of each change"],
  "refined_plan": {{
    "selected_place_ids": ["all_ids"],
    "day_groups": [
      {{
        "theme": "Day theme",
        "place_ids": ["ordered_place_ids"]
      }}
    ]
  }}
}}
```

If no issues are found, return the original plan unchanged with `"issues_found": []` and `"changes_made": []`.

Return ONLY the JSON object — no markdown fences, no text before or after.
