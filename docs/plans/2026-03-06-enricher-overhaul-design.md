# Design: Deep Enricher Overhaul — Segment-Based Transport Grounding

## Problem
The enricher skips flights entirely, falls back to driving for cross-border routes, and can't represent multi-modal journeys (flight + ground transfer). This produces unrealistic travel estimates — e.g., "flight" to Hoi An (which has no airport) with no ground transfer time.

## Approach
Scout decomposes travel legs into **transport segments**. Enricher grounds each non-flight segment via Google Directions API. Flights remain as LLM estimates (no Google flight API exists).

## Changes

### 1. New Model: TransportSegment
```python
class TransportSegment(BaseModel):
    mode: str  # "flight", "drive", "bus", "train", "ferry", "walk"
    from_place: str
    to_place: str
    duration_hours: float = 0
    distance_km: float | None = None
    notes: str = ""
    is_grounded: bool = False  # True when enricher validated with Google APIs
```

Add to TravelLeg: `segments: list[TransportSegment] = []`

### 2. Scout Prompt — Request Segments
Update scout_user.md travel leg JSON to include segments array. Add to scout_system.md transport section: "For multi-modal legs (involving airports, ferries + drives, border crossings), decompose into segments."

### 3. Enricher — Ground Non-Flight Segments
For each travel leg with segments:
- Skip segments where mode == "flight"
- For drive/bus/train/ferry segments: query Google Directions API with segment endpoints
- Update segment duration/distance with real data, set is_grounded=True
- Recompute total leg.duration_hours from sum of segment durations

For legs without segments (backward compat): use existing single-mode logic.

### 4. Accommodation — Store Unused Google Data
Add to Accommodation model:
- `website: str | None = None`
- `editorial_summary: str | None = None`

Enricher already fetches these fields — just store them.

### 5. Geocoding — Store Timezone
Add to CityStop: `timezone_offset_minutes: int | None = None`
Enricher already gets utcOffsetMinutes from geocoding — just store it.

### 6. Frontend — Show Segment Breakdown
Add TransportSegment to TypeScript types. Show on route cards:
- Each segment as a row with mode icon, from→to, duration
- "✓" badge for grounded segments
- No badge for flight segments (LLM estimate)

### 7. Reviewer — Validate Segments
Reviewer prompt should check that multi-modal legs have segments and ground transfers are included.

## Files to Modify
- `backend/app/models/journey.py` — TransportSegment, TravelLeg.segments, Accommodation.website/editorial_summary, CityStop.timezone
- `backend/app/agents/enricher.py` — segment-based grounding loop
- `backend/app/agents/scout.py` — no code change (prompt-driven)
- `backend/app/prompts/journey/scout_system.md` — segment decomposition instruction
- `backend/app/prompts/journey/scout_user.md` — segments in JSON example
- `backend/app/prompts/journey/reviewer_system.md` — segment validation
- `frontend/src/types/index.ts` — TransportSegment type
- `frontend/src/components/trip/RouteTimeline.tsx` — segment display
- `frontend/src/components/trip/CompactCityCard.tsx` — accommodation website/summary

## Verification
- Plan trips requiring multi-modal transport (SE Asia, Greek Islands)
- Verify non-flight segments are grounded with real data
- Verify total duration = sum of segments
- All 199 tests pass
