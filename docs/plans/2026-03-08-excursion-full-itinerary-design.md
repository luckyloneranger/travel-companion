# Excursion Day Full Itinerary Design

**Date:** 2026-03-08
**Status:** Approved

## Problem

Excursion days (e.g., "Hakone day trip", "Nara day trip") produce a single placeholder activity (9:00–18:00, 540min) instead of a detailed itinerary. The `_build_excursion_day_plan()` method creates a stub that bypasses the entire Day Scout → Reviewer → Fixer quality pipeline.

**Impact:** Users see "Hakone mountain and hot spring escape — explore at your own pace" instead of specific shrines, ropeway, Lake Ashi, hot springs, and dining spots.

## Approach

**Discovery + Pipeline Reuse** — Geocode the excursion destination, discover places there via Google Places API, then feed into the existing Day Scout → Reviewer → Fixer pipeline as a separate batch.

### Data Flow

```
Excursion theme (excursion_type: full_day)
    → Geocode "{excursion.name}" → excursion_location
    → discover_places(excursion_location) + discover_landmarks(excursion.name)
    → excursion_candidates[]
    → Day Scout (1-day batch, theme = excursion theme)
    → Day Reviewer → Day Fixer loop
    → TSP optimize → schedule → routes → weather
    → DayPlan (is_excursion=True, 4-6 activities)
```

## Changes

### 1. New method: `_plan_excursion_days()` in `day_plan.py`

Replaces `_build_excursion_day_plan()` calls in `generate_stream()`. For each blocked excursion day:

1. **Geocode** the excursion destination name via Google Places text search (first result's location)
2. **Discover candidates** at that location using `discover_places()`
3. **Discover landmarks** at that destination using `discover_landmarks()`
4. **Estimate transit time** from `distance_from_city_km` on the theme (1h per 50km, rough)
5. **Run Day Scout** as a 1-day batch with the excursion theme and excursion candidates
6. **Run Day Reviewer → Fixer loop** (same quality pipeline)
7. **Return AIPlan** that can be processed like regular day groups

### 2. Time constraint for transit

Excursion days have less available planning time due to transit:
- `distance_from_city_km` → estimate round-trip transit hours
- Reduce day's available hours accordingly
- Pass as time constraint to Day Scout prompt

### 3. Fallback

If geocoding or discovery fails → fall back to current `_build_excursion_day_plan()` stub (graceful degradation).

### 4. Day Reviewer update

Remove the exception clause that allows 1 activity for excursion days — they now have full itineraries.

## What Stays the Same

- `_extract_excursions()` — still identifies excursions from experience_themes
- `_compute_excursion_schedule()` — still determines which days are blocked
- `map_themes_to_days()` — still assigns excursion themes to blocked days
- `is_excursion=True` flag — preserved on resulting DayPlan
- Frontend rendering — no changes needed
- No new prompts, agents, or models required

## Files Modified

1. `backend/app/orchestrators/day_plan.py` — add `_plan_excursion_days()`, update `generate_stream()` to call it
2. `backend/app/prompts/day_plan/day_reviewer_system.md` — remove excursion exception clause
