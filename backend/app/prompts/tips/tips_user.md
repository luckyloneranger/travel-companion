Generate helpful tips for each activity in this travel schedule.

**Destination:** {destination}
**Traveler Interests:** {interests}

**Today's Schedule:**
{schedule}

**EXAMPLE OUTPUT:**
```json
{{
  "tips": {{
    "ChIJ_louvre_123": "Arrive before 9:30 AM via the underground Carrousel du Louvre entrance to skip the pyramid queue. Head straight to Denon wing for the Mona Lisa, then explore Egyptian antiquities which are less crowded.",
    "ChIJ_cafe_456": "Order the croque monsieur — it's their specialty since 1982. Sit on the terrace for a perfect view of the square."
  }}
}}
```

Return a JSON object with tips for each place:

```json
{{
  "tips": {{
    "{example_id}": "Your helpful, specific tip for this place...",
    ...
  }}
}}
```

Each tip should be 1-2 sentences with practical, insider advice specific to that place in {destination}.

Return ONLY the JSON object — no markdown fences, no text before or after.
