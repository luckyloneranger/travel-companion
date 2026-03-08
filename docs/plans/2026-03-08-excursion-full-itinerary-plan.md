# Excursion Day Full Itinerary — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace single-activity excursion day placeholders with full itineraries by discovering places at the excursion destination and running them through the existing Day Scout → Reviewer → Fixer quality pipeline.

**Architecture:** Excursion days (flagged with `excursion_type: full_day`) currently bypass the planning pipeline entirely. Instead, we geocode the excursion destination, discover places there via Google Places API, then feed those candidates into the same batched Day Scout → Reviewer → Fixer pipeline that handles regular city days. Transit time to/from the excursion destination is estimated and deducted from available planning hours.

**Tech Stack:** Python 3.14, FastAPI, Google Places API (New), async/await, Pydantic v2

---

### Task 1: Add `_plan_excursion_days()` method to orchestrator

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py:102-152` (replace `_build_excursion_day_plan` usage)

**Step 1: Write the new `_plan_excursion_days()` async method**

Add after `_build_excursion_day_plan()` (which stays as fallback). This new method:
1. Geocodes each excursion destination
2. Discovers candidates at that location
3. Discovers landmarks at that destination
4. Estimates transit time from `distance_from_city_km`
5. Runs Day Scout → Reviewer → Fixer for each excursion day as a 1-day batch
6. Returns a list of fully-planned `DayPlan` objects

```python
async def _plan_excursion_days(
    self,
    excursions_by_day: dict[int, CityHighlight],
    city: "CityStop",
    request: "TripRequest",
    day_offset: int,
) -> list["DayPlan"]:
    """Plan detailed itineraries for excursion days.

    Instead of creating single-activity stubs, discovers places at the
    excursion destination and runs them through the Day Scout -> Reviewer
    -> Fixer quality pipeline.

    Args:
        excursions_by_day: Mapping of day_index -> excursion CityHighlight.
        city: The CityStop this excursion belongs to.
        request: Original TripRequest for interests, pace, dates, etc.
        day_offset: Cumulative day offset across all cities.

    Returns:
        List of fully-planned DayPlan objects with is_excursion=True.
    """
    from app.config.planning import (
        MAX_DAY_PLAN_ITERATIONS, MIN_DAY_PLAN_SCORE,
    )
    from app.agents.day_planner import _build_meal_time_guidance
    from app.models.internal import AIPlan

    planned: list[DayPlan] = []

    # Group consecutive days for multi-day excursions (same excursion object)
    processed_excursions: set[str] = set()

    for day_idx, exc in sorted(excursions_by_day.items()):
        exc_key = exc.name
        if exc_key in processed_excursions and exc.excursion_type == "multi_day":
            continue  # Already planned as part of multi-day batch

        # Determine all day indices for this excursion
        if exc.excursion_type == "multi_day":
            exc_day_indices = sorted(
                k for k, v in excursions_by_day.items() if v is exc
            )
            processed_excursions.add(exc_key)
        else:
            exc_day_indices = [day_idx]

        # 1. Geocode the excursion destination
        try:
            geo = await self.places.geocode(f"{exc.name}, {city.country or ''}")
            exc_location = Location(lat=geo["lat"], lng=geo["lng"])
            logger.info(
                "[DayPlanOrchestrator] Geocoded excursion %r -> %.4f, %.4f",
                exc.name, geo["lat"], geo["lng"],
            )
        except Exception as e:
            logger.warning(
                "[DayPlanOrchestrator] Geocoding failed for excursion %r: %s — "
                "falling back to placeholder", exc.name, e,
            )
            for di in exc_day_indices:
                schedule_date = request.start_date + timedelta(days=day_offset + di)
                if exc.excursion_type == "multi_day":
                    multi_pos = exc_day_indices.index(di) + 1
                    day_label = f"Day {multi_pos} of {len(exc_day_indices)}"
                else:
                    day_label = ""
                planned.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                    day_label=day_label,
                ))
            continue

        # 2. Discover places at the excursion destination
        try:
            exc_candidates = await self.places.discover_places(
                location=exc_location,
                interests=request.interests,
            )
        except Exception as e:
            logger.warning(
                "[DayPlanOrchestrator] Place discovery failed for excursion %r: %s",
                exc.name, e,
            )
            exc_candidates = []

        # 3. Discover landmarks at the excursion destination
        exc_landmarks: list[dict] = []
        try:
            exc_landmarks = await self.places.discover_landmarks(exc.name)
            # Merge landmark PlaceCandidates into candidates
            if exc_landmarks:
                existing_ids = {c.place_id for c in exc_candidates}
                for lm in exc_landmarks[:7]:
                    lm_name = lm.get("name", "")
                    if not lm_name:
                        continue
                    try:
                        lm_results = await self.places.text_search_places(
                            query=f"{lm_name} {exc.name}",
                            location=exc_location,
                            max_results=1,
                        )
                        for lc in lm_results:
                            if lc.place_id not in existing_ids:
                                exc_candidates.append(lc)
                                existing_ids.add(lc.place_id)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(
                "[DayPlanOrchestrator] Landmark discovery failed for excursion %r: %s",
                exc.name, e,
            )

        if not exc_candidates:
            logger.warning(
                "[DayPlanOrchestrator] No candidates for excursion %r, using placeholder",
                exc.name,
            )
            for di in exc_day_indices:
                schedule_date = request.start_date + timedelta(days=day_offset + di)
                if exc.excursion_type == "multi_day":
                    multi_pos = exc_day_indices.index(di) + 1
                    day_label = f"Day {multi_pos} of {len(exc_day_indices)}"
                else:
                    day_label = ""
                planned.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                    day_label=day_label,
                ))
            continue

        # Resolve photo references
        for c in exc_candidates:
            if c.photo_references:
                c.photo_references = [
                    self.places.get_photo_url(ref) for ref in c.photo_references
                ]
            if c.photo_reference:
                c.photo_reference = self.places.get_photo_url(c.photo_reference)

        # 4. Estimate transit time from distance_from_city_km
        transit_hours_one_way = 1.0  # default 1h
        if exc.distance_from_city_km:
            transit_hours_one_way = max(0.5, exc.distance_from_city_km / 50)
        transit_hours_round_trip = transit_hours_one_way * 2

        # 5. Build experience theme for the batch
        from app.models.journey import ExperienceTheme
        exc_theme = ExperienceTheme(
            theme=exc.name,
            category=exc.category or "excursion",
            why=exc.description or f"Day trip to {exc.name}",
        )

        # 6. Run Day Scout for each excursion day
        meal_guidance = _build_meal_time_guidance(city.country or "")

        # Format landmarks for prompts
        landmarks_section = ""
        if exc_landmarks:
            lines = ["TOP LANDMARKS by visitor reviews (include at least one per batch):"]
            for lm in exc_landmarks[:5]:
                lines.append(f"- {lm.get('name')} ({lm.get('user_ratings_total', 0):,} reviews)")
            landmarks_section = "\n".join(lines)

        batch_themes = {
            exc_day_indices[i] + 1: [exc_theme]
            for i in range(len(exc_day_indices))
        }

        try:
            batch_plan = await self.day_scout.plan_batch(
                candidates=exc_candidates,
                batch_themes=batch_themes,
                destination=exc.name,
                pace=request.pace.value,
                landmarks=exc_landmarks if exc_landmarks else None,
                already_used=set(),
                meal_time_guidance=meal_guidance,
                travelers_description=request.travelers.summary,
            )
        except Exception as e:
            logger.error(
                "[DayPlanOrchestrator] Day Scout failed for excursion %r: %s",
                exc.name, e,
            )
            for di in exc_day_indices:
                schedule_date = request.start_date + timedelta(days=day_offset + di)
                planned.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                ))
            continue

        # 7. Quality loop: Day Reviewer -> Day Fixer
        themes_text = ""
        for d, themes in sorted(batch_themes.items()):
            theme_names = ", ".join(t.theme for t in themes)
            themes_text += f"Day {d}: {theme_names}\n"

        for iteration in range(MAX_DAY_PLAN_ITERATIONS):
            plan_detail = ""
            batch_day_nums = sorted(batch_themes.keys())
            for i, group in enumerate(batch_plan.day_groups):
                day_num = batch_day_nums[i] if i < len(batch_day_nums) else i + 1
                place_names = []
                for pid in group.place_ids:
                    name = next(
                        (c.name for c in exc_candidates if c.place_id == pid),
                        pid,
                    )
                    dur = batch_plan.durations.get(pid, "?")
                    place_names.append(f"{name} ({dur}min)")
                plan_detail += f"Day {day_num} ({group.theme}): {', '.join(place_names)}\n"

            try:
                review = await self.day_reviewer.review_batch(
                    day_plans_detail=plan_detail,
                    batch_themes=themes_text,
                    landmarks_section=landmarks_section,
                    destination=exc.name,
                )
            except Exception:
                break

            logger.info(
                "[DayPlanOrchestrator] Excursion %r review score: %d (acceptable=%s, iter=%d)",
                exc.name, review.score, review.is_acceptable, iteration + 1,
            )

            if review.is_acceptable or review.score >= MIN_DAY_PLAN_SCORE:
                break

            try:
                batch_plan = await self.day_fixer.fix_batch(
                    current_plan=batch_plan,
                    issues=review.issues,
                    candidates=exc_candidates,
                    destination=exc.name,
                )
            except Exception:
                break

        # 8. Convert AIPlan to DayPlan objects (TSP, schedule, routes, weather)
        candidate_map = {c.place_id: c for c in exc_candidates}

        # Weather for excursion location
        exc_weather: dict[str, object] = {}
        if self.weather and exc_location:
            try:
                forecasts = await self.weather.get_daily_forecast(exc_location, days=10)
                exc_weather = {str(f.date): f for f in forecasts}
            except Exception:
                pass

        for i, group in enumerate(batch_plan.day_groups):
            if i >= len(exc_day_indices):
                break
            di = exc_day_indices[i]
            schedule_date = request.start_date + timedelta(days=day_offset + di)

            day_candidates = [
                candidate_map[pid]
                for pid in group.place_ids
                if pid in candidate_map
            ]

            if not day_candidates:
                planned.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                ))
                continue

            # TSP optimize
            optimized = self.optimizer.optimize_day(
                activities=day_candidates,
                distance_fn=haversine_distance,
                start_location=exc_location,
                preserve_order=True,
            )

            # Schedule with adjusted times for transit
            transit_minutes = int(transit_hours_one_way * 60)
            base_start_hour = 9
            adjusted_start_minutes = (base_start_hour * 60) + transit_minutes
            adjusted_end_minutes = (21 * 60) - transit_minutes

            from datetime import time as dt_time
            day_start_time = dt_time(
                hour=min(adjusted_start_minutes // 60, 23),
                minute=adjusted_start_minutes % 60,
            )
            day_end_time = dt_time(
                hour=min(adjusted_end_minutes // 60, 23),
                minute=adjusted_end_minutes % 60,
            )

            activities = self.scheduler.build_schedule(
                places=optimized,
                pace=request.pace,
                durations=batch_plan.durations,
                start_location=exc_location,
                schedule_date=schedule_date,
                day_start_time=day_start_time,
                day_end_time=day_end_time,
                cost_estimates=batch_plan.cost_estimates,
                country=city.country,
            )

            # Bookend with excursion-area accommodation location (use exc_location as start)
            # No hotel bookends for excursion days — traveler is in transit

            # Compute routes
            activities = await self._compute_routes_via_matrix(
                activities, pace=request.pace,
            )

            # Weather
            day_weather = None
            forecast = exc_weather.get(str(schedule_date))
            if forecast:
                day_weather = Weather(
                    temperature_high_c=forecast.temperature_high_c,
                    temperature_low_c=forecast.temperature_low_c,
                    condition=forecast.condition,
                    precipitation_chance_percent=forecast.precipitation_chance_percent,
                    wind_speed_kmh=forecast.wind_speed_kmh,
                    humidity_percent=forecast.humidity_percent,
                    uv_index=forecast.uv_index,
                )
                activities = self._add_weather_warnings(activities, forecast)

            daily_cost = sum(
                a.estimated_cost_usd for a in activities
                if a.estimated_cost_usd is not None
            )

            planned.append(DayPlan(
                date=str(schedule_date),
                day_number=day_offset + di + 1,
                theme=group.theme,
                activities=activities,
                city_name=city.name,
                weather=day_weather,
                daily_cost_usd=daily_cost if daily_cost > 0 else None,
                is_excursion=True,
                excursion_name=exc.name,
            ))

    return planned
```

**Step 2: Run existing tests to verify no breakage**

Run: `cd backend && source venv/bin/activate && pytest tests/test_agents.py::TestExcursionBlocking -v`
Expected: All 7 existing excursion tests PASS (method still exists as fallback)

**Step 3: Commit**
```bash
git add backend/app/orchestrators/day_plan.py
git commit -m "feat: add _plan_excursion_days() for full excursion itineraries"
```

---

### Task 2: Update `generate_stream()` to call `_plan_excursion_days()`

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py:256-277`

**Step 1: Replace the excursion plan creation loop**

In `generate_stream()`, replace the loop at lines 260-277 that calls `_build_excursion_day_plan()` with a call to the new `_plan_excursion_days()`:

Change this block (lines 256-281):
```python
if excursions:
    blocked_days, partial_days = self._compute_excursion_schedule(
        excursions, city.days,
    )
    for day_idx, exc in sorted(blocked_days.items()):
        schedule_date = request.start_date + timedelta(days=day_offset + day_idx)
        if exc.excursion_type == "multi_day":
            multi_indices = sorted(k for k, v in blocked_days.items() if v is exc)
            pos = multi_indices.index(day_idx) + 1
            total = len(multi_indices)
            day_label = f"Day {pos} of {total}"
        else:
            day_label = ""
        excursion_plans.append(
            self._build_excursion_day_plan(
                excursion=exc,
                date_str=str(schedule_date),
                day_number=day_offset + day_idx + 1,
                city_name=city_name,
                day_label=day_label,
            )
        )
    logger.info(...)
```

To:
```python
if excursions:
    blocked_days, partial_days = self._compute_excursion_schedule(
        excursions, city.days,
    )
    excursion_plans = await self._plan_excursion_days(
        excursions_by_day=blocked_days,
        city=city,
        request=request,
        day_offset=day_offset,
    )
    logger.info(
        "[DayPlanOrchestrator] %s: %d excursion days planned (%d partial)",
        city_name, len(blocked_days), len(partial_days),
    )
```

**Step 2: Run existing tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_agents.py -v`
Expected: All tests PASS

**Step 3: Commit**
```bash
git add backend/app/orchestrators/day_plan.py
git commit -m "feat: wire _plan_excursion_days() into generate_stream()"
```

---

### Task 3: Update Day Reviewer prompt — remove excursion exception clause

**Files:**
- Modify: `backend/app/prompts/day_plan/day_reviewer_system.md:51`

**Step 1: Remove the exception line**

Remove this line from the activity count section:
```
- Exception: excursion days may have 1-2 activities (full-day experience)
```

Excursion days now go through the full pipeline and should have proper activity counts like any other day.

**Step 2: Commit**
```bash
git add backend/app/prompts/day_plan/day_reviewer_system.md
git commit -m "fix: remove excursion exception from Day Reviewer — excursions now fully planned"
```

---

### Task 4: Write tests for `_plan_excursion_days()`

**Files:**
- Modify: `backend/tests/test_agents.py` (add to `TestExcursionBlocking` class)

**Step 1: Write test for fallback when geocoding fails**

```python
@pytest.mark.asyncio
async def test_plan_excursion_days_fallback_on_geocode_failure(self):
    """When geocoding fails, _plan_excursion_days falls back to placeholder."""
    from unittest.mock import AsyncMock, MagicMock
    from app.models.journey import CityHighlight, CityStop, ExperienceTheme
    from app.models.common import Location
    from datetime import date

    # Create mock orchestrator with failing geocode
    orchestrator = MagicMock(spec=DayPlanOrchestrator)
    orchestrator.places = AsyncMock()
    orchestrator.places.geocode = AsyncMock(side_effect=ValueError("No results"))
    orchestrator._build_excursion_day_plan = DayPlanOrchestrator._build_excursion_day_plan

    city = MagicMock()
    city.name = "Tokyo"
    city.country = "Japan"
    city.location = Location(lat=35.6762, lng=139.6503)

    request = MagicMock()
    request.start_date = date(2026, 4, 10)
    request.interests = ["culture"]
    request.pace = MagicMock(value="moderate")
    request.travelers = MagicMock(summary="2 adults")

    excursion = CityHighlight(
        name="Hakone", category="nature",
        description="Hot springs and mountain views",
        excursion_type="full_day",
    )

    result = await DayPlanOrchestrator._plan_excursion_days(
        orchestrator,
        excursions_by_day={3: excursion},
        city=city,
        request=request,
        day_offset=0,
    )

    assert len(result) == 1
    assert result[0].is_excursion is True
    assert result[0].activities[0].place.name == "Hakone"
```

**Step 2: Run the test**

Run: `cd backend && source venv/bin/activate && pytest tests/test_agents.py::TestExcursionBlocking::test_plan_excursion_days_fallback_on_geocode_failure -v`
Expected: PASS

**Step 3: Commit**
```bash
git add backend/tests/test_agents.py
git commit -m "test: add excursion day planning fallback test"
```

---

### Task 5: End-to-end test — run a trip and verify excursion days

**Step 1: Start the backend server**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`

**Step 2: Generate a JWT token**

Run: `cd backend && source venv/bin/activate && ./venv/bin/python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'test','email':'t@t.com','name':'Test'}))"`

**Step 3: Plan a trip with known excursion days (Japan 10 days)**

Run:
```bash
TOKEN="<token from step 2>"
curl -s --max-time 300 http://localhost:8000/api/trips/plan/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Japan",
    "origin": "Mumbai, India",
    "total_days": 10,
    "start_date": "2026-04-10",
    "interests": ["culture", "food", "nature", "family"],
    "pace": "moderate",
    "travel_mode": "TRANSIT",
    "budget": "moderate",
    "travelers": {"adults": 2, "children": 1}
  }' > /tmp/japan_test_sse.txt
```

**Step 4: Get the trip ID and generate day plans**

```bash
TRIP_ID=$(curl -s http://localhost:8000/api/trips -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
curl -s --max-time 600 "http://localhost:8000/api/trips/${TRIP_ID}/days/stream" \
  -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{}' > /tmp/japan_days_test.txt
```

**Step 5: Verify excursion days have multiple activities**

Check that any day with `is_excursion=True` or with an excursion theme name (like "Hakone", "Nara") has more than 1 activity:

```bash
grep "^data:" /tmp/japan_days_test.txt | tail -1 | sed 's/^data: //' | python3 -c "
import sys, json
d = json.load(sys.stdin)
day_plans = d.get('data', {}).get('day_plans', [])
for dp in day_plans:
    acts = [a for a in dp.get('activities', []) if a.get('duration_minutes', 0) > 0]
    is_exc = dp.get('is_excursion', False)
    exc_name = dp.get('excursion_name', '')
    if is_exc or exc_name:
        status = 'PASS' if len(acts) >= 3 else 'NEEDS REVIEW'
        print(f'Day {dp[\"day_number\"]} ({exc_name}): {len(acts)} activities — {status}')
        for a in acts:
            print(f'  - {a.get(\"name\", a.get(\"place\", {}).get(\"name\", \"?\"))}: {a.get(\"duration_minutes\")}min')
if not any(dp.get('is_excursion') or dp.get('excursion_name') for dp in day_plans):
    print('No excursion days found — Scout may not have assigned excursion_type themes this run')
"
```

Expected: Excursion days have 3+ activities (not 1 placeholder).

**Step 6: Run full test suite**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: All 199+ tests PASS

**Step 7: Commit all changes**
```bash
git add -A
git commit -m "feat: excursion days get full itineraries via discovery + quality pipeline

Excursion days (Hakone, Nara, etc.) now geocode the destination, discover
places there via Google Places API, and run through the Day Scout →
Reviewer → Fixer quality pipeline. Falls back to single-activity
placeholder if geocoding or discovery fails."
```
