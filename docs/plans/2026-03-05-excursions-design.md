# Excursions & Special Experiences — Design

## Problem

The current day plan model treats every activity as a 1-3 hour slot within a single day. This can't represent full-day experiences (Disney, safaris), multi-day excursions (Ha Long Bay cruises, Sapa treks), half-day tours (cooking classes, wine tours), or evening experiences (dinner cruises, night shows).

## Decision

LLM-driven (no new API). Scout marks excursions in highlights. DayPlanOrchestrator blocks the appropriate days/slots. DayPlanner only schedules remaining unblocked time.

## Supported Types

| Type | Example | Behavior |
|------|---------|----------|
| `full_day` | Disney, safari, day cruise | Blocks entire day, single excursion activity |
| `half_day_morning` | Cooking class, market tour | Blocks morning, afternoon has normal activities |
| `half_day_afternoon` | Wine tour, boat tour | Blocks afternoon, morning has normal activities |
| `multi_day` | Ha Long Bay cruise, Sapa trek | Blocks 2-3 consecutive days, no normal scheduling |
| `evening` | Dinner cruise, night show | Normal daytime, excursion fills evening |

## Data Model Changes

### CityHighlight (journey.py)

Add 2 optional fields:

```python
class CityHighlight(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    suggested_duration_hours: float | None = None
    excursion_type: str | None = None   # null, "full_day", "half_day_morning", "half_day_afternoon", "multi_day", "evening"
    excursion_days: int | None = None   # only for multi_day (e.g., 2 for a 2-day cruise)
```

### DayPlan (day_plan.py)

Add excursion flag:

```python
class DayPlan(BaseModel):
    # ... existing fields ...
    is_excursion: bool = False
    excursion_name: str | None = None  # "Ha Long Bay Cruise - Day 1 of 2"
```

No changes to AIPlan, DayGroup, or PlaceCandidate.

## Pipeline Flow

### 1. Scout Agent

Prompt gets new "Excursions & Special Experiences" section. Scout marks highlights with `excursion_type` when appropriate. Constraints:
- Max 1 multi-day excursion per city
- Full-day excursions should not exceed half the city's allocated days
- Only mark experiences that genuinely require extended time

### 2. DayPlanOrchestrator

Before calling DayPlanner for a city:

1. Scan `city.highlights` for any with `excursion_type` set
2. Determine which day indices each excursion occupies
3. For fully-blocked days (full_day, multi_day): create pre-built DayPlan with `is_excursion=True`, single activity, no Google Places discovery
4. For partially-blocked days (half_day, evening): pass time constraints to DayPlanner via existing `time_constraints` mechanism
5. Call DayPlanner only for remaining unblocked days/time slots

**Example:** Hanoi, 4 days, Ha Long Bay 2-day cruise:
- Days 1-2: Normal DayPlanner scheduling (Hanoi sightseeing)
- Days 3-4: Pre-built excursion DayPlans, `is_excursion=True`

**Half-day constraints:**
- `half_day_morning` → normal activities get `day_start_time = 14:00`
- `half_day_afternoon` → normal activities get `day_end_time = 12:00`
- `evening` → normal activities get `day_end_time = 17:00`

### 3. DayPlanner Agent

No prompt changes needed. Excursion days bypass DayPlanner entirely. Half-day/evening constraints use existing `time_constraints` mechanism.

## Prompt Changes

### Scout system prompt — new section

```markdown
### EXCURSIONS & SPECIAL EXPERIENCES
Some destinations are famous for experiences that don't fit a normal day schedule:

- **full_day**: Theme parks, safaris, day cruises, island day-trips
- **half_day_morning**: Cooking classes, market tours, morning snorkeling
- **half_day_afternoon**: Wine tours, afternoon boat tours
- **multi_day**: Ha Long Bay cruises, Sapa treks, desert camping (set excursion_days)
- **evening**: Dinner cruises, night markets, traditional shows

Mark in highlights with excursion_type and excursion_days (multi_day only).
Only for experiences that genuinely require extended time.
Max 1 multi_day excursion per city. Full-day excursions ≤ half the city's days.
```

### DayPlanner prompt

No changes. Excursion days bypass DayPlanner. Half-day constraints flow through existing time_constraints.

## Frontend Display

`DayTimeline` handles `is_excursion` days:
- Single card with excursion name, description, estimated cost
- No time slots, no route maps
- Multi-day: "Day 1 of 2" / "Day 2 of 2" labels
- Half-day: excursion block + normal activities for the other half

## Testing

- Scout: valid excursion_type values, excursion_days > 0 for multi_day
- Orchestrator: day-blocking (4-day city + 2-day excursion → DayPlanner gets 2 days)
- Orchestrator: half-day constraint passing to DayPlanner
- Orchestrator: excursion days produce DayPlan with is_excursion=True
- Frontend: excursion day rendering vs normal day rendering

## Files Changed

| File | Change |
|------|--------|
| `app/models/journey.py` | Add `excursion_type`, `excursion_days` to CityHighlight |
| `app/models/day_plan.py` | Add `is_excursion`, `excursion_name` to DayPlan |
| `app/prompts/journey/scout_system.md` | Add excursions section |
| `app/orchestrators/day_plan.py` | Excursion day-blocking logic before DayPlanner call |
| `frontend/src/components/trip/DayTimeline.tsx` | Excursion day rendering |
| `tests/test_agents.py` | Excursion validation tests |
| `tests/test_integration.py` | End-to-end excursion flow tests |
