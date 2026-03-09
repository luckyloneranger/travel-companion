# Activity Timing & Duration Grounding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix activity duration estimation and opening hours enforcement so day plans have accurate visit times and never schedule activities after closing.

**Architecture:** Three changes work together: (1) the scheduler enforces closing times as a hard constraint, (2) opening hours from Google flow through to the Activity model for evaluator accuracy, (3) the Day Fixer receives opening hours context so it can make informed swaps. Since Google Places API does not offer a `durationMinutes` field, we improve the LLM's duration estimates by passing opening hours and editorial summaries as grounding context.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pytest, httpx

---

### Task 1: Scheduler — Enforce Closing Time Constraint

The scheduler's `_adjust_for_opening_hours()` only checks if a place has opened yet. It never validates whether the activity will *end* before closing. This causes museums scheduled at 19:00 when they close at 17:00.

**Files:**
- Modify: `backend/app/algorithms/scheduler.py:500-524`
- Test: `backend/tests/test_scheduler.py`

**Step 1: Write failing tests**

Add to `backend/tests/test_scheduler.py`:

```python
class TestScheduleBuilderOpeningHours:
    """Tests for opening hours enforcement in scheduler."""

    def test_activity_skipped_when_closed(self):
        """Activity should be skipped if it would end after closing time."""
        from app.models.internal import OpeningHours

        place = _make_place(
            "museum1", "National Museum", ["museum"],
            opening_hours=[OpeningHours(day=3, open_time="09:00", close_time="17:00")],
        )
        builder = ScheduleBuilder()
        # Schedule on a Wednesday (weekday=2, google_day=3)
        schedule = builder.build_schedule(
            places=[place],
            durations={"museum1": 120},
            pace=Pace.MODERATE,
            schedule_date=date(2026, 4, 15),  # Wednesday
            config=ScheduleConfig(day_start=time(16, 30)),  # Start at 16:30
        )
        # 16:30 + 120min = 18:30 > 17:00 close
        # Should either truncate to fit or skip
        if schedule:
            # If scheduled, must end by 17:00
            assert schedule[0].time_end <= "17:00"
        # If no activities, that's also acceptable (skipped)

    def test_activity_truncated_to_fit_closing(self):
        """Activity duration should be shortened to fit before closing time."""
        from app.models.internal import OpeningHours

        place = _make_place(
            "temple1", "Grand Temple", ["temple"],
            opening_hours=[OpeningHours(day=3, open_time="09:00", close_time="17:00")],
        )
        builder = ScheduleBuilder()
        schedule = builder.build_schedule(
            places=[place],
            durations={"temple1": 90},
            pace=Pace.MODERATE,
            schedule_date=date(2026, 4, 15),  # Wednesday
            config=ScheduleConfig(day_start=time(16, 0)),  # Start at 16:00
        )
        # 16:00 + 90min = 17:30 > 17:00 close
        # Should truncate to 60min (16:00-17:00)
        assert len(schedule) == 1
        assert schedule[0].time_end == "17:00"
        assert schedule[0].duration_minutes == 60

    def test_activity_not_truncated_when_fits(self):
        """Activity should keep full duration when it fits within opening hours."""
        from app.models.internal import OpeningHours

        place = _make_place(
            "park1", "City Park", ["park"],
            opening_hours=[OpeningHours(day=3, open_time="06:00", close_time="22:00")],
        )
        builder = ScheduleBuilder()
        schedule = builder.build_schedule(
            places=[place],
            durations={"park1": 60},
            pace=Pace.MODERATE,
            schedule_date=date(2026, 4, 15),  # Wednesday
        )
        assert len(schedule) == 1
        assert schedule[0].duration_minutes == 60

    def test_no_opening_hours_schedules_normally(self):
        """Places without opening hours should schedule normally (no enforcement)."""
        place = _make_place("attraction1", "Scenic Spot", ["scenic_spot"])
        builder = ScheduleBuilder()
        schedule = builder.build_schedule(
            places=[place],
            durations={"attraction1": 90},
            pace=Pace.MODERATE,
            schedule_date=date(2026, 4, 15),
        )
        assert len(schedule) == 1
        assert schedule[0].duration_minutes == 90
```

Update `_make_place` helper to accept `opening_hours` parameter:

```python
def _make_place(
    place_id: str = "p1",
    name: str = "Test Place",
    types: list[str] | None = None,
    lat: float = 48.0,
    lng: float = 2.0,
    suggested_duration_minutes: int | None = None,
    opening_hours: list | None = None,
) -> PlaceCandidate:
    return PlaceCandidate(
        place_id=place_id,
        name=name,
        address="123 Test St",
        location=Location(lat=lat, lng=lng),
        types=types or ["tourist_attraction"],
        rating=4.5,
        suggested_duration_minutes=suggested_duration_minutes,
        opening_hours=opening_hours,
    )
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_scheduler.py::TestScheduleBuilderOpeningHours -v`
Expected: FAIL — closing time not enforced

**Step 3: Implement closing time enforcement**

Modify `backend/app/algorithms/scheduler.py`. Rename `_adjust_for_opening_hours` to `_apply_opening_hours_constraints` and add closing time logic:

```python
def _apply_opening_hours_constraints(
    self,
    place: PlaceCandidate,
    current_time: datetime,
    duration: int,
) -> tuple[datetime, int] | None:
    """
    Apply opening hours constraints to activity scheduling.

    Returns:
        tuple of (adjusted_start_time, adjusted_duration) if schedulable,
        None if place is closed or insufficient time before closing.
    """
    if not place.opening_hours:
        return current_time, duration

    day_of_week = current_time.weekday()
    google_day = (day_of_week + 1) % 7

    for hours in place.opening_hours:
        if hours.day == google_day:
            open_time = datetime.strptime(hours.open_time, "%H:%M").time()
            close_time = datetime.strptime(hours.close_time, "%H:%M").time()

            # Push forward if place hasn't opened yet
            start = current_time
            if start.time() < open_time:
                start = datetime.combine(current_time.date(), open_time)

            # Check if already past closing
            if start.time() >= close_time:
                return None

            # Truncate duration if activity would end after closing
            close_dt = datetime.combine(current_time.date(), close_time)
            available_minutes = int((close_dt - start).total_seconds()) // 60

            if available_minutes < self.config.min_activity_duration:
                return None

            adjusted_duration = min(duration, available_minutes)
            return start, adjusted_duration

    # Day not found in opening hours — schedule normally
    return current_time, duration
```

Update `build_schedule()` at lines 332-337 to use the new method:

```python
# Determine duration
duration = self._get_duration(place, pace, durations)

# Apply opening hours constraints (start time + closing time)
oh_result = self._apply_opening_hours_constraints(place, current_time, duration)
if oh_result is None:
    logger.warning(
        "Skipping %s: closed or insufficient time before closing", place.name
    )
    continue
current_time, duration = oh_result
```

Remove the old `_adjust_for_opening_hours` method entirely.

**Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_scheduler.py -v`
Expected: ALL PASS (including existing tests)

**Step 5: Commit**

```bash
git add backend/app/algorithms/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat(scheduler): enforce closing time constraint on activities"
```

---

### Task 2: Pass Opening Hours Through to Activity Model

Currently `scheduler.py:415` hardcodes `opening_hours=[]` when building the Activity's Place model, discarding the structured `OpeningHours` data from `PlaceCandidate`. The quality evaluator then has to regex-parse strings from Google — but gets nothing because the field is always empty.

**Files:**
- Modify: `backend/app/algorithms/scheduler.py:405-417`
- Test: `backend/tests/test_scheduler.py`

**Step 1: Write failing test**

Add to `backend/tests/test_scheduler.py`:

```python
def test_opening_hours_preserved_in_activity(self):
    """Opening hours from PlaceCandidate should flow into Activity.place."""
    from app.models.internal import OpeningHours

    place = _make_place(
        "museum1", "Art Museum", ["museum"],
        opening_hours=[
            OpeningHours(day=3, open_time="09:00", close_time="17:00"),
            OpeningHours(day=4, open_time="09:00", close_time="21:00"),
        ],
    )
    builder = ScheduleBuilder()
    schedule = builder.build_schedule(
        places=[place],
        durations={"museum1": 90},
        pace=Pace.MODERATE,
        schedule_date=date(2026, 4, 15),  # Wednesday
    )
    assert len(schedule) == 1
    # Opening hours should be formatted as human-readable strings
    assert len(schedule[0].place.opening_hours) > 0
    assert "09:00" in schedule[0].place.opening_hours[0]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && pytest tests/test_scheduler.py::TestScheduleBuilderOpeningHours::test_opening_hours_preserved_in_activity -v`
Expected: FAIL — `opening_hours` is empty list

**Step 3: Implement opening hours passthrough**

In `backend/app/algorithms/scheduler.py`, replace line 415 (`opening_hours=[],`) with a conversion from structured `OpeningHours` to the string format the evaluator expects:

```python
# Format opening hours as human-readable strings for downstream consumers
_day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
formatted_hours = []
if place.opening_hours:
    for oh in place.opening_hours:
        day_name = _day_names[oh.day] if 0 <= oh.day <= 6 else f"Day{oh.day}"
        formatted_hours.append(f"{day_name}: {oh.open_time} \u2013 {oh.close_time}")

activity_place = Place(
    place_id=place.place_id,
    name=place.name,
    address=place.address,
    location=place.location,
    category=place.types[0] if place.types else "",
    rating=place.rating,
    photo_url=place.photo_reference,
    photo_urls=place.photo_references,
    opening_hours=formatted_hours,
    website=place.website,
)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_scheduler.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/algorithms/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat(scheduler): pass opening hours through to Activity model"
```

---

### Task 3: Pass Opening Hours + Editorial Summary to Day Scout LLM

The Day Scout LLM estimates durations blind — it only sees place name, rating, and types. By also passing opening hours and editorial summary, the LLM can make informed estimates (e.g., "this museum closes at 17:00 so don't budget 3 hours starting at 15:00") and gauge venue size from descriptions.

**Files:**
- Modify: `backend/app/agents/day_scout.py:112-124` (attraction entries) and `132-143` (dining entries)
- Test: `backend/tests/test_agents.py` (if day scout tests exist, otherwise skip)

**Step 1: Implement the change**

In `backend/app/agents/day_scout.py`, update the attraction entry building (around line 114-124):

```python
for c in filtered_attractions:
    entry = {
        "place_id": c.place_id,
        "name": c.name,
        "rating": c.rating,
        "user_ratings_total": c.user_ratings_total,
        "types": c.types[:3],
        "location": {"lat": c.location.lat, "lng": c.location.lng} if c.location else None,
    }
    if c.suggested_duration_minutes:
        entry["suggested_duration_minutes"] = c.suggested_duration_minutes
    if c.editorial_summary:
        entry["description"] = c.editorial_summary[:120]
    if c.opening_hours:
        # Format a few representative days so LLM can see hours
        _day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        entry["hours"] = [
            f"{_day_names[oh.day]}: {oh.open_time}-{oh.close_time}"
            for oh in c.opening_hours[:3]
        ]
    attractions.append(entry)
```

Apply the same pattern to dining entries (around line 132-143):

```python
for c in dining_candidates[:15]:
    entry = {
        "place_id": c.place_id,
        "name": c.name,
        "rating": c.rating,
        "user_ratings_total": c.user_ratings_total,
        "types": c.types[:3],
        "location": {"lat": c.location.lat, "lng": c.location.lng} if c.location else None,
    }
    if c.suggested_duration_minutes:
        entry["suggested_duration_minutes"] = c.suggested_duration_minutes
    if c.editorial_summary:
        entry["description"] = c.editorial_summary[:120]
    if c.opening_hours:
        _day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        entry["hours"] = [
            f"{_day_names[oh.day]}: {oh.open_time}-{oh.close_time}"
            for oh in c.opening_hours[:3]
        ]
    dining.append(entry)
```

**Step 2: Update the Day Scout system prompt**

Modify `backend/app/prompts/day_plan/day_scout_system.md`, update rule 6 to reference the new data:

```markdown
6. Duration estimates must be realistic — theme parks 6-8h, museums 1-3h, temples 30-90min, parks 1-2h, restaurants 45-90min, cafés 30-45min. Use opening hours (when provided) to avoid scheduling activities that would run past closing time. Use place descriptions to gauge venue size and adjust duration accordingly.
```

**Step 3: Run all tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS (no tests break — this adds data to prompts without changing schemas)

**Step 4: Commit**

```bash
git add backend/app/agents/day_scout.py backend/app/prompts/day_plan/day_scout_system.md
git commit -m "feat(day-scout): pass opening hours and descriptions to LLM for better duration estimates"
```

---

### Task 4: Pass Opening Hours Context to Day Fixer

The Day Fixer currently receives minimal candidate info (`place_id`, `name`, `types`, `rating`) — no opening hours or descriptions. When the reviewer flags "museum scheduled after hours," the fixer can't make informed swaps because it doesn't know *which* candidates are open at what times.

**Files:**
- Modify: `backend/app/agents/day_fixer.py:33-36`
- Test: No new tests needed (schema unchanged, just richer prompt data)

**Step 1: Implement the change**

In `backend/app/agents/day_fixer.py`, update candidate entries (lines 33-36):

```python
candidate_entries = []
_day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
for c in candidates[:30]:
    entry = {"place_id": c.place_id, "name": c.name, "types": c.types[:3], "rating": c.rating}
    if c.opening_hours:
        entry["hours"] = [
            f"{_day_names[oh.day]}: {oh.open_time}-{oh.close_time}"
            for oh in c.opening_hours[:3]
        ]
    if c.editorial_summary:
        entry["description"] = c.editorial_summary[:100]
    candidate_entries.append(entry)
```

**Step 2: Run all tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add backend/app/agents/day_fixer.py
git commit -m "feat(day-fixer): pass opening hours and descriptions to fixer LLM"
```

---

### Task 5: Improve Opening Hours Evaluator — Check Activity End Time

The `OpeningHoursEvaluator` currently only checks if the activity *starts* during opening hours. It should also check if the activity *ends* before closing — an activity starting at 16:00 with 90min duration ends at 17:30, which violates a 17:00 close.

**Files:**
- Modify: `backend/app/algorithms/quality/evaluators.py:703-749`
- Test: `backend/tests/test_quality.py`

**Step 1: Write failing test**

Add to `backend/tests/test_quality.py`:

```python
class TestOpeningHoursEndTimeCheck:
    """Tests that evaluator checks activity END time, not just start."""

    def test_activity_ending_after_close_flagged(self):
        """Activity starting within hours but ending after close should be flagged."""
        act = _make_activity(
            "Museum", "museum", "15:30", 120,  # 15:30 + 120min = 17:30
            opening_hours=["Wed: 09:00 – 17:00"],
        )
        day = _make_day([act], date_str="2026-04-15")  # Wednesday
        evaluator = OpeningHoursEvaluator()
        result = evaluator.evaluate([day])
        assert any("17:00" in (i.description or "") for i in result.issues), \
            "Should flag activity ending after 17:00 close"

    def test_activity_fitting_within_hours_not_flagged(self):
        """Activity fully within opening hours should not be flagged."""
        act = _make_activity(
            "Museum", "museum", "14:00", 90,  # 14:00 + 90min = 15:30
            opening_hours=["Wed: 09:00 – 17:00"],
        )
        day = _make_day([act], date_str="2026-04-15")  # Wednesday
        evaluator = OpeningHoursEvaluator()
        result = evaluator.evaluate([day])
        assert not result.issues
```

**Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && pytest tests/test_quality.py::TestOpeningHoursEndTimeCheck -v`
Expected: FAIL — evaluator only checks start time

**Step 3: Implement end-time checking**

In `backend/app/algorithms/quality/evaluators.py`, modify `_check_activity()` (around line 703-749). After confirming the start time is valid, also check end time:

```python
def _check_activity(
    self, activity: Activity, date_str: str | None
) -> tuple[str, str | None]:
    opening_hours = activity.place.opening_hours
    if not opening_hours:
        return "unknown", None

    activity_start = _parse_time(activity.time_start)
    if not activity_start:
        return "unknown", None

    activity_end = _parse_time(activity.time_end)

    if not date_str:
        return "unknown", None

    try:
        from datetime import date as _date
        d = _date.fromisoformat(date_str)
        day_abbrev = d.strftime("%a")
    except (ValueError, TypeError):
        return "unknown", None

    day_hours = self._find_day_hours(opening_hours, day_abbrev)

    if day_hours is None:
        return "unknown", None

    if day_hours == "closed":
        return (
            "closed",
            f"'{activity.place.name}' is closed on {day_abbrev}",
        )

    time_windows: list[tuple[time, time]] = day_hours  # type: ignore[assignment]

    # Check if start time falls within any window
    start_valid = any(self._time_in_window(activity_start, w) for w in time_windows)
    if not start_valid:
        hours_str = ", ".join(
            f"{w[0].strftime('%H:%M')}-{w[1].strftime('%H:%M')}" for w in time_windows
        )
        return (
            "closed",
            f"'{activity.place.name}' scheduled at {activity.time_start} but opens {hours_str}",
        )

    # Check if end time exceeds closing time
    if activity_end:
        for window in time_windows:
            if self._time_in_window(activity_start, window):
                close = window[1]
                if activity_end > close:
                    return (
                        "closed",
                        f"'{activity.place.name}' ends at {activity.time_end} but closes at {close.strftime('%H:%M')}",
                    )
                break

    return "valid", None
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_quality.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/algorithms/quality/evaluators.py backend/tests/test_quality.py
git commit -m "feat(evaluator): check activity end time against closing hours"
```

---

### Task 6: Update Fallback Duration Table With Better Defaults

The current fallback table has some values that don't match typical visit patterns (e.g., `temple: 60` when many temples like Kinkaku-ji are 30 min visits; `museum: 90` when many large museums need 120+). Since Google doesn't offer duration data, these defaults matter more.

**Files:**
- Modify: `backend/app/config/planning.py` (the `_FALLBACK_DURATION_BY_TYPE` dict)
- Test: `backend/tests/test_scheduler.py`

**Step 1: Write a test to document the new defaults**

Add to `backend/tests/test_scheduler.py`:

```python
class TestFallbackDurations:
    """Verify fallback duration table has sensible values."""

    def test_temple_default_is_reasonable(self):
        """Temples typically take 30-60 min, default should reflect common case."""
        from app.config.planning import DURATION_BY_TYPE
        assert 30 <= DURATION_BY_TYPE.get("temple", 0) <= 60

    def test_museum_default_is_generous(self):
        """Museums typically need 90-120 min for a good visit."""
        from app.config.planning import DURATION_BY_TYPE
        assert 90 <= DURATION_BY_TYPE.get("museum", 0) <= 120

    def test_shrine_has_entry(self):
        """Shinto shrines should have their own duration entry."""
        from app.config.planning import DURATION_BY_TYPE
        assert "shinto_shrine" in DURATION_BY_TYPE
        assert "buddhist_temple" in DURATION_BY_TYPE

    def test_observation_deck_has_entry(self):
        """Observation decks (Shibuya Sky, etc.) should have duration entry."""
        from app.config.planning import DURATION_BY_TYPE
        assert "observation_deck" in DURATION_BY_TYPE
```

**Step 2: Implement updated fallback table**

In `backend/app/config/planning.py`, update the `_FALLBACK_DURATION_BY_TYPE` dict. Add missing types that commonly appear in Japan/Asia trips and adjust existing values:

Add these entries to the existing dict (don't replace the whole table — just add/update):

```python
# Religious — split by type for accuracy
"shinto_shrine": 45,
"buddhist_temple": 45,
"hindu_temple": 45,
"synagogue": 30,

# Viewpoints
"observation_deck": 60,
"scenic_spot": 45,

# Activities
"cultural_center": 60,
"aquarium": 120,
"water_park": 240,

# Quick stops
"bridge": 15,
"sculpture": 15,
"historical_landmark": 30,
"tourist_attraction": 60,
```

Also update `"castle": 90` (up from whatever it is, castles like Himeji need 90-120 min).

**Step 3: Run tests to verify**

Run: `cd backend && source venv/bin/activate && pytest tests/test_scheduler.py::TestFallbackDurations -v`
Expected: ALL PASS

Run full suite: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add backend/app/config/planning.py backend/tests/test_scheduler.py
git commit -m "feat(planning): expand fallback duration table with shrine, observation_deck, etc."
```

---

### Task 7: Update CLAUDE.md

Document the changes for future sessions.

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Design Principles section**

Add to the Design Principles paragraph in CLAUDE.md:

After "Duration estimation priority: 1) LLM estimate, 2) Google Places `suggested_duration_minutes`, 3) fallback table." add:

```
Note: Google Places API v1 does not offer a duration field — tier 2 is reserved for future API additions. The scheduler enforces opening hours as a hard constraint: activities are truncated or skipped if they would end after closing time. Opening hours flow from `PlaceCandidate` through to `Activity.place.opening_hours` as formatted strings for evaluator accuracy. Day Scout and Day Fixer LLMs receive opening hours and editorial summaries as grounding context for better duration estimates.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document opening hours enforcement and duration grounding"
```

---

## Summary of Changes

| Task | Priority | Files Changed | Tests Added |
|------|----------|---------------|-------------|
| 1. Enforce closing time | P0 | `scheduler.py` | 4 tests |
| 2. Pass opening hours to Activity | P0 | `scheduler.py` | 1 test |
| 3. Ground Day Scout with hours/descriptions | P1 | `day_scout.py`, `day_scout_system.md` | 0 (prompt change) |
| 4. Ground Day Fixer with hours/descriptions | P1 | `day_fixer.py` | 0 (prompt change) |
| 5. Evaluator checks end time | P1 | `evaluators.py` | 2 tests |
| 6. Expand fallback duration table | P2 | `planning.py` | 4 tests |
| 7. Update CLAUDE.md | P2 | `CLAUDE.md` | 0 |

**Total: 7 tasks, 11 new tests, 7 files modified**
