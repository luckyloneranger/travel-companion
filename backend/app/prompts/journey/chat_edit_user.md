# Current Journey Plan

```json
{current_journey}
```

# User's Edit Request

"{user_message}"

# Original Trip Context
- Origin: {origin}
- Region: {region}
- User Interests: {interests}
- Pace: {pace}

# Instructions
Process the user's edit request and return the updated journey plan. Remember to:
1. Return the COMPLETE updated journey object
2. Keep changes minimal - only modify what the user asked for
3. Ensure travel legs are updated if cities change
4. Update the route string and total_days as needed
