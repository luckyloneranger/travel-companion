# Unified Excursion Day Planning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge excursion and regular day planning into a single Scout → Reviewer → Fixer pipeline so the LLM decides optimal excursion placement and creates coherent multi-day itineraries.

**Architecture:** Move excursion discovery (geocode + discover_places) into the main discovery phase. Tag candidates with `source_destination`. Pass ALL candidates (city + excursion) to a single Day Scout call. Scout decides which day each excursion falls on. Per-day post-processing detects excursion days from Scout output and applies excursion-specific scheduling (transit time, no hotel bookends). Remove the separate excursion planning pipeline entirely.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pytest

---

### Task 1: Add `source_destination` to PlaceCandidate

Tag candidates with where they were discovered so Scout can match candidates to excursion days.

**Files:**
- Modify: `backend/app/models/internal.py:12-33`
- Test: `backend/tests/test_agents.py`

**Step 1: Add field**

In `backend/app/models/internal.py`, add to `PlaceCandidate` (after `serves_dinner` on line 33):

```python
    source_destination: str | None = None  # e.g., "Nikko" — tags where this candidate was discovered
```

**Step 2: Add test**

Add to `backend/tests/test_agents.py`:

```python
class TestPlaceCandidateSourceDestination:
    def test_source_destination_default_none(self):
        from app.models.internal import PlaceCandidate
        from app.models.common import Location
        pc = PlaceCandidate(place_id="p1", name="Test", address="A", location=Location(lat=0, lng=0))
        assert pc.source_destination is None

    def test_source_destination_set(self):
        from app.models.internal import PlaceCandidate
        from app.models.common import Location
        pc = PlaceCandidate(place_id="p1", name="Toshogu", address="Nikko", location=Location(lat=36.7, lng=139.6), source_destination="Nikko")
        assert pc.source_destination == "Nikko"
```

**Step 3: Run tests and commit**

```bash
cd backend && source venv/bin/activate && pytest tests/test_agents.py -v
```

Commit: `feat(models): add source_destination to PlaceCandidate for excursion candidate tagging`

---

### Task 2: Update Day Scout to Handle Excursion Candidates

The Scout prompt and candidate formatting need to distinguish city candidates from excursion candidates and know which themes are excursions.

**Files:**
- Modify: `backend/app/agents/day_scout.py:73-205`
- Modify: `backend/app/prompts/day_plan/day_scout_system.md`
- Modify: `backend/app/prompts/day_plan/day_scout_user.md`

**Step 1: Update day_scout_system.md**

Add a new rule after the existing rules (after Rule 9):

```markdown
10. EXCURSION DAYS: Some themes are marked as excursions with a destination name (e.g., "Day trip to Nikko"). For these days:
   - Use ONLY candidates tagged with that destination (marked with "destination" field in the candidate JSON)
   - Do NOT mix city candidates with excursion candidates on the same day
   - Place excursion days where they create the best geographic and thematic flow (NOT forced to end of stay)
   - Include 2 dining stops from the excursion destination's candidates
```

**Step 2: Update candidate formatting in day_scout.py**

In `_build_user_prompt()`, when building attraction entries (around line 114-124), include the `source_destination` field:

```python
if c.source_destination:
    entry["destination"] = c.source_destination
```

Apply the same to dining entries (around line 132-143).

**Step 3: Update themes section in _build_user_prompt()**

In the themes text building (around line 145-159), add excursion markers:

```python
for day_num, themes in sorted(batch_themes.items()):
    theme_parts = []
    for t in themes:
        label = f"{t.theme} ({t.category})"
        if hasattr(t, 'excursion_type') and t.excursion_type:
            dest = getattr(t, 'destination_name', '') or ''
            label += f" [EXCURSION to {dest}]" if dest else " [EXCURSION]"
        theme_parts.append(label)
    themes_text += f"Day {day_num}: {', '.join(theme_parts)}\n"
```

**Step 4: Run tests and commit**

```bash
cd backend && source venv/bin/activate && pytest -v
```

Commit: `feat(day-scout): handle excursion candidates with destination tagging`

---

### Task 3: Unified Discovery — Move Excursion Discovery into Main Phase

Move excursion geocoding and place discovery from the separate pipeline into Stage 1 of `_process_city()`, running in parallel with city discovery.

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

This is the largest task. The key changes:

**Step 1: In `_process_city()`, replace Stage 0 with parallel excursion discovery**

Currently Stage 0 (lines 760-805) extracts excursions, schedules them to end days, and plans them separately. Replace with:

```python
# Stage 0: Extract excursion info (keep) but DON'T plan them separately
excursions = self._extract_excursions(city.highlights, experience_themes=city.experience_themes)
excursion_locations: dict[str, tuple[Location, ExperienceTheme]] = {}

if excursions:
    # Geocode all excursion destinations in parallel
    geocode_tasks = []
    for exc in excursions:
        geocode_name = getattr(exc, 'destination_name', None) or exc.name
        geocode_tasks.append(self._geocode_excursion(geocode_name, city.country))

    geocode_results = await asyncio.gather(*geocode_tasks, return_exceptions=True)

    for exc, result in zip(excursions, geocode_results):
        if isinstance(result, Exception) or result is None:
            logger.warning("[DayPlan] Failed to geocode excursion %s", exc.name)
            continue
        geocode_name = getattr(exc, 'destination_name', None) or exc.name
        excursion_locations[geocode_name] = (result, exc)
```

Add a helper method `_geocode_excursion()` that wraps the existing geocoding logic from `_plan_single_excursion` lines 232-239.

**Step 2: In Stage 1 (Discovery), discover excursion places in parallel with city places**

After the existing city discovery (line 824-827), add excursion discovery:

```python
# Discover places at excursion destinations in parallel with city discovery
exc_discovery_tasks = []
for dest_name, (dest_location, exc_theme) in excursion_locations.items():
    exc_discovery_tasks.append(
        self._discover_excursion_places(dest_name, dest_location, request.interests)
    )

# Run city + excursion discovery in parallel
if exc_discovery_tasks:
    exc_results = await asyncio.gather(*exc_discovery_tasks, return_exceptions=True)
    for (dest_name, _), result in zip(excursion_locations.items(), exc_results):
        if isinstance(result, list):
            # Tag all excursion candidates with source_destination
            for c in result:
                c.source_destination = dest_name
            candidates.extend(result)
```

Add helper `_discover_excursion_places()` — extracted from `_plan_single_excursion` lines 261-305.

**Step 3: Remove blocked_days/partial_days computation**

Remove:
- `_compute_excursion_schedule()` call (line 771)
- `blocked_days` / `partial_days` variables
- The separate `_plan_excursion_days()` call (line 780-785)
- The early exit `if free_day_count <= 0` (line 793-805)
- The merge at the end `if excursion_plans: city_plans.extend(...)` (line 1271-1274)

**Step 4: Update `_plan_city_batched()` — remove blocked_days parameter**

The Scout now plans ALL days, no blocked days. Update the signature and internal logic:

- Remove `blocked_days` parameter
- `map_themes_to_days()` receives ALL themes (including excursion themes) with no blocked days
- `free_day_nums` becomes `all_day_nums` = range(1, num_days + 1)

**Step 5: Update per-day post-processing to detect excursion days**

In Stage 4 (per-day processing), after TSP + Schedule, detect if the day is an excursion based on the Scout's output:

```python
# Detect if this day is an excursion (candidates have source_destination)
day_candidate_destinations = set(
    c.source_destination for c in day_candidates
    if c.source_destination
)
is_excursion_day = len(day_candidate_destinations) > 0
excursion_dest = next(iter(day_candidate_destinations)) if is_excursion_day else None

if is_excursion_day and excursion_dest:
    # Use excursion location for TSP center instead of hotel
    exc_location = excursion_locations[excursion_dest][0]
    start_location_for_day = exc_location

    # Compute transit time for adjusted schedule
    exc_theme = excursion_locations[excursion_dest][1]
    dist_km = getattr(exc_theme, 'distance_from_city_km', None) or 50
    transit_hours = max(0.5, dist_km / 50)
    day_start_time = time(int(9 + transit_hours), int((transit_hours % 1) * 60))
    day_end_time = time(int(21 - transit_hours), 0)
else:
    start_location_for_day = hotel_location
    # normal day_start/end times
```

Skip hotel bookends for excursion days (already done — just use `is_excursion_day` flag).

Set `is_excursion=True` and `excursion_name` on the DayPlan for excursion days.

**Step 6: Run tests**

```bash
cd backend && source venv/bin/activate && pytest -v
```

Commit: `feat(day-plan): unify excursion and regular day planning into single pipeline`

---

### Task 4: Update `map_themes_to_days()` — No More Blocked Days

The theme mapping function currently separates excursion themes and assigns them to blocked days. Now the LLM decides placement, so all themes (including excursions) compete for any day.

**Files:**
- Modify: `backend/app/config/planning.py:342-400`
- Test: `backend/tests/test_scheduler.py`

**Step 1: Simplify map_themes_to_days**

Remove the `blocked_days` parameter. All themes (regular, excursion, evening) are spread across all days. The LLM Scout will respect excursion markers to place them intelligently.

Update the function to:
1. Spread ALL themes (including excursion) across all days evenly
2. Evening themes still pair with least-loaded days
3. No special blocked_days handling

**Step 2: Add tests**

```python
class TestMapThemesToDaysUnified:
    def test_excursion_themes_mixed_with_regular(self):
        from app.config.planning import map_themes_to_days
        from app.models.journey import ExperienceTheme
        themes = [
            ExperienceTheme(theme="Temples", category="religious"),
            ExperienceTheme(theme="Nikko day trip", category="excursion", excursion_type="full_day", destination_name="Nikko"),
            ExperienceTheme(theme="Food tour", category="food"),
        ]
        result = map_themes_to_days(themes, 3)
        # All 3 days should have themes, excursion NOT forced to end
        assert len(result) == 3
        assert all(len(v) > 0 for v in result.values())

    def test_no_blocked_days_concept(self):
        from app.config.planning import map_themes_to_days
        from app.models.journey import ExperienceTheme
        themes = [
            ExperienceTheme(theme="A", category="culture"),
            ExperienceTheme(theme="B", category="nature"),
        ]
        # No blocked_days parameter needed
        result = map_themes_to_days(themes, 2)
        assert 1 in result and 2 in result
```

**Step 3: Run tests and commit**

```bash
cd backend && source venv/bin/activate && pytest -v
```

Commit: `refactor(planning): simplify theme mapping — excursion themes compete for any day`

---

### Task 5: Clean Up — Remove Separate Excursion Pipeline Functions

Remove the now-unused excursion planning functions from the orchestrator.

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

**Step 1: Remove these functions entirely:**
- `_plan_excursion_days()` (lines 155-198)
- `_plan_single_excursion()` (lines 200-551)
- `_compute_excursion_schedule()` (lines 554-605)
- `_build_excursion_day_plan()` (lines 104-153)

Keep `_extract_excursions()` (still needed to identify which themes are excursions for geocoding).

**Step 2: Extract helper methods from removed code**

Create small focused helpers from the code that was inside `_plan_single_excursion`:
- `_geocode_excursion(name, country)` — geocoding logic (extracted in Task 3)
- `_discover_excursion_places(dest_name, location, interests)` — discovery logic (extracted in Task 3)

These should already exist from Task 3. Verify they work.

**Step 3: Run tests and commit**

```bash
cd backend && source venv/bin/activate && pytest -v
```

Commit: `refactor(day-plan): remove separate excursion planning pipeline`

---

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the day plan pipeline description**

In the Orchestrators section, update the `day_plan.py` description to reflect the unified pipeline:

Replace mention of "Excursion days also processed in parallel via gather" with:
"Excursion days planned alongside regular days in a single Scout → Reviewer → Fixer pass. Excursion candidates are tagged with `source_destination` and the Scout decides optimal day placement. Per-day post-processing detects excursion days and applies transit-adjusted scheduling."

In Design Principles, update the excursion-related text:
"All days (regular + excursion) planned in a single Day Scout call — LLM decides optimal excursion placement based on geographic and thematic flow. Excursion candidates tagged with `source_destination` field to prevent city/excursion candidate mixing."

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document unified excursion day planning pipeline"
```

---

## Summary

| Task | Files | Complexity | Key Change |
|------|-------|------------|------------|
| 1. PlaceCandidate tag | `internal.py` | Small | Add `source_destination` field |
| 2. Scout excursion awareness | `day_scout.py`, prompts | Medium | Tag candidates, mark excursion themes |
| 3. Unified discovery + planning | `day_plan.py` | **Large** | Move excursion discovery into main phase, single Scout call |
| 4. Theme mapping simplification | `planning.py` | Medium | Remove blocked_days, spread all themes |
| 5. Remove old pipeline | `day_plan.py` | Medium | Delete 4 functions (~450 lines) |
| 6. CLAUDE.md | `CLAUDE.md` | Small | Document changes |

**Tasks 3 + 5 are the core refactor. Task 3 is the largest — it rebuilds `_process_city()` to use a single pipeline.**

**Execution order:** 1 → 2 → 4 → 3 → 5 → 6 (4 before 3 because theme mapping must be ready before the orchestrator uses it)
