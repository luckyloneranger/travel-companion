# Scout Data Pipeline Flow-Through — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure Scout's rich curated data (highlights with durations/categories/excursions, accommodation reasoning, seasonal/visa/safety context, booking tips) flows through to all downstream agents and the frontend.

**Architecture:** Update Scout's JSON schema to populate new model fields. Upgrade Reviewer and Planner formatters to pass full highlight details. Inject Scout highlights into Day Planner as must-consider context. Preserve Scout reasoning in Enricher. Display reasoning on frontend.

**Tech Stack:** Python (FastAPI, Pydantic v2), TypeScript (React, Zustand), Markdown prompt templates

---

### Task 1: Add `why` field to Accommodation model

**Files:**
- Modify: `backend/app/models/journey.py`

**Step 1:** Add `why: str = ""` to `Accommodation` model after `name`:
```python
class Accommodation(BaseModel):
    name: str
    why: str = ""  # Scout's reasoning for choosing this hotel
    address: str = ""
    ...
```

**Step 2:** Run: `cd backend && ./venv/bin/python -m pytest -q --tb=short`
Expected: 199 passed (backward compatible — default empty string)

**Step 3:** Commit: `git commit -am "feat: add why field to Accommodation model"`

---

### Task 2: Update Scout user prompt with new fields

**Files:**
- Modify: `backend/app/prompts/journey/scout_user.md`

**Step 1:** Find the JSON example output. Add `seasonal_notes`, `visa_notes`, `altitude_meters`, `safety_notes` to the city example. Add `visa_requirement` to the travel leg example. Add `why` to accommodation example.

Update the city object in the example:
```json
{
  "name": "Kyoto",
  "country": "Japan",
  "days": 3,
  "why_visit": "...",
  "best_time_to_visit": "...",
  "seasonal_notes": "Cherry blossom season Mar-Apr; rainy season Jun-Jul",
  "visa_notes": "Visa-free for most nationalities up to 90 days",
  "altitude_meters": 50,
  "safety_notes": "Very safe for all travelers including solo women",
  ...
  "accommodation": {
    "name": "Hotel Granvia Kyoto",
    "why": "Connected to Kyoto Station, perfect base for day trips",
    "estimated_nightly_usd": 180
  }
}
```

Update the travel leg example to include:
```json
{
  "from_city": "Osaka",
  "to_city": "Kyoto",
  "mode": "train",
  ...
  "visa_requirement": "No visa needed (same country)"
}
```

Add to STRICT RULES:
```
- Each city MUST include seasonal_notes, visa_notes, and safety_notes
- altitude_meters is required for destinations above sea level (use approximate elevation)
- Each accommodation MUST include `why` explaining the choice
- Each travel leg between different countries MUST include `visa_requirement`
```

**Step 2:** Run tests — still 199 passed (prompt-only change)

**Step 3:** Commit: `git commit -am "feat: update Scout JSON schema with rich context fields"`

---

### Task 3: Upgrade Reviewer formatting

**Files:**
- Modify: `backend/app/agents/reviewer.py`

**Step 1:** Replace `_format_cities()` with enriched version:
```python
def _format_cities(self, plan: JourneyPlan) -> str:
    lines = []
    for i, city in enumerate(plan.cities):
        lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
        if city.why_visit:
            lines.append(f"   Why: {city.why_visit}")
        if city.highlights:
            lines.append("   Highlights:")
            total_hours = 0
            for h in city.highlights:
                dur = f", {h.suggested_duration_hours}h" if h.suggested_duration_hours else ""
                cat = f" ({h.category}{dur})" if h.category else ""
                exc = f" [{h.excursion_type}]" if h.excursion_type else ""
                exc_days = f" ({h.excursion_days} days)" if h.excursion_days else ""
                lines.append(f"     - {h.name}{cat}{exc}{exc_days}")
                if h.suggested_duration_hours:
                    total_hours += h.suggested_duration_hours
            available = city.days * 8  # ~8h/day available
            pct = (total_hours / available * 100) if available > 0 else 0
            status = "OK" if pct <= 70 else "OVER 70% limit"
            lines.append(f"   Total highlight hours: {total_hours:.1f}h / {available}h ({pct:.0f}% — {status})")
        if city.accommodation:
            price = f" (${city.accommodation.estimated_nightly_usd}/night)" if city.accommodation.estimated_nightly_usd else ""
            lines.append(f"   Hotel: {city.accommodation.name}{price}")
        if city.best_time_to_visit:
            lines.append(f"   Best time: {city.best_time_to_visit}")
        if city.seasonal_notes:
            lines.append(f"   Seasonal: {city.seasonal_notes}")
        if city.altitude_meters and city.altitude_meters > 1000:
            lines.append(f"   Altitude: {city.altitude_meters:.0f}m")
        if city.safety_notes:
            lines.append(f"   Safety: {city.safety_notes}")
        if city.visa_notes:
            lines.append(f"   Visa: {city.visa_notes}")
        if city.location:
            lines.append(f"   Location: ({city.location.lat:.4f}, {city.location.lng:.4f})")
    return "\n".join(lines) if lines else "No cities specified."
```

**Step 2:** Replace `_format_travel()`:
```python
def _format_travel(self, plan: JourneyPlan) -> str:
    if not plan.travel_legs:
        return "No travel legs."
    lines = []
    for leg in plan.travel_legs:
        detail = f"{leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h"
        if leg.distance_km:
            detail += f", {leg.distance_km}km"
        lines.append(detail)
        if leg.notes:
            lines.append(f"   Notes: {leg.notes}")
        if leg.booking_tip:
            lines.append(f"   Booking: {leg.booking_tip}")
        if leg.visa_requirement:
            lines.append(f"   Visa: {leg.visa_requirement}")
    return "\n".join(lines)
```

**Step 3:** Update `reviewer_system.md` — add after SEASONAL & SAFETY CHECK section:
```
### 7. HIGHLIGHT & EXCURSION VALIDATION (does not contribute to score, but flag as issues)
- Verify total highlight hours per city ≤ 70% of available day hours (city.days × 8h)
- Verify max 1 multi_day excursion per destination
- Verify full_day excursions ≤ 50% of city days
- Verify accommodation price aligns with budget tier (budget: <$100, moderate: $100-300, luxury: $300+)
- Flag mismatches as **major** issues with category `balance`
```

**Step 4:** Run tests. Commit.

---

### Task 4: Upgrade Planner formatting

**Files:**
- Modify: `backend/app/agents/planner.py`

**Step 1:** Replace `_format_cities()` with same enriched version as Reviewer (include highlight details, accommodation price, seasonal/visa/safety).

**Step 2:** Replace `_format_travel()` with enriched version (include booking_tip, visa_requirement).

**Step 3:** Update `planner_user.md` — add to step-by-step process:
```
- When fixing TIME FEASIBILITY: reduce the longest highlights first, or remove an excursion
- When fixing BUDGET: suggest cheaper accommodation or remove expensive excursions
- Preserve seasonal_notes, visa_notes, altitude_meters, safety_notes from the original plan
```

**Step 4:** Run tests. Commit.

---

### Task 5: Inject Scout highlights into Day Planner

**Files:**
- Modify: `backend/app/agents/day_planner.py`
- Modify: `backend/app/prompts/day_plan/planning_user.md`
- Modify: `backend/app/orchestrators/day_plan.py`

**Step 1:** Update `plan_days()` signature — add parameters:
```python
async def plan_days(
    self,
    candidates, city_name, num_days, interests, pace,
    budget="moderate", daily_budget_usd=None, must_include=None,
    time_constraints=None, travelers_description="1 adult",
    country="",
    highlights=None,           # NEW: Scout's curated highlights
    best_time_to_visit="",     # NEW: Scheduling hints
    hotel_location=None,       # NEW: Accommodation coordinates
) -> AIPlan:
```

**Step 2:** Update `_build_user_prompt()` to accept and inject these:
```python
def _build_user_prompt(self, ..., highlights=None, best_time_to_visit="", hotel_location=None):
    ...
    # Build scout highlights section
    scout_highlights_section = ""
    if highlights:
        lines = ["## SCOUT'S RECOMMENDED HIGHLIGHTS (prioritize including these)"]
        for h in highlights:
            dur = f", {h.suggested_duration_hours}h" if h.suggested_duration_hours else ""
            desc = f': "{h.description}"' if h.description else ""
            exc = f" [{h.excursion_type}]" if h.excursion_type else ""
            lines.append(f"- {h.name}{desc} ({h.category}{dur}){exc}")
        scout_highlights_section = "\n".join(lines)

    scheduling_hints = ""
    if best_time_to_visit:
        scheduling_hints = f"## SCHEDULING HINTS\n{best_time_to_visit}"

    hotel_section = ""
    if hotel_location:
        hotel_section = f"## HOTEL LOCATION\nHotel at ({hotel_location.lat:.4f}, {hotel_location.lng:.4f}) — cluster Day 1 morning activities near hotel"
    ...
```

Add these sections to the template format call.

**Step 3:** Update `planning_user.md` to include placeholders:
```
{scout_highlights_section}

{scheduling_hints}

{hotel_section}
```

**Step 4:** Update `orchestrators/day_plan.py` — pass these to `plan_days()`:
```python
ai_plan = await self.day_planner.plan_days(
    ...,
    highlights=city.highlights if city.highlights else None,
    best_time_to_visit=city.best_time_to_visit or "",
    hotel_location=city.accommodation.location if city.accommodation and city.accommodation.location else None,
)
```

**Step 5:** Run tests. Commit.

---

### Task 6: Enricher preserves Scout reasoning

**Files:**
- Modify: `backend/app/agents/enricher.py`

**Step 1:** In `_enrich_accommodation()`, preserve `why` field:
Find the line `city.accommodation = Accommodation(name=result.name, ...)`.
Before it, save: `llm_why = city.accommodation.why if city.accommodation else ""`
Add to the Accommodation constructor: `why=llm_why`

**Step 2:** In `_enrich_travel_leg()`, preserve `booking_tip`:
Before any leg modification, save: `original_booking_tip = leg.booking_tip`
After enrichment, restore if lost: `if not leg.booking_tip and original_booking_tip: leg.booking_tip = original_booking_tip`

**Step 3:** Run tests. Commit.

---

### Task 7: Frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts`

**Step 1:** Add to `CityStop` interface:
```typescript
seasonal_notes?: string;
visa_notes?: string;
altitude_meters?: number;
safety_notes?: string;
```

Add to `Accommodation` interface:
```typescript
why?: string;
```

Add to `TravelLeg` interface:
```typescript
visa_requirement?: string;
booking_tip?: string;
```

Verify `CityHighlight` already has `description`, `excursion_type`, `excursion_days`.

**Step 2:** Run: `npx tsc --noEmit` — 0 errors

**Step 3:** Commit.

---

### Task 8: Frontend displays Scout reasoning

**Files:**
- Modify: `frontend/src/components/trip/CompactCityCard.tsx`
- Modify: `frontend/src/components/trip/RouteTimeline.tsx`

**Step 1:** In CompactCityCard, after `why_visit`:
```tsx
{city.best_time_to_visit && (
  <p className="text-xs text-text-muted mt-0.5">{city.best_time_to_visit}</p>
)}
```

**Step 2:** On accommodation card, add `title` tooltip:
```tsx
<p className="text-sm font-medium text-text-primary break-words" title={city.accommodation.why || undefined}>
  {city.accommodation.name}
</p>
```

**Step 3:** Add altitude/seasonal/safety badges after accommodation:
```tsx
<div className="flex flex-wrap gap-1.5 mt-1">
  {city.altitude_meters && city.altitude_meters > 2000 && (
    <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
      ⛰️ {city.altitude_meters.toFixed(0)}m
    </span>
  )}
  {city.seasonal_notes && (
    <span className="text-xs text-text-muted" title={city.seasonal_notes}>📅 Seasonal info</span>
  )}
  {city.visa_notes && (
    <span className="text-xs text-text-muted" title={city.visa_notes}>🛂 Visa info</span>
  )}
</div>
```

**Step 4:** In RouteTimeline, show booking_tip and visa:
```tsx
{leg.booking_tip && (
  <span className="text-xs text-text-muted">💡 {leg.booking_tip}</span>
)}
{leg.visa_requirement && (
  <span className="text-xs text-text-muted">🛂 {leg.visa_requirement}</span>
)}
```

**Step 5:** Run: `npx tsc --noEmit && npm run build` — clean

**Step 6:** Commit.

---

### Task 9: Verify full pipeline with curl test

**Step 1:** Restart server with `--reload`
**Step 2:** Plan a multi-country trip (e.g., "Southeast Asia 10 days")
**Step 3:** Verify new fields are populated:
- `seasonal_notes` not null
- `visa_notes` not null
- `altitude_meters` present
- `accommodation.why` not empty
- `travel_leg.visa_requirement` present
**Step 4:** Generate day plans — verify Scout highlights are referenced

**Step 5:** Final commit with all changes.

---

## Execution Notes

- Tasks 1-2 are Scout-side (schema + prompt)
- Tasks 3-4 are Reviewer/Planner (formatting)
- Task 5 is Day Planner (highlight injection)
- Task 6 is Enricher (preservation)
- Tasks 7-8 are Frontend (types + display)
- Task 9 is verification

Tasks 1-6 are backend-only and can be batched. Tasks 7-8 are frontend-only and can be batched separately.
