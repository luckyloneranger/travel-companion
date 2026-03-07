# Pipeline Cleanup Sprint — Design & Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 10 systemic issues found in holistic pipeline audit — prompt bloat, data model debt, silent failures, weak day quality loop. Root cause fixes, not patches.

**Architecture:** Simplify Scout prompt (200→100 lines), unify data model (remove highlights, experience_themes only), add dimension_scores to day review loop, pre-filter candidates per theme, raise errors instead of silent degradation.

**Tech Stack:** Python (Pydantic v2, FastAPI), Markdown prompts

---

### Task 1: Raise error on missing accommodation instead of placeholder

**Files:**
- Modify: `backend/app/agents/scout.py`

**Change:** In `_validate_plan()`, replace the placeholder accommodation creation with `LLMValidationError`:

Replace:
```python
city.accommodation = Accommodation(name=f"Hotel in {city.name}", estimated_nightly_usd=100)
```

With:
```python
raise LLMValidationError(
    "JourneyPlan",
    [f"City '{city.name}' has no accommodation. Each city MUST have a hotel suggestion."],
    1,
)
```

This forces the LLM to retry instead of producing fake data.

**Verify:** `pytest -q --tb=short` — tests may need updating if they test the placeholder path.

---

### Task 2: Raise error on null-island geocoding instead of silently skipping

**Files:**
- Modify: `backend/app/agents/enricher.py`
- Modify: `backend/app/orchestrators/day_plan.py`

**Change in enricher.py:** After null-island detection, log ERROR not just warning:
```python
logger.error("[Enricher] CRITICAL: City %s geocoded to null-island (0,0) — city will have no day plans", city.name)
```

**Change in day_plan.py:** When `city.location is None`, yield a more visible progress event:
```python
yield ProgressEvent(
    phase="city_complete",
    message=f"{city_name}: could not locate on map — try a different spelling",
    ...
)
```

This ensures the user sees the issue in the frontend progress stream.

---

### Task 3: Add dimension_scores to DayReviewResult

**Files:**
- Modify: `backend/app/models/day_review.py`
- Modify: `backend/app/prompts/day_plan/day_reviewer_system.md`
- Modify: `backend/app/prompts/day_plan/day_reviewer_user.md`

**Change in day_review.py:** Add dimension_scores field:
```python
class DayReviewResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    is_acceptable: bool
    dimension_scores: dict[str, int] = {}  # NEW
    issues: list[DayReviewIssue] = []
    summary: str = ""
```

**Change in day_reviewer_system.md:** Update OUTPUT section to include dimension_scores:
```json
{
  "score": 75,
  "is_acceptable": true,
  "dimension_scores": {
    "theme_coverage": 80,
    "landmark_inclusion": 60,
    "activity_variety": 90,
    "duration_realism": 85,
    "pacing_flow": 75,
    "meal_placement": 70,
    "activity_count": 90
  },
  "summary": "...",
  "issues": [...]
}
```

---

### Task 4: Unify to experience_themes — remove highlights conditional logic

**Files:**
- Modify: `backend/app/agents/reviewer.py` — remove `elif city.highlights:` branch
- Modify: `backend/app/agents/planner.py` — remove `elif city.highlights:` branch
- Modify: `backend/app/agents/scout.py` — remove `if not city.experience_themes and not city.highlights:` dual check
- Modify: `backend/app/orchestrators/day_plan.py` — remove highlights fallback in `_extract_excursions()`
- Keep `highlights` on model for backward compat with stored trips

**Key change:** All agents read ONLY from `experience_themes`. If a stored trip has only `highlights`, the trip loading code should convert them to `experience_themes` on the fly.

Add conversion in `backend/app/db/repository.py` or `tripStore`:
```python
# When loading a trip, if experience_themes is empty but highlights exist, convert
if not city.experience_themes and city.highlights:
    city.experience_themes = [
        ExperienceTheme(theme=h.name, category=h.category or "culture", why=h.description or "",
                        excursion_type=h.excursion_type, excursion_days=h.excursion_days)
        for h in city.highlights
    ]
```

---

### Task 5: Simplify Scout prompt — move safety/visa/altitude to Reviewer

**Files:**
- Modify: `backend/app/prompts/journey/scout_system.md`
- Modify: `backend/app/prompts/journey/reviewer_system.md`

**Change in scout_system.md:** Remove these sections (move to Reviewer):
- Section 7a (VISA & ENTRY REQUIREMENTS) — 6 lines
- Altitude acclimatization details — 3 lines
- Solo/female traveler safety details — 4 lines
- Island transport detailed rules — 5 lines

Replace with ONE line each:
```
- Flag visa requirements in travel_leg notes
- Flag altitude risks (>3000m) in experience_themes
- Consider traveler safety in best_time_to_visit
```

**Change in reviewer_system.md:** The SEASONAL & SAFETY CHECK section already covers these. Just ensure it has enough detail.

**Target:** Scout prompt from ~200 lines to ~120 lines.

---

### Task 6: Add city-state collapse to Planner

**Files:**
- Modify: `backend/app/agents/planner.py`

**Change:** Import and call `_collapse_city_state_destinations` from Scout (or duplicate the logic):

```python
from app.agents.scout import ScoutAgent

# In fix_plan(), after LLM returns the fixed plan:
ScoutAgent._collapse_city_state_destinations(plan)
```

Since it's a `@classmethod`, this works without instantiation.

---

### Task 7: Pre-filter candidates per theme for Day Scout

**Files:**
- Modify: `backend/app/agents/day_scout.py`

**Change in `_build_user_prompt()`:** Instead of sending ALL 40+ attractions to Day Scout, filter to ~15 most relevant per batch:

```python
# Filter candidates by theme relevance
batch_theme_keywords = set()
for themes in batch_themes.values():
    for t in themes:
        batch_theme_keywords.update(t.theme.lower().split())
        if hasattr(t, 'category'):
            batch_theme_keywords.add(t.category.lower())

# Score candidates by theme relevance
scored = []
for c in candidates:
    score = 0
    name_lower = c.name.lower()
    types_str = " ".join(c.types).lower()
    for kw in batch_theme_keywords:
        if kw in name_lower or kw in types_str:
            score += 1
    # Landmarks always get max score
    if any(c.name == lm.get('name') for lm in (landmarks or [])):
        score += 100
    scored.append((score, c))

scored.sort(key=lambda x: (-x[0], -(x[1].user_ratings_total or 0)))
filtered_attractions = [c for _, c in scored if not (set(c.types) & DINING_TYPES)][:20]
```

This ensures landmarks are always at the top and theme-relevant candidates are prioritized.

---

### Task 8: Cache landmark discovery per city

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

**Change:** Add a `_landmark_cache` dict to the orchestrator:

```python
def __init__(self, ...):
    ...
    self._landmark_cache: dict[str, list[dict]] = {}
```

Before calling `discover_landmarks()`, check cache:
```python
if city_name in self._landmark_cache:
    city_landmarks = self._landmark_cache[city_name]
else:
    city_landmarks = await self.places.discover_landmarks(city_name)
    self._landmark_cache[city_name] = city_landmarks
```

---

### Task 9: Validate transport modes against regional reality

**Files:**
- Modify: `backend/app/agents/enricher.py`

**Change:** After enriching a travel leg, if transit API returned ZERO_RESULTS for the Scout's suggested mode, log a warning:

```python
if leg.mode in (TransportMode.TRAIN, TransportMode.BUS, TransportMode.FERRY):
    if not best_transit:
        logger.warning(
            "[Enricher] No %s service found for %s → %s — mode may not exist",
            leg.mode.value, leg.from_city, leg.to_city,
        )
```

This is informational — doesn't reject, just creates an audit trail.

---

### Task 10: Day planner validates dining as error, not warning

**Files:**
- Modify: `backend/app/agents/day_planner.py`

**Change:** In `_validate_ai_plan()`, change the dining warning to an error:

```python
if day_dining_count < 2:
    raise LLMValidationError(
        "AIPlan",
        [f"Day {i+1} ({group.theme}) has only {day_dining_count} dining places (need 2)"],
        1,
    )
```

This triggers a retry instead of proceeding with missing meals.

---

## Execution Notes

**Batch 1** (Tasks 1-3): Critical fixes — errors not placeholders, dimension_scores
**Batch 2** (Tasks 4-5): Data model + prompt cleanup — biggest impact
**Batch 3** (Tasks 6-8): Pipeline improvements — collapse, filtering, caching
**Batch 4** (Tasks 9-10): Validation — transport modes, dining errors

All tasks are independent except Task 4 (unify model) affects how Tasks 5-7 read data.

## Verification
```bash
cd backend && ./venv/bin/python -m pytest -q --tb=short  # 199 tests
cd frontend && npx tsc --noEmit && npm run build          # TS clean
# Curl test: Singapore 10d, Greece 7d, Peru 10d
```
