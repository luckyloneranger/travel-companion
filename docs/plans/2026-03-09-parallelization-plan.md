# Day Plan Pipeline Parallelization — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Parallelize the day plan pipeline at three levels (cities, excursions, landmark searches) to reduce total time from 10-17 min to 5-8 min for a typical 3-city trip.

**Architecture:** Queue + Semaphore pattern for city-level parallelism; asyncio.gather() for excursion-level and landmark-search-level parallelism. No cross-city dedup. Interleaved SSE events. Retry once on city failure, then `city_error` SSE event → frontend toast.

**Tech Stack:** Python asyncio (Queue, Semaphore, gather), FastAPI SSE streaming, React hook + toast

---

### Task 1: Add MAX_CONCURRENT_CITIES configuration

**Files:**
- Modify: `backend/app/config/planning.py:22` (after `DAY_PLAN_BATCH_SIZE`)
- Modify: `backend/app/config/settings.py:62` (after rate limit settings)

**Step 1: Add constant to planning.py**

In `backend/app/config/planning.py`, after line 22 (`DAY_PLAN_BATCH_SIZE: int = 3`), add:

```python
MAX_CONCURRENT_CITIES: int = 3
```

**Step 2: Add settings field to settings.py**

In `backend/app/config/settings.py`, after line 62 (`rate_limit_tips_window_seconds`), add:

```python
    # Parallelization
    max_concurrent_cities: int = 3
```

**Step 3: Run tests to verify no breakage**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: All 207 tests pass.

**Step 4: Commit**

```bash
git add backend/app/config/planning.py backend/app/config/settings.py
git commit -m "feat: add MAX_CONCURRENT_CITIES config for parallel day planning"
```

---

### Task 2: Parallelize landmark text searches (Level 3)

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py:719-728` (city landmark searches)
- Modify: `backend/app/orchestrators/day_plan.py:737-752` (theme-based discovery)
- Modify: `backend/app/orchestrators/day_plan.py:252-267` (excursion landmark searches)

**Step 1: Write tests for parallel landmark search**

In `backend/tests/test_agents.py`, add at end of file (after line 756):

```python
class TestParallelLandmarkSearch:
    """Landmark text searches should run in parallel via asyncio.gather."""

    @pytest.mark.asyncio
    async def test_landmark_searches_deduplicate(self):
        """Parallel landmark searches should still deduplicate by place_id."""
        from app.orchestrators.day_plan import DayPlanOrchestrator

        # Two landmarks, one returns a duplicate place_id
        mock_places = AsyncMock()
        mock_places.text_search_places = AsyncMock(side_effect=[
            [PlaceCandidate(place_id="p1", name="Temple A", location=Location(lat=35, lng=139), types=[])],
            [PlaceCandidate(place_id="p1", name="Temple A duplicate", location=Location(lat=35, lng=139), types=[])],
            [PlaceCandidate(place_id="p2", name="Shrine B", location=Location(lat=35.1, lng=139.1), types=[])],
        ])

        candidates = []
        existing_ids = set()
        city_landmarks = [{"name": "Temple A"}, {"name": "Temple A alt"}, {"name": "Shrine B"}]
        city_name = "Kyoto"
        location = Location(lat=35, lng=139)

        # Simulate the parallel landmark search logic
        async def _search_landmark(lm_name: str):
            try:
                return await mock_places.text_search_places(
                    query=f"{lm_name} {city_name}",
                    location=location,
                    max_results=1,
                )
            except Exception:
                return []

        import asyncio
        lm_results_all = await asyncio.gather(
            *(_search_landmark(lm["name"]) for lm in city_landmarks)
        )
        for lm_results in lm_results_all:
            for lc in lm_results:
                if lc.place_id not in existing_ids:
                    candidates.append(lc)
                    existing_ids.add(lc.place_id)

        # Should have 2 unique candidates (p1 and p2), not 3
        assert len(candidates) == 2
        assert {c.place_id for c in candidates} == {"p1", "p2"}
```

**Step 2: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_agents.py::TestParallelLandmarkSearch -v`
Expected: PASS (test validates gather + dedup logic standalone)

**Step 3: Parallelize city landmark searches in generate_stream()**

In `backend/app/orchestrators/day_plan.py`, replace the sequential landmark for-loop (lines 718-728):

```python
                    # BEFORE (lines 718-728):
                    if city_landmarks:
                        existing_ids = {c.place_id for c in candidates}
                        for lm in city_landmarks:
                            lm_results = await self.places.text_search_places(
                                query=lm["name"] + " " + city_name,
                                location=city.location,
                                max_results=1,
                            )
                            for lc in lm_results:
                                if lc.place_id not in existing_ids:
                                    candidates.append(lc)
                                    existing_ids.add(lc.place_id)
```

With:

```python
                    if city_landmarks:
                        existing_ids = {c.place_id for c in candidates}

                        async def _search_lm(lm_name: str):
                            try:
                                return await self.places.text_search_places(
                                    query=f"{lm_name} {city_name}",
                                    location=city.location,
                                    max_results=1,
                                )
                            except Exception:
                                return []

                        lm_results_all = await asyncio.gather(
                            *(_search_lm(lm["name"]) for lm in city_landmarks)
                        )
                        for lm_results in lm_results_all:
                            for lc in lm_results:
                                if lc.place_id not in existing_ids:
                                    candidates.append(lc)
                                    existing_ids.add(lc.place_id)
```

**Step 4: Parallelize theme-based discovery**

In the same file, replace the sequential theme search (lines 737-752):

```python
                # BEFORE (lines 737-752):
                if city.experience_themes:
                    existing_ids = {c.place_id for c in candidates}
                    for et in city.experience_themes:
                        if et.distance_from_city_km and et.distance_from_city_km > 20:
                            try:
                                theme_results = await self.places.text_search_places(
                                    query=f"{et.theme} near {city_name}",
                                    location=city.location,
                                    max_results=3,
                                )
                                for tr in theme_results:
                                    if tr.place_id not in existing_ids:
                                        candidates.append(tr)
                                        existing_ids.add(tr.place_id)
                            except Exception:
                                pass
```

With:

```python
                if city.experience_themes:
                    existing_ids = {c.place_id for c in candidates}
                    far_themes = [
                        et for et in city.experience_themes
                        if et.distance_from_city_km and et.distance_from_city_km > 20
                    ]
                    if far_themes:
                        async def _search_theme(theme_name: str):
                            try:
                                return await self.places.text_search_places(
                                    query=f"{theme_name} near {city_name}",
                                    location=city.location,
                                    max_results=3,
                                )
                            except Exception:
                                return []

                        theme_results_all = await asyncio.gather(
                            *(_search_theme(et.theme) for et in far_themes)
                        )
                        for theme_results in theme_results_all:
                            for tr in theme_results:
                                if tr.place_id not in existing_ids:
                                    candidates.append(tr)
                                    existing_ids.add(tr.place_id)
```

**Step 5: Parallelize excursion landmark searches**

In `_plan_excursion_days()`, replace the sequential excursion landmark loop (lines 252-267):

```python
                    # BEFORE (lines 250-267):
                    if exc_landmarks:
                        existing_ids = {c.place_id for c in exc_candidates}
                        for lm in exc_landmarks[:7]:
                            lm_name = lm.get("name", "")
                            if not lm_name:
                                continue
                            try:
                                lm_results = await self.places.text_search_places(
                                    query=f"{lm_name} {geocode_name}",
                                    location=exc_location,
                                    max_results=1,
                                )
                                for lc in lm_results:
                                    if lc.place_id not in existing_ids:
                                        exc_candidates.append(lc)
                                        existing_ids.add(lc.place_id)
                            except Exception:
                                pass
```

With:

```python
                    if exc_landmarks:
                        existing_ids = {c.place_id for c in exc_candidates}
                        valid_landmarks = [lm for lm in exc_landmarks[:7] if lm.get("name")]

                        async def _search_exc_lm(lm_name: str):
                            try:
                                return await self.places.text_search_places(
                                    query=f"{lm_name} {geocode_name}",
                                    location=exc_location,
                                    max_results=1,
                                )
                            except Exception:
                                return []

                        exc_lm_results = await asyncio.gather(
                            *(_search_exc_lm(lm["name"]) for lm in valid_landmarks)
                        )
                        for lm_results in exc_lm_results:
                            for lc in lm_results:
                                if lc.place_id not in existing_ids:
                                    exc_candidates.append(lc)
                                    existing_ids.add(lc.place_id)
```

**Step 6: Run all tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: All 207+ tests pass.

**Step 7: Commit**

```bash
git add backend/app/orchestrators/day_plan.py backend/tests/test_agents.py
git commit -m "perf: parallelize landmark and theme text searches via asyncio.gather"
```

---

### Task 3: Parallelize excursion processing (Level 2)

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py:155-518` (refactor `_plan_excursion_days()`)

**Step 1: Write test for parallel excursion processing**

In `backend/tests/test_agents.py`, add after `TestParallelLandmarkSearch`:

```python
class TestParallelExcursionProcessing:
    """Excursion days should process in parallel via asyncio.gather."""

    @pytest.mark.asyncio
    async def test_excursion_grouping(self):
        """Independent excursions should be grouped correctly for parallel processing."""
        from app.models.journey import CityHighlight

        excursions_by_day = {
            0: CityHighlight(name="Nikko", excursion_type="full_day"),
            2: CityHighlight(name="Hakone", excursion_type="full_day"),
        }

        # Group by name (each unique name = independent group)
        exc_groups = {}
        for day_idx, exc in sorted(excursions_by_day.items()):
            key = exc.name
            if key not in exc_groups:
                exc_groups[key] = (exc, [])
            exc_groups[key][1].append(day_idx)

        assert len(exc_groups) == 2
        assert exc_groups["Nikko"][1] == [0]
        assert exc_groups["Hakone"][1] == [2]

    @pytest.mark.asyncio
    async def test_multi_day_excursion_grouped_together(self):
        """Multi-day excursions sharing same object should form one group."""
        from app.models.journey import CityHighlight

        shared_exc = CityHighlight(name="Ha Long Bay", excursion_type="multi_day", excursion_days=2)
        excursions_by_day = {
            3: shared_exc,
            4: shared_exc,
        }

        exc_groups = {}
        for day_idx, exc in sorted(excursions_by_day.items()):
            key = exc.name
            if key not in exc_groups:
                exc_groups[key] = (exc, [])
            exc_groups[key][1].append(day_idx)

        assert len(exc_groups) == 1
        assert exc_groups["Ha Long Bay"][1] == [3, 4]
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agents.py::TestParallelExcursionProcessing -v`
Expected: PASS

**Step 3: Extract `_plan_single_excursion()` from `_plan_excursion_days()`**

Refactor `_plan_excursion_days()` (lines 155-518) by:

1. Creating a new method `_plan_single_excursion(self, exc, exc_day_indices, city, request, day_offset)` that contains the body of the current for-loop (lines 202-516). This method processes one excursion group and returns `list[DayPlan]`.

2. Rewriting `_plan_excursion_days()` to:
   - Group excursions by name (multi-day shares same name → one group)
   - Use `asyncio.gather()` to process all groups in parallel
   - Merge results, using fallback stubs for failures

```python
    async def _plan_single_excursion(
        self,
        exc: CityHighlight,
        exc_day_indices: list[int],
        city: "CityStop",
        request: "TripRequest",
        day_offset: int,
    ) -> list["DayPlan"]:
        """Process a single excursion group (geocode → discover → scout → quality → routes).

        Returns list of DayPlan objects, one per day in exc_day_indices.
        """
        # ... lines 202-516 of current _plan_excursion_days, extracted verbatim ...
        # All references to `planned` become local `result: list[DayPlan] = []`
        # Uses `result.append(...)` and `return result` at the end

    async def _plan_excursion_days(
        self,
        excursions_by_day: dict[int, CityHighlight],
        city: "CityStop",
        request: "TripRequest",
        day_offset: int,
    ) -> list["DayPlan"]:
        """Plan excursion days in parallel."""
        from app.config.planning import MAX_DAY_PLAN_ITERATIONS, MIN_DAY_PLAN_SCORE
        from app.agents.day_planner import _build_meal_time_guidance
        from app.models.internal import AIPlan

        # Group excursions by name (multi-day → single group)
        exc_groups: dict[str, tuple[CityHighlight, list[int]]] = {}
        for day_idx, exc in sorted(excursions_by_day.items()):
            key = exc.name
            if key not in exc_groups:
                exc_groups[key] = (exc, [])
            exc_groups[key][1].append(day_idx)

        # Process all excursion groups in parallel
        tasks = [
            self._plan_single_excursion(exc, days, city, request, day_offset)
            for exc, days in exc_groups.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results, build fallback stubs for failures
        planned: list[DayPlan] = []
        group_items = list(exc_groups.values())
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                exc, days = group_items[i]
                logger.error(
                    "[DayPlanOrchestrator] Excursion %r failed: %s", exc.name, r,
                )
                for di in days:
                    schedule_date = request.start_date + timedelta(days=day_offset + di)
                    planned.append(self._build_excursion_day_plan(
                        excursion=exc,
                        date_str=str(schedule_date),
                        day_number=day_offset + di + 1,
                        city_name=city.name,
                    ))
            else:
                planned.extend(r)

        return planned
```

**Step 4: Run all tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add backend/app/orchestrators/day_plan.py backend/tests/test_agents.py
git commit -m "perf: parallelize excursion day processing via asyncio.gather"
```

---

### Task 4: Parallelize city processing (Level 1) — extract `_process_city()`

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py:574-1149` (refactor `generate_stream()`)

This is the largest task. Split into two steps: first extract `_process_city()`, then rewrite `generate_stream()`.

**Step 1: Extract `_process_city()` method**

Create a new async method `_process_city()` containing the body of the current `for city_idx, city in enumerate(journey.cities)` loop (lines 596-1128).

Signature:
```python
    async def _process_city(
        self,
        city_idx: int,
        city: "CityStop",
        journey: JourneyPlan,
        request: TripRequest,
        event_queue: "asyncio.Queue[ProgressEvent | None]",
        total_cities: int,
    ) -> list[DayPlan]:
```

Key changes from the loop body:
- Compute `day_offset = sum(journey.cities[i].days for i in range(city_idx))` (no shared state)
- Each city gets its own `_route_cache: dict[tuple, Route] = {}` (local, not `self._route_cache`)
- Replace all `yield ProgressEvent(...)` with `await event_queue.put(ProgressEvent(...))`
- Replace all `all_plans.extend(...)` / `all_plans` with local `city_plans` list
- Replace all `continue` (which skipped to next city) with `return city_plans`
- Replace `day_offset += city.days` lines with nothing (computed at top)

**Step 2: Rewrite `generate_stream()` to use Queue + Semaphore**

Replace the current `generate_stream()` (lines 574-1149) with:

```python
    async def generate_stream(
        self,
        journey: JourneyPlan,
        request: TripRequest,
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Generate day plans for all cities in the journey, processing cities in parallel."""
        from app.config.settings import get_settings

        event_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        total_cities = len(journey.cities)
        max_concurrent = get_settings().max_concurrent_cities

        async def _run_all_cities():
            sem = asyncio.Semaphore(max_concurrent)

            async def _bounded_city(city_idx: int, city):
                async with sem:
                    return await self._process_city(
                        city_idx, city, journey, request,
                        event_queue, total_cities,
                    )

            results = await asyncio.gather(
                *(_bounded_city(i, c) for i, c in enumerate(journey.cities)),
                return_exceptions=True,
            )
            await event_queue.put(None)  # Sentinel
            return results

        try:
            producer = asyncio.create_task(_run_all_cities())

            # Stream events in real-time as cities produce them
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event

            # Collect results, retry failures once
            results = await producer
            all_plans: list[DayPlan] = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    city = journey.cities[i]
                    logger.error(
                        "[DayPlanOrchestrator] City %s failed: %s",
                        city.name, r,
                    )
                    # Retry once
                    try:
                        retry_plans = await self._process_city(
                            i, city, journey, request,
                            event_queue, total_cities,
                        )
                        all_plans.extend(retry_plans)
                    except Exception as e2:
                        logger.error(
                            "[DayPlanOrchestrator] City %s retry failed: %s",
                            city.name, e2,
                        )
                        yield ProgressEvent(
                            phase="city_error",
                            message=f"Failed to plan {city.name}. You can regenerate day plans to try again.",
                            data={"city": city.name},
                        )
                else:
                    all_plans.extend(r)

            # Drain any retry progress events
            while not event_queue.empty():
                event = await event_queue.get()
                if event is not None:
                    yield event

            all_plans.sort(key=lambda dp: dp.day_number)

            yield ProgressEvent(
                phase="complete",
                message="All day plans generated",
                progress=100,
                data={
                    "day_plans": [dp.model_dump() for dp in all_plans],
                },
            )

        except Exception as exc:
            logger.error(
                "[DayPlanOrchestrator] Unexpected error: %s", exc, exc_info=True
            )
            yield ProgressEvent(
                phase="error",
                message=f"Day plan generation failed: {exc}",
                progress=0,
                data=None,
            )
```

**Step 3: Run all tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add backend/app/orchestrators/day_plan.py
git commit -m "perf: parallelize city processing via Queue + Semaphore

Cities now process concurrently (bounded by MAX_CONCURRENT_CITIES).
Each city pushes SSE events to a shared queue for real-time streaming.
Failed cities retry once; if still failing, emit city_error event."
```

---

### Task 5: Frontend — handle `city_error` SSE event

**Files:**
- Modify: `frontend/src/hooks/useStreamingDayPlans.ts:54-62`

**Step 1: Add city_error handling**

In `frontend/src/hooks/useStreamingDayPlans.ts`, add after line 58 (after the `complete` block) and before line 60 (the `error` block):

```typescript
        if (event.phase === 'city_error') {
          const { showToast } = await import('@/components/ui/toast');
          showToast(event.message, 'error');
        }
```

Note: Use dynamic import to avoid adding showToast to the hook's top-level imports if it's not already imported.

Alternatively, add a static import at the top of the file:
```typescript
import { showToast } from '@/components/ui/toast';
```
And inline:
```typescript
        if (event.phase === 'city_error') {
          showToast(event.message, 'error');
        }
```

**Step 2: Build to verify no TypeScript errors**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add frontend/src/hooks/useStreamingDayPlans.ts
git commit -m "feat: show toast notification when city day plan generation fails"
```

---

### Task 6: Add comprehensive parallelization tests

**Files:**
- Modify: `backend/tests/test_agents.py` (add new test class)

**Step 1: Add tests for city-level parallelism**

Add to `backend/tests/test_agents.py`:

```python
class TestCityParallelism:
    """City-level parallel processing via Queue + Semaphore."""

    @pytest.mark.asyncio
    async def test_day_offset_computed_from_city_index(self):
        """Each city computes its own day_offset without shared state."""
        journey = _make_journey_plan()
        # Rome = 3 days, Florence = 2 days
        # Rome day_offset = 0, Florence day_offset = 3
        day_offset_0 = sum(journey.cities[i].days for i in range(0))
        day_offset_1 = sum(journey.cities[i].days for i in range(1))
        assert day_offset_0 == 0
        assert day_offset_1 == 3

    @pytest.mark.asyncio
    async def test_max_concurrent_cities_config_exists(self):
        """MAX_CONCURRENT_CITIES should be importable from planning config."""
        from app.config.planning import MAX_CONCURRENT_CITIES
        assert isinstance(MAX_CONCURRENT_CITIES, int)
        assert MAX_CONCURRENT_CITIES > 0

    @pytest.mark.asyncio
    async def test_settings_max_concurrent_cities(self):
        """Settings should expose max_concurrent_cities field."""
        from app.config.settings import Settings
        s = Settings(
            max_concurrent_cities=2,
            database_url="postgresql+asyncpg://localhost/test",
        )
        assert s.max_concurrent_cities == 2
```

**Step 2: Run all tests**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/tests/test_agents.py
git commit -m "test: add parallelization config and day_offset computation tests"
```

---

### Task 7: Run full test suite and verify

**Step 1: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass (207 existing + ~7 new = ~214 total).

**Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 3: Final commit if any cleanup needed**

---

### Task 8: Update CLAUDE.md and memory

**Files:**
- Modify: `CLAUDE.md` — update test count, add parallelization to Design Principles, add `MAX_CONCURRENT_CITIES` to env vars
- Modify: `/Users/harendraprasad/.claude/projects/-Users-harendraprasad-Coding-travel-companion/memory/MEMORY.md` — add parallelization section

**Step 1: Update CLAUDE.md**

- Update test count from 207 to new count
- Add to Design Principles: "City processing parallelized via asyncio.Queue + Semaphore (bounded by `MAX_CONCURRENT_CITIES`). Excursion processing and landmark searches also parallelized via asyncio.gather(). Failed cities retry once then emit `city_error` SSE event."
- Add `MAX_CONCURRENT_CITIES` to Backend env vars list

**Step 2: Update MEMORY.md**

Add parallelization architecture notes.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with parallelization architecture"
```
