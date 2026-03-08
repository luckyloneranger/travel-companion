Fix these day plans for **{destination}**:

**Issues found by reviewer:**
{issues_detail}

**Current plan:**
{current_plan_json}

**Available candidates for swapping:**
{candidates_json}

**Already planned on other days (DO NOT reuse these place_ids):**
{already_used_ids}

Fix each issue. Return the COMPLETE revised plan as JSON:
{{
    "selected_place_ids": ["id1", "id2", ...],
    "day_groups": [...],
    "durations": {{...}},
    "cost_estimates": {{...}}
}}
