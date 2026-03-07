# Design: Clean Scout / Day Planner Separation — Experience Themes Architecture

## Problem
Scout currently does two jobs: journey-level planning (cities, days, transport) AND activity-level curation (specific attractions, excursion types, durations). This creates a cascade of complexity — we keep beefing up Scout with landmarks, highlights, excursion rules, and duration tables, then fighting to pass this data through to downstream agents that re-discover the same information.

## Core Principle
**Scout decides WHERE to go and HOW LONG. Day Planner decides WHAT to DO there.**

## Architecture

### New Model: ExperienceTheme (replaces CityHighlight for Scout)

```python
class ExperienceTheme(BaseModel):
    theme: str                          # "ha long bay cruise", "street food culture"
    category: str                       # "excursion", "food", "culture", "nature", etc.
    excursion_type: str | None = None   # "full_day", "half_day", "multi_day", "evening"
    excursion_days: int | None = None   # ONLY for multi_day
    distance_from_city_km: float | None = None  # Signals Day Planner search radius
    why: str = ""                       # Brief context for Reviewer/Day Planner
```

CityStop gains: `experience_themes: list[ExperienceTheme] = []`

### Responsibility Matrix

| Responsibility | Scout | Enricher | Reviewer | Day Planner |
|---|---|---|---|---|
| Pick cities | ✅ OWN | Validate/geocode | Validate | — |
| Allocate days per city | ✅ OWN | — | Validate | — |
| Inter-city transport | ✅ OWN | Ground with Google | Validate | — |
| Experience themes per city | ✅ OWN | — | Validate vs landscape | Consume as guidance |
| Excursion intent (multi_day etc) | ✅ Signal | — | Validate | Block days + schedule |
| Specific attraction selection | — | — | — | ✅ OWN |
| Activity duration estimation | — | — | — | ✅ OWN |
| Restaurant/dining selection | — | — | — | ✅ OWN |
| Daily schedule building | — | — | — | ✅ OWN |

### Pipeline Flow

```
1. Pre-Scout: Landscape Discovery (Google)
   - 3 parallel queries per destination ("attractions", "best places", "theme parks")
   - Categorize results by type (theme_parks, nature, cultural, etc.)
   - Feed to Scout as landscape summary (NOT specific must-include names)

2. Scout (LLM)
   - Sees landscape data: "Singapore has theme parks (110K reviews), zoo (51K), gardens (156K)"
   - Outputs: cities + days + transport + experience_themes
   - experience_themes include excursion signals for day-trip/multi-day destinations
   - Does NOT output specific attraction names or durations

3. Enricher (Google APIs)
   - Geocodes cities, enriches accommodation, grounds transport
   - Unchanged — doesn't touch experience_themes

4. Reviewer (LLM)
   - Validates: route, timing, transport, city balance, interest alignment
   - NEW: Validates experience_themes against landscape data
   - Checks: theme count justifies day allocation, excursion_days are realistic

5. Planner (LLM — fix issues)
   - Receives experience_themes + landscape for context when fixing

6. Day Plan Orchestrator (per city)
   a. Extract excursions from experience_themes → block days (existing logic)
   b. Landmark discovery: Google search for city's top attractions by review count
   c. Theme-based discovery: text search per experience_theme
      - For themes with distance_from_city_km > 20: search without radius limit
   d. Type-based discovery: existing interest → Google type search
   e. Merge all candidates, deduplicate
   f. Day Planner LLM receives: experience_themes + landmarks + candidates

7. Day Planner (LLM)
   - Sees: experience_themes (guidance), top landmarks (by reviews), full candidates
   - Builds themed days covering all experience themes
   - Owns: activity selection, excursion detection, duration estimation
   - Prompt: "Build days that cover these experience themes. Prioritize top-reviewed attractions."
```

### Pre-Scout Landscape Discovery

```python
async def discover_destination_landscape(destination: str) -> str:
    """Returns categorized landscape summary for Scout context."""
    # 3 parallel queries (existing multi-query approach)
    all_results = await multi_query_search(destination)

    # Categorize by Google Place types
    categories = categorize_by_type(all_results)

    # Format as landscape summary (NOT numbered must-include list)
    lines = [f"## DESTINATION LANDSCAPE (from Google — use for day allocation, NOT specific attraction selection)"]
    for cat_name, places in categories.items():
        if places:
            top = ", ".join(f"{p['name']} ({p['reviews']:,} reviews)" for p in places[:3])
            lines.append(f"- {cat_name}: {top}")
    return "\n".join(lines)
```

### Day Planner Discovery Expansion

```python
# In DayPlanOrchestrator, per city:

# 1. Landmark discovery (NEW - per city)
city_landmarks = await places.discover_landmarks(city_name)

# 2. Theme-specific discovery (NEW)
for theme in city.experience_themes:
    if theme.distance_from_city_km and theme.distance_from_city_km > 20:
        # Far excursion — text search without radius
        theme_results = await places.text_search_places(
            query=f"{theme.theme} near {city_name}",
            location=city.location,
            radius_meters=int(theme.distance_from_city_km * 1000),
        )
    else:
        # Near attraction — existing radius-based search
        pass  # Covered by type-based discovery

# 3. Existing type-based discovery (unchanged)
candidates = await places.discover_places(location=city.location, interests=interests)

# 4. Merge all
all_candidates = merge_deduplicate(candidates, landmark_candidates, theme_candidates)
```

### Migration Strategy

1. Add `ExperienceTheme` model alongside existing `CityHighlight`
2. `CityStop` gains `experience_themes: list[ExperienceTheme] = []`
3. Scout generates experience_themes (new prompt), stops generating highlights
4. DayPlanOrchestrator reads excursions from experience_themes, falls back to highlights
5. Day Planner receives experience_themes + landmark data
6. Old highlights kept on model for backward compat with stored trips
7. Frontend adapts: show experience_themes on journey view, highlights on day plans

### What Gets Removed from Scout

- Specific attraction names in highlights
- suggested_duration_hours (Day Planner estimates)
- Highlight scaling rules (8-12 for 10 days)
- "MUST include theme parks" language
- Landmark numbered list fed as must-consider

### What Gets Added to Day Planner

- Per-city landmark discovery
- Theme-based text search for excursion destinations
- experience_themes as mandatory coverage guidance
- Top-reviewed attractions prioritization

## Files to Modify

| File | Changes |
|------|---------|
| `models/journey.py` | Add ExperienceTheme, CityStop.experience_themes |
| `agents/scout.py` | Generate experience_themes, remove highlight curation |
| `prompts/journey/scout_system.md` | Replace highlight rules with experience_theme rules |
| `prompts/journey/scout_user.md` | New JSON schema with experience_themes |
| `agents/reviewer.py` | Format experience_themes, validate against landscape |
| `prompts/journey/reviewer_system.md` | Theme validation rules |
| `agents/planner.py` | Format experience_themes |
| `orchestrators/journey.py` | Landscape discovery (replaces landmark discovery) |
| `orchestrators/day_plan.py` | Per-city landmark + theme discovery |
| `agents/day_planner.py` | Accept landmarks + themes, build must-cover prompt |
| `prompts/day_plan/planning_user.md` | Experience themes + landmarks sections |
| `services/google/places.py` | discover_destination_landscape() |
| `config/planning.py` | Duration fixes already done |
| `frontend/src/types/index.ts` | ExperienceTheme type |
| `frontend/src/components/trip/CompactCityCard.tsx` | Show experience_themes |

## Success Criteria

1. Singapore 10-day: Universal Studios and Zoo appear in day plans (via landmark discovery at Day Planner level)
2. Hanoi 5-day: Ha Long Bay 2-day cruise appears (via excursion theme from Scout)
3. Tokyo 10-day: Mt Fuji day trip appears (via excursion theme from Scout)
4. Scout prompt is simpler and shorter (fewer highlight rules)
5. Day Planner produces richer itineraries (direct access to Google landmark data)
6. All 199 tests pass
