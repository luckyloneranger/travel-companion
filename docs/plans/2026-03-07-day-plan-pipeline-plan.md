# Day Plan Quality Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an iterative quality loop to day plan generation: Day Scout → Day Enricher → Day Reviewer → Day Fixer, processing in batches of 2-3 days with theme pre-mapping, matching the journey pipeline's quality process.

**Architecture:** Pre-map experience_themes to day numbers deterministically. Plan in 2-3 day batches via Day Scout (LLM). Validate opening hours and routes via Day Enricher (Google). Score quality via Day Reviewer (LLM). Fix issues via Day Fixer (LLM). Loop until score ≥ 70 (max 2 iterations per batch). Merge batches, then existing TSP/schedule/weather post-processing.

**Tech Stack:** Python (Pydantic v2, FastAPI, Google Places/Routes API), LLM (Azure OpenAI/Anthropic/Gemini via existing abstraction)

---

### Task 1: Add DayReviewResult model

**Files:**
- Create: `backend/app/models/day_review.py`

**Step 1:** Create the model file:
```python
from pydantic import BaseModel, Field


class DayReviewIssue(BaseModel):
    """A specific issue found during day plan quality review."""
    severity: str       # "critical", "major", "minor"
    day_number: int
    category: str       # "theme_coverage", "landmark", "variety", "duration", "pacing", "meal"
    description: str
    suggestion: str


class DayReviewResult(BaseModel):
    """Result of reviewing a batch of day plans."""
    score: int = Field(..., ge=0, le=100)
    is_acceptable: bool
    issues: list[DayReviewIssue] = []
    summary: str = ""
```

**Step 2:** Run tests — 199 passed (new file, no impact)
**Step 3:** Commit: `git commit -am "feat: add DayReviewResult model"`

---

### Task 2: Add theme-to-day pre-mapping utility

**Files:**
- Modify: `backend/app/config/planning.py`

**Step 1:** Add constants:
```python
MAX_DAY_PLAN_ITERATIONS: int = 2
MIN_DAY_PLAN_SCORE: int = 70
DAY_PLAN_BATCH_SIZE: int = 3
```

**Step 2:** Add `map_themes_to_days()` function:
```python
def map_themes_to_days(
    themes: list,  # ExperienceTheme objects
    num_days: int,
    blocked_days: dict[int, Any] | None = None,
) -> dict[int, list]:
    """Assign experience themes to day numbers, ensuring even coverage.

    1. Excursion themes (multi_day, full_day) go on their blocked days
    2. Evening themes pair with daytime themes on the same day
    3. Remaining themes spread evenly across free days
    4. If more days than themes, themes repeat (e.g., "food" on 2 days)
    """
    blocked = blocked_days or {}
    day_map: dict[int, list] = {d: [] for d in range(1, num_days + 1)}

    excursion_themes = []
    evening_themes = []
    regular_themes = []

    for t in themes:
        et = getattr(t, 'excursion_type', None)
        if et in ('full_day', 'multi_day'):
            excursion_themes.append(t)
        elif et == 'evening':
            evening_themes.append(t)
        else:
            regular_themes.append(t)

    # Step 1: Excursion themes go on blocked days
    for day_num, exc_highlight in blocked.items():
        matching = [t for t in excursion_themes
                    if t.theme.lower() in exc_highlight.name.lower()
                    or exc_highlight.name.lower() in t.theme.lower()]
        if matching:
            day_map[day_num].append(matching[0])

    # Step 2: Regular themes spread across free days
    free_days = sorted(d for d in range(1, num_days + 1) if d not in blocked)
    for i, theme in enumerate(regular_themes):
        if free_days:
            day_idx = free_days[i % len(free_days)]
            day_map[day_idx].append(theme)

    # Step 3: Evening themes pair with the least-loaded free days
    for theme in evening_themes:
        if free_days:
            lightest = min(free_days, key=lambda d: len(day_map[d]))
            day_map[lightest].append(theme)

    # Step 4: Empty free days get the most versatile theme repeated
    for d in free_days:
        if not day_map[d] and regular_themes:
            day_map[d].append(regular_themes[0])  # Repeat first theme

    return day_map
```

**Step 3:** Run tests, commit.

---

### Task 3: Create Day Scout Agent

**Files:**
- Create: `backend/app/agents/day_scout.py`
- Create: `backend/app/prompts/day_plan/day_scout_system.md`
- Create: `backend/app/prompts/day_plan/day_scout_user.md`

**Step 1:** Create `day_scout_system.md`:
```markdown
You are an expert activity planner selecting the BEST activities for specific themed days.

You receive:
- A batch of 2-3 days with ASSIGNED themes (you must follow these themes)
- Candidate places from Google Places API with ratings, reviews, and coordinates
- The destination's top landmarks by popularity
- Activities already planned on other days (do NOT repeat)

## RULES
1. Each day MUST have activities matching its assigned theme
2. Include at least one top-landmark per batch (by review count)
3. Each day needs 2 dining stops (lunch + dinner) from the restaurant candidates
4. Keep activities geographically clustered per day
5. Never repeat a place_id that appears in "already planned" list
6. Duration estimates must be realistic — theme parks 6-8h, museums 1-3h, cafes 30-45min

## OUTPUT
Return ONLY valid JSON. No markdown fences.
```

**Step 2:** Create `day_scout_user.md`:
```markdown
Plan activities for days {batch_day_numbers} in **{destination}**.

ASSIGNED THEMES:
{batch_themes}

PACE: {pace} ({activities_per_day} activities per day)

{landmarks_section}

ALREADY PLANNED (do NOT repeat these place_ids):
{already_used_ids}

=== ATTRACTIONS ===
{attractions_json}

=== RESTAURANTS ===
{dining_json}

{meal_time_guidance}

## OUTPUT FORMAT
{{
    "selected_place_ids": ["id1", "id2", ...],
    "day_groups": [
        {{
            "theme": "Theme matching the assigned theme for this day",
            "place_ids": ["morning1", "attraction2", "LUNCH", "afternoon", "DINNER"]
        }}
    ],
    "durations": {{"place_id": minutes}},
    "cost_estimates": {{"place_id": usd_amount}}
}}
```

**Step 3:** Create `day_scout.py`:
```python
import json
import logging
from app.models.internal import AIPlan
from app.prompts.loader import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayScoutAgent:
    """Selects activities for themed days from Google Places candidates."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def plan_batch(
        self,
        candidates: list,
        batch_themes: dict[int, list],  # {day_num: [themes]}
        destination: str,
        pace: str,
        landmarks: list[dict] | None = None,
        already_used: set[str] | None = None,
        meal_time_guidance: str = "",
        travelers_description: str = "1 adult",
    ) -> AIPlan:
        """Plan activities for a batch of 2-3 themed days."""
        system_prompt = day_plan_prompts.load("day_scout_system")
        user_prompt = self._build_user_prompt(
            candidates, batch_themes, destination, pace,
            landmarks, already_used, meal_time_guidance, travelers_description,
        )

        plan = await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
        return plan

    def _build_user_prompt(self, candidates, batch_themes, destination, pace,
                           landmarks, already_used, meal_time_guidance, travelers_description):
        """Build the user prompt for the Day Scout."""
        from app.config.planning import DAY_PLANNER_PACE_GUIDE, DINING_TYPES

        guide = DAY_PLANNER_PACE_GUIDE.get(pace, DAY_PLANNER_PACE_GUIDE["moderate"])

        # Separate attractions from dining
        attractions = []
        dining = []
        for c in candidates:
            entry = {"place_id": c.place_id, "name": c.name, "rating": c.rating,
                     "user_ratings_total": c.user_ratings_total, "types": c.types,
                     "location": {"lat": c.location.lat, "lng": c.location.lng} if c.location else None}
            if set(c.types) & DINING_TYPES:
                dining.append(entry)
            else:
                attractions.append(entry)

        # Format themes
        themes_text = ""
        for day_num, themes in sorted(batch_themes.items()):
            theme_names = ", ".join(t.theme for t in themes)
            themes_text += f"Day {day_num}: {theme_names}\n"

        # Format landmarks
        landmarks_section = ""
        if landmarks:
            lines = ["TOP LANDMARKS (include at least one per batch):"]
            for lm in landmarks[:5]:
                lines.append(f"- {lm.get('name')} ({lm.get('user_ratings_total',0):,} reviews)")
            landmarks_section = "\n".join(lines)

        # Already used
        used_text = ", ".join(already_used) if already_used else "none"

        template = day_plan_prompts.load("day_scout_user")
        return template.format(
            batch_day_numbers=", ".join(str(d) for d in batch_themes.keys()),
            destination=destination,
            batch_themes=themes_text,
            pace=pace,
            activities_per_day=guide["total"],
            landmarks_section=landmarks_section,
            already_used_ids=used_text,
            attractions_json=json.dumps(attractions[:40], indent=2),
            dining_json=json.dumps(dining[:20], indent=2),
            meal_time_guidance=meal_time_guidance,
        )
```

**Step 4:** Run tests, commit.

---

### Task 4: Create Day Reviewer Agent

**Files:**
- Create: `backend/app/agents/day_reviewer.py`
- Create: `backend/app/prompts/day_plan/day_reviewer_system.md`
- Create: `backend/app/prompts/day_plan/day_reviewer_user.md`

**Step 1:** Create `day_reviewer_system.md`:
```markdown
You are a travel itinerary quality reviewer. Score a batch of day plans on 6 dimensions.

## EVALUATION DIMENSIONS (score each 0-100, compute weighted average)

### 1. THEME COVERAGE (30%)
- Does each day cover its assigned theme?
- Are the selected activities relevant to the theme?
- Score 90+: Every day matches theme perfectly
- Score <50: Multiple days ignore their assigned theme

### 2. LANDMARK INCLUSION (20%)
- Are the destination's top-reviewed attractions included in this batch?
- A batch covering 3 days should include at least 1-2 landmarks
- Score 90+: Top landmarks included
- Score <50: All major landmarks absent

### 3. ACTIVITY VARIETY (15%)
- Mix of categories (culture, food, nature, shopping, entertainment)?
- No 3+ consecutive same-category activities within a day
- Score 90+: Great variety
- Score <50: Monotonous days

### 4. DURATION REALISM (15%)
- Theme parks, zoos: 4-8 hours
- Museums: 1-3 hours
- Restaurants: 45-90 minutes
- Quick stops: 15-45 minutes
- Score <50: Major attractions with unrealistic 30-minute visits

### 5. PACING & FLOW (10%)
- Morning: major attraction → midday: lighter activity → lunch → afternoon → dinner
- Not too many heavy activities back-to-back
- Score <50: Exhausting schedule or empty gaps

### 6. MEAL PLACEMENT (10%)
- Each day has lunch (mid-day) and dinner (evening)?
- Both are actual restaurants, not temples or parks?
- Score <50: Missing meals or non-restaurant dining

## OUTPUT
Return ONLY valid JSON:
{
  "score": 75,
  "is_acceptable": true,
  "summary": "Brief assessment",
  "issues": [
    {"severity": "major", "day_number": 3, "category": "theme_coverage", "description": "...", "suggestion": "..."}
  ]
}
```

**Step 2:** Create `day_reviewer_user.md`:
```markdown
Review this batch of day plans for **{destination}**:

**Assigned themes:**
{batch_themes}

**Top landmarks (by visitor reviews):**
{landmarks_section}

**Day plans to review:**
{day_plans_detail}

Score this batch and list specific issues.
Return ONLY the JSON object.
```

**Step 3:** Create `day_reviewer.py`:
```python
import logging
from app.models.day_review import DayReviewResult
from app.prompts.loader import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayReviewerAgent:
    """Reviews a batch of day plans for quality."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def review_batch(
        self,
        day_plans_detail: str,
        batch_themes: str,
        landmarks_section: str,
        destination: str,
    ) -> DayReviewResult:
        system_prompt = day_plan_prompts.load("day_reviewer_system")
        user_prompt = day_plan_prompts.load("day_reviewer_user").format(
            destination=destination,
            batch_themes=batch_themes,
            landmarks_section=landmarks_section,
            day_plans_detail=day_plans_detail,
        )

        result = await self.llm.generate_structured(
            system_prompt, user_prompt, schema=DayReviewResult
        )
        logger.info("[DayReviewer] Batch score: %d (acceptable=%s)", result.score, result.is_acceptable)
        return result
```

**Step 4:** Run tests, commit.

---

### Task 5: Create Day Fixer Agent

**Files:**
- Create: `backend/app/agents/day_fixer.py`
- Create: `backend/app/prompts/day_plan/day_fixer_system.md`
- Create: `backend/app/prompts/day_plan/day_fixer_user.md`

**Step 1:** Create `day_fixer_system.md`:
```markdown
You are a travel itinerary fixer. You receive day plans with quality issues and must fix them.

## RULES
1. Fix each issue by swapping activities, not rewriting entire days
2. Preserve activities that are working well
3. Use the candidate pool to find replacement activities
4. Maintain geographic clustering within each day
5. Keep 2 dining stops per day (lunch + dinner)
6. Selected place_ids MUST come from the candidate lists

## OUTPUT
Return the complete fixed plan in the same JSON format as the original.
```

**Step 2:** Create `day_fixer_user.md`:
```markdown
Fix these day plans for **{destination}**:

**Issues found by reviewer:**
{issues_detail}

**Current plan:**
{current_plan_json}

**Available candidates for swapping:**
{candidates_json}

Fix each issue. Return the complete revised plan as JSON.
```

**Step 3:** Create `day_fixer.py`:
```python
import json
import logging
from app.models.internal import AIPlan
from app.prompts.loader import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayFixerAgent:
    """Fixes day plan quality issues identified by the reviewer."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def fix_batch(
        self,
        current_plan: AIPlan,
        issues: list,
        candidates: list,
        destination: str,
    ) -> AIPlan:
        system_prompt = day_plan_prompts.load("day_fixer_system")

        issues_detail = "\n".join(
            f"- [{i.severity}] Day {i.day_number}: {i.description} → Suggestion: {i.suggestion}"
            for i in issues
        )

        # Slim candidate list for prompt
        candidate_entries = [{"place_id": c.place_id, "name": c.name, "types": c.types,
                              "rating": c.rating} for c in candidates[:30]]

        user_prompt = day_plan_prompts.load("day_fixer_user").format(
            destination=destination,
            issues_detail=issues_detail,
            current_plan_json=json.dumps(current_plan.model_dump(), indent=2),
            candidates_json=json.dumps(candidate_entries, indent=2),
        )

        return await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
```

**Step 4:** Run tests, commit.

---

### Task 6: Wire new agents in dependencies.py

**Files:**
- Modify: `backend/app/dependencies.py`

**Step 1:** Import new agents and create dependency functions:
```python
from app.agents.day_scout import DayScoutAgent
from app.agents.day_reviewer import DayReviewerAgent
from app.agents.day_fixer import DayFixerAgent

def get_day_scout(llm: LLMService = Depends(get_llm_service)) -> DayScoutAgent:
    return DayScoutAgent(llm)

def get_day_reviewer(llm: LLMService = Depends(get_llm_service)) -> DayReviewerAgent:
    return DayReviewerAgent(llm)

def get_day_fixer(llm: LLMService = Depends(get_llm_service)) -> DayFixerAgent:
    return DayFixerAgent(llm)
```

**Step 2:** Update `get_day_plan_orchestrator()` to accept new agents.

**Step 3:** Run tests, commit.

---

### Task 7: Rewrite DayPlanOrchestrator for batched pipeline

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

This is the biggest task. The orchestrator changes from single-shot to batched pipeline.

**Step 1:** Update constructor to accept new agents:
```python
def __init__(self, llm, places, routes, directions=None, weather=None,
             day_scout=None, day_reviewer=None, day_fixer=None):
    self.day_scout = day_scout or DayScoutAgent(llm)
    self.day_reviewer = day_reviewer or DayReviewerAgent(llm)
    self.day_fixer = day_fixer or DayFixerAgent(llm)
    # ... existing init
```

**Step 2:** Add `_plan_city_batched()` method alongside existing flow:
```python
async def _plan_city_batched(self, city, candidates, request, landmarks, ...):
    """Plan a city's days using batched quality pipeline."""
    from app.config.planning import (
        map_themes_to_days, MAX_DAY_PLAN_ITERATIONS,
        MIN_DAY_PLAN_SCORE, DAY_PLAN_BATCH_SIZE,
    )

    # Step 0: Pre-map themes to days
    theme_map = map_themes_to_days(
        city.experience_themes, free_day_count, blocked_days
    )

    # Step 1: Plan in batches
    all_day_groups = []
    planned_ids = set()
    batch_size = DAY_PLAN_BATCH_SIZE

    day_nums = sorted(d for d in range(1, free_day_count + 1) if d not in blocked_days)

    for batch_start in range(0, len(day_nums), batch_size):
        batch = day_nums[batch_start:batch_start + batch_size]
        batch_themes = {d: theme_map.get(d, []) for d in batch}

        # Day Scout
        batch_plan = await self.day_scout.plan_batch(
            candidates=candidates,
            batch_themes=batch_themes,
            destination=city.name,
            pace=request.pace.value,
            landmarks=landmarks,
            already_used=planned_ids,
            ...
        )

        # Quality loop
        for iteration in range(MAX_DAY_PLAN_ITERATIONS):
            # Day Reviewer
            review = await self.day_reviewer.review_batch(...)

            yield ProgressEvent(
                phase="city_start",
                message=f"{city.name}: batch {batch_start//batch_size + 1} review — score {review.score}",
                ...
            )

            if review.is_acceptable or review.score >= MIN_DAY_PLAN_SCORE:
                break

            # Day Fixer
            batch_plan = await self.day_fixer.fix_batch(
                batch_plan, review.issues, candidates, city.name
            )

        all_day_groups.extend(batch_plan.day_groups)
        planned_ids.update(batch_plan.selected_place_ids)

    return all_day_groups
```

**Step 3:** Update `generate_stream()` to use `_plan_city_batched()` when `city.experience_themes` is available, falling back to existing single-shot for backward compat.

**Step 4:** Run tests, commit.

---

### Task 8: Integration test

**Step 1:** Restart server
**Step 2:** Plan Singapore 10-day trip
**Step 3:** Verify:
  - SSE events show batch progress (batch_1_review, batch_2_review, etc.)
  - Each experience_theme gets at least one day
  - Universal Studios / Zoo appear in day plans (from landmark discovery)
  - Quality scores shown per batch
**Step 4:** Final commit

---

## Execution Notes

**Sequential dependencies:**
- Task 1 (model) → Task 4 (reviewer uses model)
- Task 2 (planning config) → Task 7 (orchestrator uses config)
- Tasks 3,4,5 (agents) → Task 6 (wiring) → Task 7 (orchestrator)

**Can parallelize:**
- Batch 1: Tasks 1, 2 (models + config)
- Batch 2: Tasks 3, 4, 5 (agents — independent of each other)
- Batch 3: Tasks 6, 7 (wiring + orchestrator)
- Batch 4: Task 8 (integration test)
