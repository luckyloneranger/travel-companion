# Design: Day Plan Quality Pipeline — Iterative Batch Planning

## Problem
Day plans are generated in a single-shot LLM call with no quality review or iteration. This produces:
- 6/10 nature days for Singapore (theme clustering)
- Universal Studios missing despite landmark discovery (no review catches it)
- Excursion days with 1 placeholder activity (no activity planning)
- 40% iconic attraction coverage vs 80%+ for journey plans

Journey planning uses Scout → Enrich → Review → Planner loop (scores 80-90). Day planning needs the same.

## Architecture

```
For each city:
  0. Pre-map experience_themes → day numbers (deterministic)
  1. Per batch of 2-3 days:
     a. Day Scout (LLM) — select activities for assigned themes from candidates
     b. Day Enricher (Google) — validate hours, compute routes, fill photos
     c. Day Reviewer (LLM) — score theme coverage, iconic inclusion, variety
     d. Day Planner Fix (LLM) — fix reviewer issues
     e. Loop if score < 70 (max 2 iterations)
  2. Merge all batches → TSP optimize → schedule → weather
```

## Components

### Theme-to-Day Pre-Mapping (deterministic, no LLM)

Before Day Scout runs, assign experience_themes to specific day numbers:

```python
def map_themes_to_days(
    themes: list[ExperienceTheme], num_days: int,
    blocked_days: dict[int, CityHighlight],
) -> dict[int, list[ExperienceTheme]]:
    """Assign themes to days, ensuring coverage."""
    # 1. Excursion themes go on blocked days (already scheduled)
    # 2. Full-day excursions go on specific single days
    # 3. Evening themes pair with daytime themes
    # 4. Remaining themes spread evenly across free days
    # 5. If more themes than days, combine compatible themes
    # 6. If more days than themes, allow multi-day themes (e.g., "food" on 2 days)
```

Output: `{1: [food_theme], 2: [culture_theme], 3: [excursion_theme], ...}`

### Day Scout Agent (renamed from DayPlannerAgent)

Receives per batch (2-3 days):
- Assigned themes for those days
- ALL candidates (attractions + dining) — same pool as current
- Landmark data (top 10 by review count) with "priority" flag
- Previously planned days (to avoid repeating places)
- Experience theme context (why, distance_from_city_km)

Outputs: `AIPlan` with day_groups, durations, cost_estimates (same schema as current).

**Prompt**: `day_scout_system.md` + `day_scout_user.md`

Key prompt differences from current day planner:
- Plans 2-3 days not 10 (smaller scope, better quality)
- Receives specific theme assignment per day (not free choice)
- Sees previously planned days (prevents repetition)
- Must include at least one landmark-flagged place per batch
- Excursion days get proper activity planning (not just placeholder)

### Day Enricher (Google validation, no LLM)

For each activity in the batch:
1. Validate opening hours vs scheduled time (Google Places `currentOpeningHours`)
2. Compute routes between consecutive activities (existing Routes API)
3. Fill missing photos from Google if available
4. Flag permanently closed venues
5. Validate coordinates are within city bounds

This reuses existing code:
- `_compute_routes_via_matrix()` → existing
- `places.get_place_details()` → for hours validation
- Photo URL resolution → existing

### Day Reviewer Agent (LLM)

Reviews the batch with full context:

**Prompt**: `day_reviewer_system.md` + `day_reviewer_user.md`

Evaluation dimensions:
1. **Theme Coverage (30%)**: Does each day cover its assigned theme? Are theme-relevant activities selected?
2. **Landmark Inclusion (20%)**: Are top-reviewed attractions from landmark data included? Missing top-5 = major issue.
3. **Activity Variety (15%)**: No 3+ consecutive same-category activities. Mix of indoor/outdoor.
4. **Duration Realism (15%)**: Full-day venues (theme parks, zoos) get 4-8h. Museums get 1-3h. Quick stops 30-60min.
5. **Pacing & Flow (10%)**: Morning major → light mid-day → afternoon → dinner flow. Not 3 museums then 3 parks.
6. **Meal Placement (10%)**: Lunch mid-day, dinner evening. Both are real restaurants, not temples.

Output: `DayReviewResult(score: int, is_acceptable: bool, issues: list[DayReviewIssue])`

```python
class DayReviewIssue(BaseModel):
    severity: str       # "critical", "major", "minor"
    day_number: int
    category: str       # "theme_coverage", "landmark", "variety", "duration", "pacing", "meal"
    description: str
    suggestion: str
```

### Day Planner Fix Agent (LLM)

Receives:
- Current batch plan with issues
- Reviewer feedback
- Full candidate pool (for swapping)
- Landmark data

**Prompt**: `day_planner_fix_system.md` + `day_planner_fix_user.md`

Fixes by swapping activities, not rewriting entire days. Preserves what works, replaces what doesn't.

### DayPlanOrchestrator Changes

```python
async def _plan_city_batched(self, city, candidates, landmarks, request):
    """Plan a city's days in batches with quality loop."""

    # Step 0: Pre-map themes to days
    theme_map = map_themes_to_days(
        city.experience_themes, free_day_count, blocked_days
    )

    # Step 1: Plan in batches of 2-3 days
    all_day_groups = []
    batch_size = 3
    planned_place_ids = set()  # Track what's already used

    for batch_start in range(0, free_day_count, batch_size):
        batch_days = range(batch_start, min(batch_start + batch_size, free_day_count))
        batch_themes = {d: theme_map.get(d+1, []) for d in batch_days}

        # Day Scout: plan this batch
        batch_plan = await self.day_scout.plan_batch(
            candidates=candidates,
            batch_themes=batch_themes,
            landmarks=landmarks,
            already_used=planned_place_ids,
            ...
        )

        # Day Enricher: validate hours + routes
        batch_plan = await self.day_enricher.enrich_batch(batch_plan)

        # Quality loop
        for iteration in range(MAX_DAY_ITERATIONS):
            review = await self.day_reviewer.review_batch(
                batch_plan, batch_themes, landmarks
            )

            if review.is_acceptable:
                break

            batch_plan = await self.day_fixer.fix_batch(
                batch_plan, review, candidates, landmarks
            )

        all_day_groups.extend(batch_plan.day_groups)
        planned_place_ids.update(batch_plan.selected_place_ids)

    return all_day_groups
```

### Progress Events

SSE stream shows batch progress:
```
city_start → batch_1_scouting → batch_1_reviewing → batch_2_scouting → ... → city_complete
```

### Models

```python
class DayReviewResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    is_acceptable: bool
    issues: list[DayReviewIssue] = []
    summary: str = ""

class DayReviewIssue(BaseModel):
    severity: str
    day_number: int
    category: str
    description: str
    suggestion: str
```

## Files

### New Files
- `backend/app/agents/day_scout.py` — DayScoutAgent (adapted from DayPlannerAgent)
- `backend/app/agents/day_enricher.py` — DayEnricherAgent (Google validation)
- `backend/app/agents/day_reviewer.py` — DayReviewerAgent (LLM quality)
- `backend/app/agents/day_fixer.py` — DayFixerAgent (LLM fix)
- `backend/app/models/day_review.py` — DayReviewResult, DayReviewIssue
- `backend/app/prompts/day_plan/day_scout_system.md`
- `backend/app/prompts/day_plan/day_scout_user.md`
- `backend/app/prompts/day_plan/day_reviewer_system.md`
- `backend/app/prompts/day_plan/day_reviewer_user.md`
- `backend/app/prompts/day_plan/day_fixer_system.md`
- `backend/app/prompts/day_plan/day_fixer_user.md`

### Modified Files
- `backend/app/orchestrators/day_plan.py` — batched planning loop
- `backend/app/dependencies.py` — wire new agents
- `backend/app/config/planning.py` — MAX_DAY_ITERATIONS, MIN_DAY_SCORE constants

### Unchanged Files
- `backend/app/algorithms/scheduler.py` — post-processing (after quality loop)
- `backend/app/algorithms/tsp.py` — route optimization (after quality loop)
- `backend/app/algorithms/quality/evaluators.py` — can be used alongside LLM reviewer
- `backend/app/services/google/routes.py` — route computation
- `backend/app/services/google/weather.py` — weather (post-processing)

## Success Criteria

1. Singapore 10-day: 70%+ iconic attraction coverage (up from 40%)
2. Every experience_theme gets at least one dedicated day
3. No 3+ consecutive same-category days
4. Theme parks get full-day treatment (6-8h, not 2h)
5. Day plan quality scores ≥ 70 via LLM reviewer
6. Total day plan generation time < 5 minutes for 10-day trip
