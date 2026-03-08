# Day Plan Pipeline Parallelization — Design

## Problem

The day plan pipeline processes cities **sequentially**. A 10-day, 3-city trip takes 10-17 minutes because each city's full pipeline (discovery → Day Scout → Reviewer → Fixer → TSP → routes → weather) runs one after another. Landmark text searches and excursion processing are also sequential within each city.

## Goals

- Reduce total pipeline time from 10-17 min to **5-8 min** for a typical 3-city trip
- Maintain real-time SSE progress streaming
- Preserve all quality guarantees (dedup, quality loop, error recovery)
- No cross-city duplicate prevention (cities are independent experiences)

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cross-city dedup | No | Same place in different cities is a different experience. Eliminates shared state. |
| SSE ordering | Interleaved | Frontend processes events as they arrive. Final `complete` event is ground truth. |
| Concurrency limit | Configurable (`MAX_CONCURRENT_CITIES`, default 3) | Env var control for different API key tiers. |
| Error handling | Retry once → partial results + toast | Resilient UX without over-complexity. |
| City failure UX | `city_error` SSE event → frontend toast | "Failed to plan {city}. You can regenerate day plans to try again." |

---

## Architecture

```
generate_stream()
  └── asyncio.Semaphore(MAX_CONCURRENT_CITIES)
      └── _process_city()           [parallel per city via Queue]
          ├── _plan_excursion_days()
          │   └── asyncio.gather()  [parallel per excursion]
          │       └── landmark searches via gather()
          ├── landmark text searches via gather()        ← Level 3
          ├── theme-based discovery via gather()         ← Level 3
          └── _plan_city_batched()  [sequential within city — planned_ids constraint]
              └── Day Scout → Reviewer → Fixer [sequential batches]
```

Three parallelization levels compose naturally. Levels 2 and 3 operate inside level 1.

---

## Level 1: City Parallelism (2-3x speedup)

### Current (sequential)

```python
for city_idx, city in enumerate(journey.cities):
    yield ProgressEvent(phase="city_start", ...)
    # ... 500+ lines of per-city processing ...
    yield ProgressEvent(phase="city_complete", ...)
yield ProgressEvent(phase="complete", ...)
```

### New (parallel via Queue + Semaphore)

**Refactor `generate_stream()`:**

```python
async def generate_stream(self, journey, request):
    event_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    total_cities = len(journey.cities)
    max_concurrent = settings.max_concurrent_cities

    async def _run_all_cities():
        sem = asyncio.Semaphore(max_concurrent)

        async def _bounded_city(city_idx, city):
            async with sem:
                return await self._process_city(
                    city_idx, city, journey, request,
                    event_queue, total_cities
                )

        results = await asyncio.gather(
            *(_bounded_city(i, c) for i, c in enumerate(journey.cities)),
            return_exceptions=True,
        )
        await event_queue.put(None)  # Sentinel — signals end of stream
        return results

    producer = asyncio.create_task(_run_all_cities())

    # Stream events as they arrive (interleaved from all cities)
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
            logger.error("City %s failed: %s", journey.cities[i].name, r)
            try:
                retry_plans = await self._process_city(
                    i, journey.cities[i], journey, request,
                    event_queue, total_cities
                )
                all_plans.extend(retry_plans)
            except Exception as e2:
                logger.error("City %s retry failed: %s", journey.cities[i].name, e2)
                await event_queue.put(ProgressEvent(
                    phase="city_error",
                    message=f"Failed to plan {journey.cities[i].name}. You can regenerate day plans to try again.",
                    data={"city": journey.cities[i].name},
                ))
        else:
            all_plans.extend(r)

    # Drain any retry events
    while not event_queue.empty():
        event = await event_queue.get()
        if event is not None:
            yield event

    all_plans.sort(key=lambda dp: dp.day_number)
    yield ProgressEvent(
        phase="complete",
        data={"day_plans": [dp.model_dump() for dp in all_plans]},
    )
```

**New `_process_city()` method** — extracted from the current for-loop body:

```python
async def _process_city(
    self, city_idx, city, journey, request,
    event_queue, total_cities
) -> list[DayPlan]:
    """Process a single city. Pushes ProgressEvents to queue. Returns DayPlans."""
    # Compute day_offset without shared state
    day_offset = sum(journey.cities[i].days for i in range(city_idx))

    # ... current per-city logic (lines 596-1128) ...
    # All `yield ProgressEvent(...)` become `await event_queue.put(ProgressEvent(...))`

    return city_plans
```

**Key insight:** `day_offset` is computable from city index — no shared mutable state between cities.

---

## Level 2: Excursion Parallelism (2-4x speedup for excursion phase)

### Current (sequential)

```python
for day_idx, exc in sorted(excursions_by_day.items()):
    # geocode → discover → scout → quality → routes → weather
```

### New (parallel via gather)

Extract per-excursion logic into `_plan_single_excursion()`, then gather:

```python
async def _plan_single_excursion(self, exc, exc_day_indices, city, request, day_offset):
    """Process one excursion: geocode → discover → scout → quality → routes."""
    # Current lines 202-505, extracted as-is
    return planned_days  # list[DayPlan]

async def _plan_excursion_days(self, excursions_by_day, city, request, day_offset):
    # Group by independence (multi-day share same object)
    exc_groups = {}  # exc_key -> (exc, [day_indices])
    for day_idx, exc in sorted(excursions_by_day.items()):
        key = exc.name
        if key not in exc_groups:
            exc_groups[key] = (exc, [])
        exc_groups[key][1].append(day_idx)

    # Parallel processing
    tasks = [
        self._plan_single_excursion(exc, days, city, request, day_offset)
        for exc, days in exc_groups.values()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge with fallback stubs for failures
    planned = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("Excursion failed: %s", r)
            # Build fallback stub day plan (existing _build_excursion_day_plan pattern)
        else:
            planned.extend(r)
    return planned
```

---

## Level 3: Landmark & Theme Search Parallelism (3-5x speedup for discovery phase)

### Current (sequential — 7-10 API calls one at a time)

```python
for lm in city_landmarks:
    lm_results = await self.places.text_search_places(
        query=lm["name"] + " " + city_name,
        location=city.location, max_results=1,
    )
```

### New (parallel via gather)

```python
async def _search_landmark(lm_name):
    try:
        return await self.places.text_search_places(
            query=lm_name + " " + city_name,
            location=city.location, max_results=1,
        )
    except Exception:
        return []

lm_results_all = await asyncio.gather(
    *(_search_landmark(lm["name"]) for lm in city_landmarks)
)
for lm_results in lm_results_all:
    for lc in lm_results:
        if lc.place_id not in existing_ids:
            candidates.append(lc)
            existing_ids.add(lc.place_id)
```

Same gather pattern applied to theme-based discovery (lines 737-752).

---

## Error Handling

| Failure | Action | UX |
|---------|--------|-----|
| City pipeline fails | Retry once | If retry fails: `city_error` SSE event → frontend toast: "Failed to plan {city}. You can regenerate day plans to try again." Other cities render normally. |
| Excursion geocode fails | Fallback stub day plan | Existing behavior (placeholder day) |
| Excursion pipeline fails | Fallback stub day plan | Same as geocode failure |
| Landmark search fails | Skip silently | Existing behavior |
| Theme discovery fails | Skip silently | Existing behavior |

### Frontend Change

In `useStreamingDayPlans.ts`, add handling for `city_error` phase:

```typescript
if (event.phase === 'city_error') {
    showToast(event.message, 'error');
}
```

---

## Configuration

**`backend/app/config/planning.py`:**
```python
MAX_CONCURRENT_CITIES: int = 3
```

**`backend/app/config/settings.py`:**
```python
max_concurrent_cities: int = Field(default=3, env="MAX_CONCURRENT_CITIES")
```

**Environment variable:** `MAX_CONCURRENT_CITIES=3` (default, adjustable per deployment)

---

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `backend/app/config/planning.py` | Add `MAX_CONCURRENT_CITIES` | ~2 |
| `backend/app/config/settings.py` | Add `max_concurrent_cities` field | ~2 |
| `backend/app/orchestrators/day_plan.py` | Refactor `generate_stream()`, extract `_process_city()`, parallelize excursions via `_plan_single_excursion()`, parallelize landmark/theme searches | ~200 restructured |
| `frontend/src/hooks/useStreamingDayPlans.ts` | Handle `city_error` phase → toast | ~3 |
| `backend/tests/test_agents.py` | Parallelization tests | ~30 |

---

## Estimated Impact

| Scenario (10-day, 3-city) | Before | After |
|---------------------------|--------|-------|
| Total pipeline time | 10-17 min | **5-8 min** |
| Per-city wall clock | 9-15 min (3 cities × 3-5 min) | 3-5 min (slowest city) |
| Excursion phase | 2-4 min (sequential) | ~1-2 min (parallel) |
| Landmark discovery | 10-20s per city | 3-5s per city |

---

## Testing

- All 207 existing tests must pass (no behavior change for single-city trips)
- New tests: parallel city processing produces correct results with mocked services
- New tests: semaphore bounds respected (3 cities with MAX_CONCURRENT=2 → max 2 concurrent)
- New tests: retry on failure → partial results returned
- New tests: landmark gather produces same candidates as sequential
- Manual: run a 3-city trip end-to-end, verify ~2x speedup and correct SSE events
