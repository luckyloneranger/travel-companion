# Scout / Day Planner Separation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate Scout (journey-level: cities, days, transport, experience themes) from Day Planner (activity-level: specific attractions, excursions, durations, scheduling) using a new ExperienceTheme model.

**Architecture:** Scout outputs `experience_themes` instead of `highlights` — lightweight category descriptions with excursion signals. Landmark discovery moves to Day Planner stage (per city). Day Planner owns all activity curation using Google data + experience themes as guidance. Backward-compatible migration keeps `highlights` on model for stored trips.

**Tech Stack:** Python (Pydantic v2, FastAPI, Google Places API), TypeScript (React), Markdown prompts

---

### Task 1: Add ExperienceTheme model + CityStop.experience_themes

**Files:**
- Modify: `backend/app/models/journey.py`

**Step 1:** Add `ExperienceTheme` model BEFORE `CityHighlight`:
```python
class ExperienceTheme(BaseModel):
    """A category of experience available at a destination — used by Scout for journey-level planning."""
    theme: str                              # "ha long bay cruise", "street food culture", "theme parks"
    category: str                           # "excursion", "food", "culture", "nature", "adventure", "shopping", "nightlife", "entertainment"
    excursion_type: str | None = None       # "full_day", "half_day", "multi_day", "evening" — ONLY for out-of-city experiences
    excursion_days: int | None = None       # ONLY for multi_day (e.g., 2 for Ha Long Bay cruise)
    distance_from_city_km: float | None = None  # Signals Day Planner to search wider radius
    why: str = ""                           # Brief context: "UNESCO limestone karsts with overnight cruise"
```

**Step 2:** Add to `CityStop` after `highlights`:
```python
    experience_themes: list[ExperienceTheme] = []
```

**Step 3:** Run: `cd backend && ./venv/bin/python -m pytest -q --tb=short` — 199 passed

**Step 4:** Commit: `git commit -am "feat: add ExperienceTheme model and CityStop.experience_themes"`

---

### Task 2: Add discover_destination_landscape() to Places service

**Files:**
- Modify: `backend/app/services/google/places.py`

**Step 1:** Add method after `discover_landmarks()`:
```python
    async def discover_destination_landscape(
        self, destination: str
    ) -> str:
        """Discover what types of experiences a destination offers.

        Returns a formatted landscape summary for Scout context — categorized
        by type (theme parks, nature, cultural, etc.) with top attractions
        by review count. NOT specific must-include names — just landscape intel.
        """
        landmarks = await self.discover_landmarks(destination, max_results=15)
        if not landmarks:
            return ""

        # Categorize by detected types
        categories: dict[str, list[dict]] = {
            "Theme parks & entertainment": [],
            "Nature & wildlife": [],
            "Cultural & historical": [],
            "Religious & spiritual": [],
            "Shopping & markets": [],
            "Landmarks & viewpoints": [],
            "Other attractions": [],
        }

        type_to_category = {
            "amusement_park": "Theme parks & entertainment",
            "theme_park": "Theme parks & entertainment",
            "water_park": "Theme parks & entertainment",
            "zoo": "Nature & wildlife",
            "aquarium": "Nature & wildlife",
            "park": "Nature & wildlife",
            "national_park": "Nature & wildlife",
            "garden": "Nature & wildlife",
            "museum": "Cultural & historical",
            "art_gallery": "Cultural & historical",
            "historical_landmark": "Cultural & historical",
            "monument": "Cultural & historical",
            "temple": "Religious & spiritual",
            "church": "Religious & spiritual",
            "mosque": "Religious & spiritual",
            "hindu_temple": "Religious & spiritual",
            "shopping_mall": "Shopping & markets",
            "market": "Shopping & markets",
            "tourist_attraction": "Landmarks & viewpoints",
        }

        for lm in landmarks:
            placed = False
            for t in lm.get("types", []):
                if t in type_to_category:
                    categories[type_to_category[t]].append(lm)
                    placed = True
                    break
            if not placed:
                categories["Other attractions"].append(lm)

        lines = [
            "## DESTINATION LANDSCAPE (from Google data)",
            f"Top experiences available in {destination} by visitor popularity:",
            "",
        ]
        for cat_name, places in categories.items():
            if places:
                top = ", ".join(
                    f"{p['name']} ({p.get('user_ratings_total', 0):,} reviews)"
                    for p in places[:3]
                )
                lines.append(f"- **{cat_name}**: {top}")

        lines.append("")
        lines.append("Use this landscape to set experience_themes and allocate days appropriately.")
        lines.append("Do NOT copy specific attraction names into experience_themes — describe the experience category instead.")

        return "\n".join(lines)
```

**Step 2:** Run tests — 199 passed

**Step 3:** Commit: `git commit -am "feat: add discover_destination_landscape() for categorized experience intel"`

---

### Task 3: Update Scout prompts for experience_themes

**Files:**
- Modify: `backend/app/prompts/journey/scout_system.md`
- Modify: `backend/app/prompts/journey/scout_user.md`

**Step 1:** In `scout_system.md`, find section 6 (HIGHLIGHTS). Replace entirely with:
```
### 6. EXPERIENCE THEMES — What To Do There
For each destination, provide `experience_themes` — categories of experiences the city offers:
- Each theme describes a TYPE of experience, not a specific attraction name
- Include 5-8 themes per destination (more for longer stays)
- For out-of-city experiences (day trips, multi-day excursions), set `excursion_type` and `distance_from_city_km`
- Categories: "food", "culture", "nature", "adventure", "excursion", "shopping", "nightlife", "entertainment", "beach", "wellness", "religious"

**Excursion themes** (experiences outside the city that need dedicated time):
- `full_day`: Theme parks, safaris, far day trips (set distance_from_city_km)
- `half_day`: Cooking classes, morning snorkeling, afternoon tours
- `multi_day`: Overnight cruises, multi-day treks (set excursion_days)
- `evening`: Night markets, dinner shows, pub crawls

Example for Hanoi (5 days):
- "Old Quarter street food culture" (food)
- "Temple & pagoda heritage" (culture)
- "Ha Long Bay overnight cruise" (excursion, multi_day, 2 days, 170km from city)
- "Ninh Binh rice paddy day trip" (excursion, full_day, 90km from city)
- "Evening water puppets & night market" (nightlife)
```

**Step 2:** Remove section 6b (EXCURSIONS & SPECIAL EXPERIENCES) — its logic is now in section 6 above.

**Step 3:** In `scout_user.md`, find the city JSON template. Replace `highlights` array with:
```json
      "experience_themes": [
        {{
          "theme": "Street food and hawker culture",
          "category": "food",
          "why": "Ancient food stalls across 36 streets of the old quarter"
        }},
        {{
          "theme": "Ha Long Bay overnight cruise",
          "category": "excursion",
          "excursion_type": "multi_day",
          "excursion_days": 2,
          "distance_from_city_km": 170,
          "why": "UNESCO World Heritage limestone karsts with overnight junk boat"
        }}
      ]
```

Update the STRICT RULES to reference experience_themes instead of highlights:
- "Each destination MUST have 5-8 experience_themes"
- "Out-of-city excursions MUST have excursion_type and distance_from_city_km"
- Remove rules about highlight counts and excursion limits

**Step 4:** Run tests — 199 passed

**Step 5:** Commit: `git commit -am "feat: Scout prompts generate experience_themes instead of highlights"`

---

### Task 4: Update Scout agent for experience_themes

**Files:**
- Modify: `backend/app/agents/scout.py`

**Step 1:** Update `_validate_plan()`:
- Remove highlight-related validation (accommodation already has its own check)
- Remove excursion day validation against highlights (now on experience_themes)
- Add: validate each city has at least 3 experience_themes
- Add: validate excursion themes have excursion_type set

```python
# Validate experience themes
for city in plan.cities:
    if len(city.experience_themes) < 3:
        logger.warning(
            "[Scout] City %s has only %d experience themes — adding generic themes",
            city.name, len(city.experience_themes),
        )
        # Add generic themes based on interests if sparse
```

**Step 2:** Keep city-state collapse logic but update to work with experience_themes (merge themes instead of highlights).

**Step 3:** Run tests, commit.

---

### Task 5: Update journey orchestrator — landscape discovery

**Files:**
- Modify: `backend/app/orchestrators/journey.py`

**Step 1:** Replace the current `discover_landmarks()` call with `discover_destination_landscape()`:

```python
# Pre-Scout: Discover destination landscape
landscape_context = ""
try:
    landscape_context = await self.places.discover_destination_landscape(
        request.destination
    )
    if landscape_context:
        logger.info("[Orchestrator] Landscape discovered for %s", request.destination)
except Exception as exc:
    logger.warning("[Orchestrator] Landscape discovery failed: %s", exc)
```

**Step 2:** Pass `landscape_context` (instead of `landmarks_section`) to Scout, Reviewer, Planner.

**Step 3:** Run tests, commit.

---

### Task 6: Update Reviewer for experience_themes

**Files:**
- Modify: `backend/app/agents/reviewer.py`
- Modify: `backend/app/prompts/journey/reviewer_system.md`

**Step 1:** Update `_format_cities()` to show experience_themes instead of highlights:
```python
if city.experience_themes:
    lines.append("   Experience themes:")
    for et in city.experience_themes:
        exc = f" [{et.excursion_type}]" if et.excursion_type else ""
        dist = f" ({et.distance_from_city_km:.0f}km)" if et.distance_from_city_km else ""
        lines.append(f"     - {et.theme} ({et.category}){exc}{dist}")
    # Check theme count vs days
    theme_count = len(city.experience_themes)
    lines.append(f"   Themes: {theme_count} for {city.days} days")
```

Keep the existing highlight formatting as fallback for stored trips:
```python
elif city.highlights:
    # Backward compat for stored trips
    lines.append(f"   Highlights: {', '.join(h.name for h in city.highlights)}")
```

**Step 2:** Update `reviewer_system.md` — replace HIGHLIGHT & EXCURSION VALIDATION with:
```
### 7. EXPERIENCE THEME VALIDATION (does not contribute to score, but flag as issues)
- Each city should have at least 5 experience themes for stays of 3+ days
- Theme count should roughly match day allocation (5 themes for 3 days is OK; 3 themes for 10 days is sparse)
- Excursion themes must have realistic excursion_days (Ha Long Bay = 2, not 5)
- Verify landscape data supports the themes — don't suggest "theme parks" if Google shows none
```

Replace LANDMARK COVERAGE CHECK with:
```
### 8. LANDSCAPE ALIGNMENT CHECK (does not contribute to score, but flag as issues)
- Compare experience_themes against the destination landscape data above
- If the destination has top-reviewed attractions (50,000+ reviews) in categories NOT covered by any theme, flag as **major** issue
- Example: Singapore has Universal Studios (110K reviews) — if no "theme parks" or "entertainment" theme exists, flag it
```

**Step 3:** Run tests, commit.

---

### Task 7: Update Planner for experience_themes

**Files:**
- Modify: `backend/app/agents/planner.py`
- Modify: `backend/app/prompts/journey/planner_user.md`

**Step 1:** Update `_format_cities()` same as Reviewer — show experience_themes with fallback to highlights.

**Step 2:** Update `planner_user.md`:
- Replace "When fixing INTEREST ALIGNMENT: check if top-5 landmarks are missing" with:
  "When fixing INTEREST ALIGNMENT: check if major experience categories from the landscape are missing from experience_themes and add appropriate themes"

**Step 3:** Run tests, commit.

---

### Task 8: Day Plan Orchestrator — per-city landmark + theme discovery

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

**Step 1:** After existing `discover_places()` call, add per-city landmark discovery:
```python
# Per-city landmark discovery (top attractions by review count)
try:
    city_landmarks = await self.places.discover_landmarks(city_name)
    if city_landmarks:
        landmark_candidates = []
        for lm in city_landmarks:
            # Convert raw dict to PlaceCandidate-compatible search
            lm_results = await self.places.text_search_places(
                query=lm["name"] + " " + city_name,
                location=city.location,
                max_results=1,
            )
            landmark_candidates.extend(lm_results)
        # Merge
        existing_ids = {c.place_id for c in candidates}
        for lc in landmark_candidates:
            if lc.place_id not in existing_ids:
                candidates.append(lc)
                existing_ids.add(lc.place_id)
        logger.info("[DayPlanOrchestrator] Added %d landmark candidates for %s",
                    len(landmark_candidates), city_name)
except Exception as exc:
    logger.warning("[DayPlanOrchestrator] Landmark discovery failed for %s: %s", city_name, exc)
```

**Step 2:** Add theme-based discovery for excursion themes with large distance:
```python
# Theme-based discovery for far excursions
if city.experience_themes:
    for et in city.experience_themes:
        if et.distance_from_city_km and et.distance_from_city_km > 20:
            try:
                theme_results = await self.places.text_search_places(
                    query=f"{et.theme} near {city_name}",
                    location=city.location,
                    radius_meters=int(et.distance_from_city_km * 1000),
                    max_results=5,
                )
                for tr in theme_results:
                    if tr.place_id not in existing_ids:
                        candidates.append(tr)
                        existing_ids.add(tr.place_id)
            except Exception:
                pass
```

**Step 3:** Update excursion extraction to read from `experience_themes`:
Find `_extract_excursions()`. Update to read from `city.experience_themes` instead of (or in addition to) `city.highlights`:
```python
@staticmethod
def _extract_excursions(
    city: CityStop,
) -> list:
    """Extract excursion themes from experience_themes (preferred) or highlights (fallback)."""
    excursions = []
    # Prefer experience_themes
    if city.experience_themes:
        for et in city.experience_themes:
            if et.excursion_type:
                excursions.append(CityHighlight(
                    name=et.theme,
                    description=et.why,
                    category=et.category,
                    excursion_type=et.excursion_type,
                    excursion_days=et.excursion_days,
                ))
    # Fallback to highlights for stored trips
    elif city.highlights:
        excursions = [h for h in city.highlights if h.excursion_type is not None]
    return excursions
```

**Step 4:** Pass experience_themes to Day Planner (instead of highlights):
```python
ai_plan = await self.day_planner.plan_days(
    ...
    highlights=city.highlights if city.highlights else None,
    experience_themes=city.experience_themes if city.experience_themes else None,
    ...
)
```

**Step 5:** Run tests, commit.

---

### Task 9: Day Planner agent — receive themes + landmarks

**Files:**
- Modify: `backend/app/agents/day_planner.py`
- Modify: `backend/app/prompts/day_plan/planning_user.md`

**Step 1:** Update `plan_days()` to accept `experience_themes`:
```python
async def plan_days(
    self, ...,
    experience_themes: list | None = None,
    ...
):
```

**Step 2:** Update `_build_user_prompt()` — build experience themes section:
```python
# Build experience themes section (preferred over scout highlights)
themes_section = ""
if experience_themes:
    lines = ["## EXPERIENCE THEMES TO COVER (from journey plan)",
             "Build themed days that cover these experience categories. Ensure every theme gets at least one day.\n"]
    for et in experience_themes:
        exc = f" [{et.excursion_type}]" if hasattr(et, 'excursion_type') and et.excursion_type else ""
        why = f' — "{et.why}"' if hasattr(et, 'why') and et.why else ""
        lines.append(f"- {et.theme} ({et.category}){exc}{why}")
    themes_section = "\n".join(lines)
elif highlights:
    # Fallback: use existing scout highlights section
    ...existing code...
```

**Step 3:** Update `planning_user.md`:
Replace `{scout_highlights_section}` with `{experience_themes_section}` or keep both with fallback.

Actually simpler: build the section in code and inject via same placeholder:
```python
scout_highlights_section = themes_section or scout_highlights_section
```

**Step 4:** Run tests, commit.

---

### Task 10: Frontend — ExperienceTheme type + display

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/components/trip/CompactCityCard.tsx`

**Step 1:** Add TypeScript type:
```typescript
export interface ExperienceTheme {
  theme: string;
  category: string;
  excursion_type?: string;
  excursion_days?: number;
  distance_from_city_km?: number;
  why?: string;
}
```

Add to CityStop: `experience_themes?: ExperienceTheme[];`

**Step 2:** In CompactCityCard, show experience_themes when available (fallback to highlights):
```tsx
{city.experience_themes && city.experience_themes.length > 0 ? (
  <div className="px-4 pb-2 flex flex-wrap gap-x-3 gap-y-1">
    {city.experience_themes.map((et) => (
      <span key={et.theme} className="text-sm text-text-secondary flex items-center gap-1" title={et.why || undefined}>
        <Badge variant="outline" className="text-xs capitalize">{et.category}</Badge>
        {et.theme}
        {et.excursion_type && <span className="text-xs text-accent-500">({et.excursion_type})</span>}
      </span>
    ))}
  </div>
) : !hideHighlights && city.highlights.length > 0 && (
  // ... existing highlights rendering (fallback)
)}
```

**Step 3:** Run: `npx tsc --noEmit && npm run build` — clean

**Step 4:** Commit.

---

### Task 11: Integration test

**Step 1:** Restart server with `--reload`
**Step 2:** Plan Singapore 10-day trip — verify:
  - Scout returns `experience_themes` (not highlights)
  - Themes include "theme parks" (informed by landscape discovery)
  - Day plans include Universal Studios (from per-city landmark discovery)
**Step 3:** Plan Hanoi 5-day trip — verify:
  - Scout returns Ha Long Bay as excursion theme (multi_day, 2 days, 170km)
  - Day plans block 2 days for Ha Long Bay
**Step 4:** Final commit

---

## Execution Notes

**Batch 1** (Tasks 1-2): Models + landscape discovery — independent
**Batch 2** (Tasks 3-5): Scout prompts + agent + orchestrator — sequential
**Batch 3** (Tasks 6-7): Reviewer + Planner — independent of each other
**Batch 4** (Tasks 8-9): Day Plan orchestrator + agent — sequential
**Batch 5** (Task 10): Frontend — independent
**Batch 6** (Task 11): Integration test — depends on all

Can parallelize: Batch 1, then [Batch 2 + Batch 3], then [Batch 4 + Batch 5], then Batch 6
