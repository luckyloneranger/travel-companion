# Current Day Plans

```json
{day_plans}
```

# User's Edit Request

"{user_message}"

# Trip Context
- Cities: {cities}
- Interests: {interests}
- Pace: {pace}

# Instructions
Process the user's edit request and return the updated day plans. Remember to:
1. Return the COMPLETE updated day_plans array
2. Keep changes minimal - only modify what the user asked for
3. Ensure times flow logically (no overlaps, reasonable transitions)
4. Update day themes if the activities significantly change
5. Maintain realistic activity durations
