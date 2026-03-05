# Excursions & Special Experiences — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support full-day, half-day, multi-day, and evening excursions (Disney, Ha Long Bay cruises, cooking classes, dinner shows) by having Scout mark highlights with excursion metadata and DayPlanOrchestrator block the appropriate days/slots.

**Architecture:** Add `excursion_type` and `excursion_days` fields to `CityHighlight`. Scout prompt instructs LLM to mark highlights as excursions. DayPlanOrchestrator pre-builds `DayPlan` entries for fully-blocked days and passes time constraints for partial days. Frontend renders excursion days with a simplified card.

**Tech Stack:** Pydantic v2 (backend models), FastAPI, pytest, React/TypeScript (frontend), Tailwind CSS

---

### Task 1: Add excursion fields to CityHighlight model

**Files:**
- Modify: `backend/app/models/journey.py:17-22`
- Test: `backend/tests/test_agents.py`

**Step 1: Write failing test**

Append to `backend/tests/test_agents.py`:

```python
class TestCityHighlightExcursion:
    def test_excursion_fields_default_none(self):
        """CityHighlight excursion fields default to None."""
        from app.models.journey import CityHighlight
        h = CityHighlight(name="Test")
        assert h.excursion_type is None
        assert h.excursion_days is None

    def test_excursion_fields_set(self):
        """CityHighlight accepts excursion metadata."""
        from app.models.journey import CityHighlight
        h = CityHighlight(
            name="Ha Long Bay Cruise",
            category="adventure",
            excursion_type="multi_day",
            excursion_days=2,
        )
        assert h.excursion_type == "multi_day"
        assert h.excursion_days == 2

    def test_full_day_excursion(self):
        from app.models.journey import CityHighlight
        h = CityHighlight(name="Disney", excursion_type="full_day")
        assert h.excursion_type == "full_day"
        assert h.excursion_days is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_agents.py::TestCityHighlightExcursion -v`
Expected: FAIL — `excursion_type` field doesn't exist

**Step 3: Add the fields**

In `backend/app/models/journey.py`, modify `CityHighlight`:

```python
class CityHighlight(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    suggested_duration_hours: float | None = None
    excursion_type: str | None = None
    excursion_days: int | None = None
```

**Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_agents.py::TestCityHighlightExcursion -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/journey.py backend/tests/test_agents.py
git commit -m "feat: add excursion_type and excursion_days to CityHighlight"
```

---

### Task 2: Add excursion fields to DayPlan model

**Files:**
- Modify: `backend/app/models/day_plan.py:54-61`
- Modify: `frontend/src/types/index.ts:145-153`

**Step 1: Add fields to backend DayPlan**

In `backend/app/models/day_plan.py`, add to `DayPlan`:

```python
class DayPlan(BaseModel):
    date: str
    day_number: int
    theme: str = ""
    activities: list[Activity] = []
    city_name: str = ""
    weather: Weather | None = None
    daily_cost_usd: float | None = None
    is_excursion: bool = False
    excursion_name: str | None = None
```

**Step 2: Add fields to frontend DayPlan type**

In `frontend/src/types/index.ts`, update the `DayPlan` interface:

```typescript
export interface DayPlan {
  date: string;
  day_number: number;
  theme: string;
  activities: Activity[];
  city_name: string;
  weather: Weather | null;
  daily_cost_usd: number | null;
  is_excursion: boolean;
  excursion_name: string | null;
}
```

Also add `excursion_type` and `excursion_days` to the `CityHighlight` interface:

```typescript
export interface CityHighlight {
  name: string;
  description: string;
  category: string;
  suggested_duration_hours: number | null;
  excursion_type: string | null;
  excursion_days: number | null;
}
```

**Step 3: Run backend tests + frontend build**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_agents.py -v`
Run: `cd frontend && npm run build`
Expected: Both PASS

**Step 4: Commit**

```bash
git add backend/app/models/day_plan.py frontend/src/types/index.ts
git commit -m "feat: add is_excursion and excursion_name to DayPlan model"
```

---

### Task 3: Update Scout system prompt with excursions section

**Files:**
- Modify: `backend/app/prompts/journey/scout_system.md`

**Step 1: Add excursions section**

In `backend/app/prompts/journey/scout_system.md`, add after section "### 6. HIGHLIGHTS For Each Destination" (after line 59):

```markdown
### 6b. EXCURSIONS & SPECIAL EXPERIENCES
Some destinations are famous for experiences that don't fit a standard day itinerary. When a destination has such experiences, mark them in highlights with `excursion_type`:

- **full_day**: Theme parks (Disney, Universal Studios), safaris, day cruises, island day-trips — consumes entire day
- **half_day_morning**: Cooking classes, market tours, morning snorkeling — blocks morning only
- **half_day_afternoon**: Wine tours, afternoon boat tours, sunset cruises — blocks afternoon only
- **multi_day**: Ha Long Bay overnight cruises, Sapa treks, desert camping, Mekong Delta tours — spans 2-3 consecutive days. Set `excursion_days` (e.g., 2)
- **evening**: Dinner cruises, night markets, traditional shows (kabuki, flamenco), pub crawls — evening only, daytime free

Rules:
- Only mark experiences that GENUINELY require extended time — don't mark a 2-hour museum as full_day
- Maximum 1 multi_day excursion per destination
- Full-day excursions must not exceed half the destination's allocated days (e.g., 3-day city → max 1 full_day excursion)
- Set `excursion_type` on the highlight object. Set `excursion_days` only for multi_day type
- Not every destination needs excursions — only include them when the destination is genuinely famous for such experiences
```

**Step 2: Commit**

```bash
git add backend/app/prompts/journey/scout_system.md
git commit -m "feat: add excursions section to Scout system prompt"
```

---

### Task 4: Build excursion day-blocking logic in DayPlanOrchestrator

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`
- Test: `backend/tests/test_agents.py`

**Step 1: Write failing tests for excursion blocking**

Append to `backend/tests/test_agents.py`:

```python
from app.orchestrators.day_plan import DayPlanOrchestrator


class TestExcursionBlocking:
    """Test DayPlanOrchestrator excursion day-blocking helpers."""

    def test_extract_excursions_none(self):
        """No excursions when highlights have no excursion_type."""
        from app.models.journey import CityHighlight
        highlights = [
            CityHighlight(name="Museum", category="culture"),
            CityHighlight(name="Temple", category="religious"),
        ]
        result = DayPlanOrchestrator._extract_excursions(highlights)
        assert result == []

    def test_extract_excursions_full_day(self):
        """Extracts full_day excursion."""
        from app.models.journey import CityHighlight
        highlights = [
            CityHighlight(name="Disney", category="entertainment", excursion_type="full_day"),
            CityHighlight(name="Museum", category="culture"),
        ]
        result = DayPlanOrchestrator._extract_excursions(highlights)
        assert len(result) == 1
        assert result[0].name == "Disney"
        assert result[0].excursion_type == "full_day"

    def test_extract_excursions_multi_day(self):
        """Extracts multi_day excursion with days."""
        from app.models.journey import CityHighlight
        highlights = [
            CityHighlight(name="Ha Long Bay", category="adventure", excursion_type="multi_day", excursion_days=2),
        ]
        result = DayPlanOrchestrator._extract_excursions(highlights)
        assert len(result) == 1
        assert result[0].excursion_days == 2

    def test_build_excursion_day_plan(self):
        """Builds a DayPlan for an excursion day."""
        from app.models.journey import CityHighlight
        excursion = CityHighlight(name="Ha Long Bay Cruise", category="adventure",
                                   excursion_type="multi_day", excursion_days=2)
        plan = DayPlanOrchestrator._build_excursion_day_plan(
            excursion=excursion,
            date_str="2026-06-20",
            day_number=3,
            city_name="Hanoi",
            day_label="Day 1 of 2",
        )
        assert plan.is_excursion is True
        assert plan.excursion_name == "Ha Long Bay Cruise — Day 1 of 2"
        assert plan.city_name == "Hanoi"
        assert plan.day_number == 3
        assert plan.date == "2026-06-20"
        assert plan.theme == "Ha Long Bay Cruise"
        assert len(plan.activities) == 1
        assert plan.activities[0].place.name == "Ha Long Bay Cruise"

    def test_compute_excursion_schedule(self):
        """Computes which day indices are blocked and which are free."""
        from app.models.journey import CityHighlight
        excursions = [
            CityHighlight(name="Ha Long Bay", excursion_type="multi_day", excursion_days=2),
            CityHighlight(name="Cooking Class", excursion_type="half_day_morning"),
        ]
        blocked, partial = DayPlanOrchestrator._compute_excursion_schedule(
            excursions=excursions,
            num_days=5,
        )
        # Multi-day takes last 2 days (indices 3, 4)
        assert len(blocked) == 2
        # Half-day creates a partial constraint on one of the free days
        assert len(partial) == 1
```

**Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_agents.py::TestExcursionBlocking -v`
Expected: FAIL — methods don't exist

**Step 3: Add helper methods to DayPlanOrchestrator**

In `backend/app/orchestrators/day_plan.py`, add these static methods to the `DayPlanOrchestrator` class (before `generate_stream`):

```python
    @staticmethod
    def _extract_excursions(highlights: list[CityHighlight]) -> list[CityHighlight]:
        """Extract highlights that are marked as excursions."""
        return [h for h in highlights if h.excursion_type]

    @staticmethod
    def _build_excursion_day_plan(
        excursion: CityHighlight,
        date_str: str,
        day_number: int,
        city_name: str,
        day_label: str = "",
    ) -> DayPlan:
        """Build a pre-built DayPlan for an excursion day."""
        label = f"{excursion.name} — {day_label}" if day_label else excursion.name
        place = Place(
            place_id=f"excursion-{excursion.name.lower().replace(' ', '-')}",
            name=excursion.name,
            location=Location(lat=0, lng=0),
            category=excursion.category or "excursion",
        )
        activity = Activity(
            time_start="09:00",
            time_end="18:00",
            duration_minutes=540,
            place=place,
            notes=excursion.description,
        )
        return DayPlan(
            date=date_str,
            day_number=day_number,
            theme=excursion.name,
            activities=[activity],
            city_name=city_name,
            is_excursion=True,
            excursion_name=label,
        )

    @staticmethod
    def _compute_excursion_schedule(
        excursions: list[CityHighlight],
        num_days: int,
    ) -> tuple[dict[int, CityHighlight], dict[int, CityHighlight]]:
        """Compute which day indices are fully blocked vs partially blocked.

        Fully-blocked types: full_day, multi_day
        Partially-blocked types: half_day_morning, half_day_afternoon, evening

        Multi-day excursions are placed at the END of the city stay.
        Full-day excursions fill remaining slots from the end.
        Half-day/evening are placed on the earliest free days.

        Returns:
            (blocked, partial) — both are dict mapping day_index -> excursion
        """
        blocked: dict[int, CityHighlight] = {}
        partial: dict[int, CityHighlight] = {}

        # First pass: multi-day excursions (placed at end)
        next_blocked_from_end = num_days - 1
        for exc in excursions:
            if exc.excursion_type == "multi_day":
                days_needed = exc.excursion_days or 2
                for d in range(days_needed):
                    idx = next_blocked_from_end - (days_needed - 1 - d)
                    if 0 <= idx < num_days:
                        blocked[idx] = exc
                next_blocked_from_end -= days_needed

        # Second pass: full-day excursions (placed at end of remaining)
        for exc in excursions:
            if exc.excursion_type == "full_day":
                while next_blocked_from_end in blocked and next_blocked_from_end >= 0:
                    next_blocked_from_end -= 1
                if next_blocked_from_end >= 0:
                    blocked[next_blocked_from_end] = exc
                    next_blocked_from_end -= 1

        # Third pass: half-day/evening (placed on earliest free days)
        free_days = sorted(i for i in range(num_days) if i not in blocked)
        partial_excs = [e for e in excursions if e.excursion_type in ("half_day_morning", "half_day_afternoon", "evening")]
        for exc, day_idx in zip(partial_excs, free_days):
            partial[day_idx] = exc

        return blocked, partial
```

Also add `Location` to the imports from `app.models.common` if not already there.

**Step 4: Run tests**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_agents.py::TestExcursionBlocking -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/orchestrators/day_plan.py backend/tests/test_agents.py
git commit -m "feat: add excursion scheduling helpers to DayPlanOrchestrator"
```

---

### Task 5: Integrate excursion blocking into generate_stream

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py:88-110`

**Step 1: Add excursion handling to the city loop**

In `generate_stream`, after the `city_start` ProgressEvent yield (around line 99), add excursion detection before the place discovery step. The logic:

1. Extract excursions from `city.highlights`
2. Compute blocked/partial day indices
3. For each blocked day index: create pre-built excursion DayPlan, add to `city_plans`
4. For partial days: inject time constraints
5. Only call DayPlanner for the unblocked (free) days count

Insert this block after line 99 (`data={"city": city_name}`), before the place discovery section:

```python
                # ----------------------------------------------------------
                # 0. Handle excursions (full-day, multi-day, half-day, evening)
                # ----------------------------------------------------------
                excursions = self._extract_excursions(city.highlights)
                blocked_days: dict[int, CityHighlight] = {}
                partial_days: dict[int, CityHighlight] = {}
                excursion_plans: list[DayPlan] = []

                if excursions:
                    blocked_days, partial_days = self._compute_excursion_schedule(
                        excursions, city.days,
                    )
                    # Build pre-built DayPlans for fully blocked days
                    for day_idx, exc in sorted(blocked_days.items()):
                        schedule_date = request.start_date + timedelta(days=day_offset + day_idx)
                        if exc.excursion_type == "multi_day":
                            # Find which day of the multi-day this is
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
                    logger.info(
                        "[DayPlanOrchestrator] %s: %d excursion days blocked, %d partial",
                        city_name, len(blocked_days), len(partial_days),
                    )

                # Compute how many days need normal planning
                free_day_count = city.days - len(blocked_days)
```

Then update the `num_days` passed to `self.day_planner.plan_days()` to use `free_day_count` instead of `city.days`. Find the line `num_days=city.days` in the `plan_days()` call and change it to `num_days=free_day_count`.

Also add excursion time constraints for partial days. Before the existing `time_constraints` list building, inject:

```python
                # Add time constraints from partial excursions
                for d_idx, exc in partial_days.items():
                    if exc.excursion_type == "half_day_morning":
                        time_constraints.append({
                            "day_num": d_idx + 1,
                            "reason": f"{exc.name} (morning excursion)",
                            "available_hours": 5,
                        })
                    elif exc.excursion_type == "half_day_afternoon":
                        time_constraints.append({
                            "day_num": d_idx + 1,
                            "reason": f"{exc.name} (afternoon excursion)",
                            "available_hours": 4,
                        })
                    elif exc.excursion_type == "evening":
                        time_constraints.append({
                            "day_num": d_idx + 1,
                            "reason": f"{exc.name} (evening excursion)",
                            "available_hours": 8,
                        })
```

After city plans are built, merge excursion plans with city plans in day-number order. Before `all_plans.extend(city_plans)`:

```python
                # Merge excursion day plans into city plans, sorted by day number
                city_plans.extend(excursion_plans)
                city_plans.sort(key=lambda dp: dp.day_number)
```

Also handle the edge case: if `free_day_count == 0` (all days are excursions), skip the discovery/DayPlanner/scheduling entirely and just yield excursion plans.

**Step 2: Run full test suite**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/app/orchestrators/day_plan.py
git commit -m "feat: integrate excursion day-blocking into DayPlanOrchestrator"
```

---

### Task 6: Render excursion days in frontend DayTimeline

**Files:**
- Modify: `frontend/src/components/trip/DayTimeline.tsx:139-160`

**Step 1: Add excursion day rendering**

In `DayTimeline.tsx`, update the `DayTimeline` component to check `dayPlan.is_excursion` and render a simplified card:

```tsx
export function DayTimeline({ dayPlan, tips }: DayTimelineProps) {
  // Excursion day — simplified rendering
  if (dayPlan.is_excursion) {
    return (
      <div className="rounded-lg border-2 border-accent-300 dark:border-accent-700 bg-accent-50 dark:bg-accent-950/30 p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎯</span>
          <h4 className="text-sm font-semibold text-text-primary">
            {dayPlan.excursion_name || dayPlan.theme}
          </h4>
        </div>
        {dayPlan.activities.length > 0 && dayPlan.activities[0].notes && (
          <p className="text-sm text-text-secondary leading-relaxed">
            {dayPlan.activities[0].notes}
          </p>
        )}
        {dayPlan.daily_cost_usd != null && dayPlan.daily_cost_usd > 0 && (
          <p className="text-sm text-text-muted flex items-center gap-1">
            <DollarSign className="h-3.5 w-3.5" />
            Estimated cost: ~${dayPlan.daily_cost_usd.toFixed(0)}
          </p>
        )}
        <p className="text-sm text-text-muted">
          Full-day experience — no individual activity scheduling
        </p>
      </div>
    );
  }

  const visibleActivities = dayPlan.activities.filter(a => a.duration_minutes > 0);

  if (visibleActivities.length === 0) {
    return (
      <p className="text-sm text-text-muted text-center py-8">No activities planned for this day.</p>
    );
  }

  return (
    <div className="space-y-0">
      {visibleActivities.map((activity, i) => (
        <TimelineActivity
          key={activity.id}
          activity={activity}
          tip={tips[activity.place.place_id]}
          isLast={i === visibleActivities.length - 1}
        />
      ))}
    </div>
  );
}
```

**Step 2: Build frontend**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/components/trip/DayTimeline.tsx
git commit -m "feat: render excursion days with simplified card in DayTimeline"
```

---

### Task 7: Full test suite verification

**Step 1: Run all backend tests**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Run frontend build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: PASS

**Step 3: Verify imports**

Run: `cd backend && source venv/bin/activate && python -c "from app.models.journey import CityHighlight; h = CityHighlight(name='Test', excursion_type='full_day'); print(f'{h.excursion_type}'); from app.models.day_plan import DayPlan; d = DayPlan(date='2026-01-01', day_number=1, is_excursion=True, excursion_name='Test Excursion'); print(f'{d.is_excursion}, {d.excursion_name}')"`
Expected: `full_day` and `True, Test Excursion`

**Step 4: Commit any fixes**

```bash
git add -u
git commit -m "fix: resolve any test/build issues from excursions feature"
```
