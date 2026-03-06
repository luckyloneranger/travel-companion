# Design: Scout Data Pipeline — Full Stack Flow Through

## Problem
Scout generates rich, curated data (highlights with descriptions/durations/categories, accommodation reasoning, seasonal/visa/safety context, excursion types, booking tips, best visit times) — but downstream agents (Reviewer, Planner, Day Planner, Enricher) either can't see it, don't use it, or accidentally overwrite it. This wastes Scout's intelligence and produces lower-quality trips.

## Approach
"Pass Everything Through" — ensure every piece of Scout data reaches every agent that needs it. No summarization, no re-discovery.

---

## Changes

### 1. Scout Output Schema
**Files:** `scout_user.md`

Update the JSON example to explicitly request new model fields:
- `seasonal_notes` per city (monsoon, hurricane, winter closures)
- `visa_notes` per city (entry requirements, visa-free status)
- `altitude_meters` per city (for >3000m acclimatization warnings)
- `safety_notes` per city (solo traveler, female safety, nightlife safety)
- `visa_requirement` per travel leg (border crossing requirements)

Add these to the example JSON output so the LLM consistently populates them.

### 2. Reviewer — Full Highlight Details + Enriched Context
**Files:** `reviewer.py`, `reviewer_system.md`

#### 2a. Upgrade `_format_cities()` to include:
- Highlight name, category, duration, excursion_type
- Computed time feasibility: `Total highlight hours: X / Y available (Z%)`
- Accommodation name + nightly rate
- `seasonal_notes`, `visa_notes`, `altitude_meters`, `safety_notes`
- `best_time_to_visit`

Example output:
```
1. Cusco, Peru (3 days)
   Why: Gateway to Machu Picchu...
   Highlights:
     - Machu Picchu (history, 8h) [full_day excursion]
     - Sacred Valley Tour (culture, 4h) [half_day_morning]
     - San Pedro Market (food, 1.5h)
   Total highlight hours: 13.5h / 16.8h available (80% — OVER 70% limit)
   Hotel: Belmond Hotel Rio Sagrado ($350/night)
   Seasonal: Dry season May-Oct ideal
   Altitude: 3400m — acclimatization day needed
   Safety: Safe for all travelers
   Visa: Most nationalities visa-free 90 days
   Best time: Morning for Inca sites, evening for market food tours
```

#### 2b. Upgrade `_format_travel()` to include:
- `booking_tip` and `visa_requirement`
- Accommodation price for budget validation

#### 2c. Update `reviewer_system.md`:
- Add explicit instruction: "Verify total highlight hours per city ≤ 70% of available hours"
- Add: "Verify excursion rules: max 1 multi_day per city, full_day ≤ 50% of city days"
- Add: "Verify accommodation price_level fits budget tier (budget: <$100, moderate: $100-300, luxury: $300+)"

### 3. Planner — Full Highlight Details for Rebalancing
**Files:** `planner.py`, `planner_user.md`

#### 3a. Upgrade `_format_cities()` to include:
- Same highlight detail as Reviewer (name, category, duration, excursion_type)
- Accommodation price

#### 3b. Update `planner_user.md`:
- Add instruction: "When fixing TIME FEASIBILITY issues, reduce the longest highlights first or remove an excursion"
- Add: "When fixing BUDGET issues, suggest cheaper accommodation or remove expensive excursions"
- Add: "Preserve the `seasonal_notes`, `visa_notes`, `altitude_meters`, `safety_notes` from the original plan"

### 4. Day Planner — Scout Highlights as Must-Consider Context
**Files:** `day_planner.py`, `planning_user.md`

#### 4a. Inject Scout highlights into day planner prompt:
Add new section to `planning_user.md`:
```
## SCOUT'S RECOMMENDED HIGHLIGHTS
These attractions were curated for this destination. Prioritize including them:
{scout_highlights}
```

Build `scout_highlights` from `city.highlights`:
```
- Colosseum: "Iconic amphitheater — arrive early to beat crowds" (history, 2.5h)
- Roman Forum: "Walk among ancient ruins" (history, 1.5h)
```

#### 4b. Inject scheduling hints:
Add to prompt:
```
## SCHEDULING HINTS
{best_time_to_visit}
```

#### 4c. Inject hotel location for Day 1 proximity:
Add to prompt:
```
## HOTEL LOCATION
{hotel_name} at ({hotel_lat}, {hotel_lng}) — cluster early morning activities near hotel for easy start
```

#### 4d. Update `plan_days()` signature:
Add: `highlights: list[CityHighlight] | None = None`, `best_time_to_visit: str = ""`, `hotel_location: Location | None = None`

#### 4e. Update orchestrator call:
Pass `city.highlights`, `city.best_time_to_visit`, `city.accommodation.location` from `day_plan.py` orchestrator.

### 5. Enricher — Preserve Scout Reasoning
**Files:** `enricher.py`

#### 5a. Preserve `accommodation.why`:
When `_enrich_accommodation()` creates a new `Accommodation(...)`, carry over the LLM's `why` field:
```python
llm_why = city.accommodation.why if city.accommodation else None
# ... build enriched accommodation ...
city.accommodation = Accommodation(..., why=llm_why)
```

#### 5b. Preserve `travel_leg.booking_tip`:
When enriching travel legs, don't overwrite `leg.booking_tip` if the Scout set it.

#### 5c. Preserve new context fields:
Verify `seasonal_notes`, `visa_notes`, `altitude_meters`, `safety_notes` are not cleared during enrichment. (They shouldn't be — Enricher doesn't touch highlight/city metadata — but verify.)

### 6. Frontend — Display Scout Reasoning
**Files:** `CompactCityCard.tsx`, `DayTimeline.tsx`, `JourneyDashboard.tsx`

#### 6a. Show `accommodation.why` as tooltip on hotel card:
Add `title={city.accommodation?.why}` to hotel name element.

#### 6b. Show `best_time_to_visit` below city name:
Add small text below city header: `{city.best_time_to_visit}`.

#### 6c. Show `booking_tip` on travel leg cards:
Below fare/duration, show: `💡 {leg.booking_tip}`.

#### 6d. Show seasonal/safety badges on city cards:
If `seasonal_notes` exists, show amber badge. If `safety_notes` exists, show info icon with tooltip.

#### 6e. Show `highlight.description` on city highlight list:
Currently only names shown. Add descriptions as expandable text or tooltip.

#### 6f. Show `altitude_meters` if >3000m:
Badge: "⛰️ 3,400m altitude" on city header.

#### 6g. Show `visa_requirement` on travel leg cards:
Below route info: "🛂 No visa needed" or "🛂 Visa required — apply 4 weeks ahead".

### 7. Accommodation Model — Add `why` field
**Files:** `journey.py`

`Accommodation` model needs a `why` field (currently not in the model):
```python
class Accommodation(BaseModel):
    name: str
    why: str = ""  # Scout's reasoning for this hotel choice
    ...
```

### 8. Types Update for Frontend
**Files:** `frontend/src/types/index.ts`

Add the new fields to TypeScript types:
- `CityStop`: `seasonal_notes?`, `visa_notes?`, `altitude_meters?`, `safety_notes?`, `best_time_to_visit?`
- `Accommodation`: `why?`
- `TravelLeg`: `visa_requirement?`, `booking_tip?`
- `CityHighlight`: `description?`, `excursion_type?`, `excursion_days?`

---

## Files to Modify (18 files)

| File | Changes |
|------|---------|
| `backend/app/prompts/journey/scout_user.md` | Add new fields to JSON example |
| `backend/app/prompts/journey/reviewer_system.md` | Add highlight/excursion/budget validation rules |
| `backend/app/prompts/journey/planner_user.md` | Add rebalancing instructions |
| `backend/app/prompts/day_plan/planning_user.md` | Add scout_highlights, scheduling hints, hotel location |
| `backend/app/agents/reviewer.py` | Upgrade `_format_cities()` and `_format_travel()` |
| `backend/app/agents/planner.py` | Same upgrade |
| `backend/app/agents/day_planner.py` | Accept + inject highlights, best_time, hotel location |
| `backend/app/agents/enricher.py` | Preserve `accommodation.why` and `booking_tip` |
| `backend/app/orchestrators/day_plan.py` | Pass highlights, best_time, hotel location to day planner |
| `backend/app/models/journey.py` | Add `why` to Accommodation |
| `frontend/src/types/index.ts` | Add new fields to TS types |
| `frontend/src/components/trip/CompactCityCard.tsx` | Show why, best_time, seasonal, safety, altitude, highlight descriptions |
| `frontend/src/components/trip/JourneyDashboard.tsx` | Show booking_tip, visa on route timeline |
| `frontend/src/components/trip/RouteTimeline.tsx` | Show visa_requirement, booking_tip |

---

## Verification
```bash
cd backend && ./venv/bin/python -m pytest -q --tb=short  # 199 tests pass
cd frontend && npx tsc --noEmit && npm run build          # TS + build clean
# Curl test: plan trip, verify new fields populated
```

## Success Criteria
1. Scout populates seasonal_notes, visa_notes, altitude_meters, safety_notes, visa_requirement
2. Reviewer validates: highlight hours ≤ 70%, excursion rules, budget-accommodation alignment
3. Planner receives full highlight details for rebalancing
4. Day Planner receives Scout highlights as must-consider context
5. Enricher preserves accommodation.why and booking_tip
6. Frontend displays all Scout reasoning (tooltips, badges, descriptions)
