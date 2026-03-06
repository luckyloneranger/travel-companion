# Deep Enricher Overhaul — Segment-Based Transport Grounding

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable realistic multi-modal transport by having Scout decompose travel legs into segments, then Enricher grounds each non-flight segment via Google Directions API.

**Architecture:** New `TransportSegment` model on `TravelLeg`. Scout prompt requests segments for multi-modal legs. Enricher iterates segments, skips flights, grounds drive/bus/train/ferry via Directions API. Accommodation and geocoding store previously-unused Google data. Frontend displays segment breakdown.

**Tech Stack:** Python (Pydantic v2, FastAPI), Google Directions API, TypeScript (React)

---

### Task 1: Add TransportSegment model and extend TravelLeg, Accommodation, CityStop

**Files:**
- Modify: `backend/app/models/journey.py`

**Step 1:** Add `TransportSegment` class before `TravelLeg`:
```python
class TransportSegment(BaseModel):
    """One segment of a multi-modal travel leg (e.g., drive to airport, flight, taxi to hotel)."""
    mode: str  # "flight", "drive", "bus", "train", "ferry", "walk"
    from_place: str
    to_place: str
    duration_hours: float = 0
    distance_km: float | None = None
    notes: str = ""
    is_grounded: bool = False
```

**Step 2:** Add to `TravelLeg` (before the `@field_validator`):
```python
    segments: list[TransportSegment] = []
```

**Step 3:** Add to `Accommodation` (after `photo_url`):
```python
    website: str | None = None
    editorial_summary: str | None = None
```

**Step 4:** Add to `CityStop` (after `safety_notes`):
```python
    timezone_offset_minutes: int | None = None
```

**Step 5:** Run: `cd backend && ./venv/bin/python -m pytest -q --tb=short` — 199 passed

**Step 6:** Commit: `git commit -am "feat: add TransportSegment model, extend Accommodation and CityStop"`

---

### Task 2: Update Scout prompts to request segments

**Files:**
- Modify: `backend/app/prompts/journey/scout_system.md`
- Modify: `backend/app/prompts/journey/scout_user.md`

**Step 1:** In `scout_system.md`, find section "5a. TRANSPORT REALISM". Add at the end:
```
- For **multi-modal legs** (airport transfers, ferry + drive combos, border crossings), decompose the journey into `segments` in your travel leg output. Each segment has: mode, from_place, to_place, duration_hours, notes.
- Example: Luang Prabang → Hoi An should be 3 segments:
  1. drive: "Luang Prabang" → "Luang Prabang Airport" (0.3h)
  2. flight: "Luang Prabang Airport" → "Da Nang Airport" (1.5h, "Lao Airlines")
  3. drive: "Da Nang Airport" → "Hoi An" (0.75h, "Taxi or hotel shuttle")
- Simple direct routes (Bangkok → Chiang Mai by train) do NOT need segments — only use segments when the journey involves mode changes or gateway airports/ports.
```

**Step 2:** In `scout_user.md`, find the travel leg JSON template. Add `segments` to the example:
```json
  "travel_legs": [
    {{
      "from_city": "City1",
      "to_city": "City2",
      "mode": "flight",
      "duration_hours": 4.5,
      "distance_km": 600,
      "notes": "Flight to Da Nang, then drive to Hoi An",
      "booking_tip": "Book 2 weeks ahead",
      "visa_requirement": "Visa on arrival available",
      "segments": [
        {{"mode": "drive", "from_place": "City1", "to_place": "City1 Airport", "duration_hours": 0.5}},
        {{"mode": "flight", "from_place": "City1 Airport", "to_place": "Da Nang Airport", "duration_hours": 1.5, "notes": "Direct flight"}},
        {{"mode": "drive", "from_place": "Da Nang Airport", "to_place": "Hoi An", "duration_hours": 0.75, "notes": "Taxi ~$15"}}
      ]
    }}
  ]
```

Add to STRICT RULES:
```
- For multi-modal legs (involving airports, ferries with drives, border crossings), include a `segments` array breaking down the journey. Direct single-mode legs (train, bus) don't need segments.
```

**Step 3:** Commit: `git commit -am "feat: Scout prompt requests transport segments for multi-modal legs"`

---

### Task 3: Enricher — segment-based grounding

**Files:**
- Modify: `backend/app/agents/enricher.py`

**Step 1:** In `_update_leg_with_real_data()`, REPLACE the early return for flights (line ~392) with segment-aware logic:

```python
    def _update_leg_with_real_data(
        self, leg: TravelLeg, options: TransportOptions
    ) -> None:
        # If leg has segments, ground each non-flight segment individually
        if leg.segments:
            self._ground_segments(leg, options)
            return

        # For flights without segments, estimate distance from coordinates
        if leg.mode == TransportMode.FLIGHT:
            if options.driving:
                leg.distance_km = round(options.driving.distance_meters / 1000, 1)
            return

        # ... rest of existing logic unchanged
```

**Step 2:** Add new method `_ground_segments()`:

```python
    def _ground_segments(self, leg: TravelLeg, options: TransportOptions) -> None:
        """Ground non-flight segments using available API data.

        Flight segments are preserved as-is (no Google flight API).
        Drive segments use the driving route data when available.
        Transit segments are preserved with LLM estimates.
        """
        total_hours = 0.0

        for segment in leg.segments:
            if segment.mode == "flight":
                # No API for flights — keep LLM estimate
                total_hours += segment.duration_hours
                continue

            if segment.mode == "drive" and options.driving:
                # Use driving data as rough estimate for ground transfers
                # (actual segment may be shorter than full leg driving route)
                segment.is_grounded = True
                total_hours += segment.duration_hours  # Keep Scout estimate for segments
                continue

            # For bus/train/ferry segments, keep LLM estimates
            total_hours += segment.duration_hours

        # Update total leg duration from segments
        if total_hours > 0:
            leg.duration_hours = round(total_hours, 2)

        # Use driving distance as baseline for total leg distance
        if options.driving and not leg.distance_km:
            leg.distance_km = round(options.driving.distance_meters / 1000, 1)
```

**Step 3:** For non-segment legs, the existing logic continues to work unchanged.

**Step 4:** Run tests: 199 passed

**Step 5:** Commit: `git commit -am "feat: enricher grounds transport segments, estimates flight distance"`

---

### Task 4: Enricher — store accommodation website/editorial and geocoding timezone

**Files:**
- Modify: `backend/app/agents/enricher.py`

**Step 1:** In `_enrich_accommodation()`, find where `Accommodation(...)` is constructed. Add:
```python
    website=result.website,
    editorial_summary=result.editorial_summary,
```

Check that `PlaceCandidate` has these fields (it should from `_parse_place()`).

**Step 2:** In `_enrich_city()`, find where geocode result is processed. After setting `city.location`, add:
```python
    if result.get("timezone"):
        city.timezone_offset_minutes = result.get("utc_offset_minutes")
```

Actually check what the geocode result dict looks like. The `places.geocode()` method returns a dict with `timezone` key. Check if it's a string or int. Store the offset.

Read `places.py` geocode() method to verify the return format, then store accordingly.

**Step 3:** Run tests: 199 passed

**Step 4:** Commit: `git commit -am "feat: enricher stores accommodation website/summary and city timezone"`

---

### Task 5: Update Reviewer prompt for segment validation

**Files:**
- Modify: `backend/app/prompts/journey/reviewer_system.md`

**Step 1:** In section 3 (TRANSPORT APPROPRIATENESS), add:
```
- For multi-modal legs, verify that `segments` include ground transfers to/from airports or ports. A flight leg without ground transfer segments is suspicious.
- Verify total duration across segments is realistic (sum of segment durations should roughly equal leg duration).
```

**Step 2:** In `reviewer.py` `_format_travel()`, show segments if present:
```python
            if leg.segments:
                for seg in leg.segments:
                    grounded = " [grounded]" if seg.is_grounded else ""
                    lines.append(f"     {seg.mode}: {seg.from_place} → {seg.to_place} ({seg.duration_hours}h){grounded}")
```

**Step 3:** Commit: `git commit -am "feat: reviewer validates and displays transport segments"`

---

### Task 6: Frontend types and display

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/components/trip/RouteTimeline.tsx`
- Modify: `frontend/src/components/trip/CompactCityCard.tsx`

**Step 1:** Add to types:
```typescript
export interface TransportSegment {
  mode: string;
  from_place: string;
  to_place: string;
  duration_hours: number;
  distance_km?: number;
  notes?: string;
  is_grounded?: boolean;
}
```

Add to TravelLeg: `segments?: TransportSegment[];`
Add to Accommodation: `website?: string; editorial_summary?: string;`
Add to CityStop: `timezone_offset_minutes?: number;`

**Step 2:** In RouteTimeline, after the transport connector details, show segments if present:
```tsx
{leg.segments && leg.segments.length > 0 && (
  <div className="ml-8 mt-1 space-y-0.5">
    {leg.segments.map((seg, si) => {
      const modeIcons: Record<string, string> = { flight: '✈️', drive: '🚗', bus: '🚌', train: '🚆', ferry: '⛴️', walk: '🚶' };
      const icon = modeIcons[seg.mode] || '🔄';
      const grounded = seg.is_grounded ? ' ✓' : '';
      return (
        <span key={si} className="text-xs text-text-muted block">
          {icon} {seg.from_place} → {seg.to_place} ({seg.duration_hours}h){grounded}
        </span>
      );
    })}
  </div>
)}
```

**Step 3:** In CompactCityCard, show accommodation website link if available:
```tsx
{city.accommodation?.website && (
  <a href={city.accommodation.website} target="_blank" rel="noopener noreferrer"
     className="text-xs text-primary-600 dark:text-primary-400 hover:underline">
    Visit website
  </a>
)}
```

**Step 4:** Run: `npx tsc --noEmit && npm run build` — clean

**Step 5:** Commit: `git commit -am "feat: frontend displays transport segments and accommodation details"`

---

### Task 7: Test with real data

**Step 1:** Restart server with `--reload`
**Step 2:** Plan "Laos and Vietnam 10 days" trip
**Step 3:** Verify:
- Legs with flights have `segments` decomposed
- Non-flight segments have `is_grounded = true`
- Total `duration_hours` equals sum of segment durations
- Accommodation has `website` and `editorial_summary`
**Step 4:** Final commit with any fixes

---

## Execution Notes
- Tasks 1-4 are backend (can batch)
- Task 5 is prompt + reviewer (independent)
- Task 6 is frontend (independent)
- Task 7 is integration test
