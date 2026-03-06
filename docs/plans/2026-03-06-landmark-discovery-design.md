# Design: Iconic Attraction Coverage — Google-Driven Landmark Discovery

## Problem
Major attractions (Universal Studios Singapore, Mt Fuji, Disneyland Tokyo) are consistently missed because the pipeline optimizes for variety/quality scores over iconic coverage. The system has no grounded data about what's popular — it relies entirely on LLM training knowledge, which inconsistently produces "creative" alternatives over obvious must-sees.

## Approach
Add a pre-Scout "Landmark Discovery" step that queries Google Places for the destination's most-reviewed attractions. Feed this data through ALL downstream stages. Zero hardcoded attraction names — Google's review count data determines what's iconic.

## Pipeline Changes

### 1. Landmark Discovery (NEW — before Scout)
New method in journey orchestrator:
- Queries `text_search_places("top attractions in {destination}")` for each destination
- Sorts results by `user_ratings_total` (review count as prominence proxy)
- Returns top 10 landmarks with name, rating, reviews, types, category

### 2. Scout — Receives Landmarks as Must-Consider
New section in scout_user.md:
```
## DESTINATION'S MOST POPULAR ATTRACTIONS (from Google data)
These are the top attractions by visitor reviews. You MUST consider including
the top-ranked ones in your highlights. If you exclude a top-5 attraction,
explain why in the city's why_visit field.
{landmarks_json}
```

### 3. Reviewer — Validates Landmark Coverage
New validation rule in reviewer_system.md + reviewer receives landmarks in user prompt:
```
### LANDMARK COVERAGE CHECK
Compare plan's highlights against top 5 most-reviewed attractions.
Missing top-5 = major issue (interest_alignment category).
```

### 4. Planner — Receives Landmarks for Fixing
Planner user prompt includes landmark list so it can ADD missing attractions when fixing interest_alignment issues.

### 5. Day Planner Discovery — Text-Search for Landmarks
After normal type-based discovery, text-search for each landmark name to ensure they appear in candidates even if their Google type wasn't searched.

### 6. Day Planner Selection — Must-Include Enforcement
Change "try to include" → "MUST include" for Scout highlights. Day planner validation warns if highlights are missing from selected places.

### 7. Duration Fixes
- amusement_park: 180 → 480 min (full-day parks)
- zoo: 120 → 240 min (4 hours)
- aquarium: 90 → 180 min (3 hours)

## Files to Modify

| File | Change |
|------|--------|
| `orchestrators/journey.py` | Add `_discover_landmarks()` step before Scout, store on orchestrator, pass through pipeline |
| `services/google/places.py` | New `discover_landmarks()` method (text search sorted by reviews) |
| `agents/scout.py` | Accept + pass `landmarks` to prompt template |
| `prompts/journey/scout_user.md` | New `{landmarks_section}` with must-consider language |
| `agents/reviewer.py` | Accept + pass `landmarks` to prompt template |
| `prompts/journey/reviewer_user.md` | New `{landmarks_section}` with coverage check |
| `prompts/journey/reviewer_system.md` | Landmark coverage validation rules |
| `agents/planner.py` | Accept + pass `landmarks` to prompt template |
| `prompts/journey/planner_user.md` | New `{landmarks_section}` |
| `orchestrators/day_plan.py` | Text-search for landmark names in discovery |
| `agents/day_planner.py` | Change "try to include" → "MUST include" |
| `prompts/day_plan/planning_user.md` | Enforce must-include language |
| `config/planning.py` | Fix duration fallbacks for parks/zoos |

## How "Iconic" is Determined (Zero Hardcoding)
Google Places API returns attractions sorted by prominence. Attractions with 10,000+ reviews have earned that status through millions of visitors — not our opinion. The system surfaces what travelers actually visit, not what we think they should.

## Success Criteria
1. Singapore 10-day trip includes Universal Studios
2. Japan 10-day trip includes Mt Fuji area
3. Paris trip includes Louvre, Eiffel Tower
4. No attraction names hardcoded anywhere in prompts or code
5. Works for ANY destination worldwide
