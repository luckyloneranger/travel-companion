# Multi-Country Journey Quality: Per-Country Discovery + Two-Phase Scout

**Goal:** Improve multi-country trip quality by breaking the single-shot Scout into a two-phase pipeline — a lightweight Country Allocator decides countries/days/entry cities, then per-country landscape discovery runs in parallel, then the existing Scout plans within those constraints.

**Architecture:** Multi-country detection (from must-see results) gates a new pre-Scout phase. Phase 1 is a small structured LLM call (~1500 tokens) that outputs country allocations. Per-country discovery runs the existing `discover_destination_landscape()` once per country in parallel. Phase 2 is the existing Scout with richer per-country context and a hard allocation constraint. Single-country trips are completely unaffected.

**Activation:** Multi-country regions only (SE Asia, Europe, etc.). Single-country trips (Japan, Italy) skip Phase 1 entirely.

---

## Problem

For multi-country trips, the Scout makes all decisions in a single LLM call:
- Which countries to visit
- How many days per country
- Which cities within each country
- Experience themes, accommodation, transport

Meanwhile, landscape discovery runs 4 queries for the entire region (e.g., "landmarks in Southeast Asia"), returning broad cross-country results with poor per-country depth.

**Result:** The Scout operates on thin context and makes structural decisions (country allocation) that are hard to fix in later iterations. The Reviewer catches issues but the Planner can only patch — it can't restructure the country split.

---

## Design

### 1. Multi-Country Detection

**Mechanism:** After the must-see LLM call completes, count distinct countries in the results.

- Add `country: str` field to the `MustSeeAttraction` schema (each attraction already has `city_or_region`, adding `country` is natural)
- If must-see returns attractions in **2+ distinct countries** → multi-country trip → activate two-phase path
- Fallback: if must-see call fails, check destination string against a known multi-country region set: `{"Southeast Asia", "Europe", "Central America", "East Africa", "West Africa", "Middle East", "Scandinavia", "Balkans", "Caribbean", "South America", "Central Asia", "South Asia", "East Asia", "Pacific Islands"}`

**Single-country trips:** Must-see returns all attractions in one country → skip Phase 1 → existing single-shot Scout unchanged.

### 2. Phase 1 — Country Allocator

A lightweight LLM call that runs after must-see detection confirms multi-country.

**Input:**
- Destination region, total days, interests, pace, budget, travelers
- Must-see attractions with countries
- User's must_include / avoid lists
- Origin city

**Output schema:**

```python
class CountryPlan(BaseModel):
    country: str              # "Thailand"
    days: int                 # 5
    entry_city: str           # "Bangkok"
    why: str                  # "Gateway to temples, street food capital"

class CountryAllocation(BaseModel):
    countries: list[CountryPlan]   # 2-4 countries
    routing_order: list[str]       # ["Thailand", "Cambodia", "Vietnam"]
    reasoning: str                 # Brief allocation logic
```

**Prompt rules:**
- Minimum 3 days per country (depth over breadth)
- Maximum 4 countries for <=14 days, 5 for 15-21 days
- Must include countries that contain must-see attractions
- Entry city should be the main international gateway or closest to previous country's exit
- Days should be proportional to attraction density and traveler interests
- Respect user's avoid list (skip countries/cities mentioned)

**LLM config:**
- Temperature: 0.3 (factual allocation, not creative)
- Max tokens: 1500
- Search grounding: follows `should_use_search_grounding("selective")` — same tier as Scout

**Cost:** ~$0.01 per call. **Latency:** ~1-2s.

### 3. Per-Country Landscape Discovery

After Phase 1 returns countries, run full discovery per country in parallel.

**Current (single-destination):**
```
discover_destination_landscape("Southeast Asia")  →  30 landmarks
```

**New (multi-country):**
```
asyncio.gather(
    discover_destination_landscape("Thailand"),
    discover_destination_landscape("Cambodia"),
    discover_destination_landscape("Vietnam"),
)
→  30 landmarks per country = 90 total, organized by country
```

**Formatting:** Landmarks grouped under country headers:

```
## Thailand — Landscape Discovery
### Landmarks & viewpoints
- Grand Palace (4.6★, 89,000 reviews)
...

## Cambodia — Landscape Discovery
### Landmarks & viewpoints
- Angkor Wat (4.8★, 61,000 reviews)
...
```

**Details:**
- Reuses existing `discover_destination_landscape()` — no changes to discovery logic
- 3 countries × 4 queries = 12 parallel Google API calls, ~1s total
- Google API cost: ~$0.06 additional (3x current $0.03)

**Single-country trips:** Unchanged. Still `discover_destination_landscape("Japan")`.

### 4. Phase 2 — Enhanced Scout

The existing Scout, but receiving:
1. **Country allocation as hard constraint** via new `{country_allocation}` placeholder
2. **Per-country landmarks** via existing `{landmarks_context}` placeholder (now richer)

**Country allocation injection:**
```
## COUNTRY ALLOCATION (from pre-planning)
You MUST follow this allocation:
1. Thailand — 5 days, enter via Bangkok
2. Cambodia — 3 days, enter via Siem Reap
3. Vietnam — 5 days, enter via Hanoi

Route order: Thailand → Cambodia → Vietnam
Total: 13 days

Do NOT add, remove, or reorder countries.
Do NOT reallocate days between countries.
You MAY add secondary cities within a country.
Entry city must be the first base in that country.
```

**Scout system prompt addition (new Rule 11):**
```markdown
### Rule 11: Country Allocation Constraint
- If a COUNTRY ALLOCATION section is provided, treat it as a HARD constraint
- Do NOT add, remove, or reorder countries
- Do NOT reallocate days between countries
- You MAY add secondary cities within a country (e.g., Chiang Mai within Thailand's 5 days)
- Entry city must be the first base in that country
```

**What stays the same:**
- Scout output schema (JourneyPlan) unchanged
- Scout still decides cities within countries, themes, accommodation, transport
- Reviewer + Planner loop unchanged
- Search grounding wiring unchanged
- Single-country trips: no `{country_allocation}` injected, Scout behaves exactly as today

**What the Planner can fix:**
- Cities within a country, day distribution within a country, themes, accommodation
- NOT country allocation — that's fixed by Phase 1

### 5. Geographic Context Enhancement

With Phase 1, geographic context gets better input data.

**Current:** Built from must-see cities only (may not match Scout's final choices).

**New (multi-country):** Built from Phase 1 entry cities + must-see cities:
- Phase 1 entry cities are primary nodes (Bangkok, Siem Reap, Hanoi)
- Must-see cities added only if they introduce new locations
- Same geocoding + haversine + nearest-neighbor logic

No new API calls. Just better input data for the existing method.

### 6. Error Handling

Every new step falls back to the existing single-shot pipeline:

| Step | Failure | Fallback |
|------|---------|----------|
| Must-see returns no `country` field | Can't detect multi-country | Region name set lookup |
| Phase 1 LLM call fails | No allocation | Single-shot Scout (current path) |
| Phase 1 returns 1 country | Not multi-country | Single-shot Scout (current path) |
| Per-country discovery fails for one country | Partial data | Use whatever succeeded |
| All per-country discovery fails | No landscape | Fall back to `discover_destination_landscape(destination)` |

**Principle:** Two-phase is an enhancement, not a gate. Any failure degrades gracefully to current behavior.

### 7. Pipeline Timeline

**Current (multi-country):**
```
0s    Landscape("SE Asia") + Must-see     [parallel]
~2s   Must-see done → geographic context
~2.5s Scout (single-shot, thin context)
~90s  Scout done → Enrich → Review → [Planner → Enrich → Review] × 1-2
~180s Complete
```

**New (multi-country):**
```
0s    Landscape("SE Asia") + Must-see     [parallel, for detection]
~2s   Must-see done → detect multi-country
~2s   Phase 1 Country Allocator starts
~4s   Phase 1 done → per-country discovery starts [parallel]
~5s   Per-country discovery done → geographic context
~5s   Scout Phase 2 (rich context, constrained allocation)
~90s  Scout done → Enrich → Review → [fewer Planner iterations expected]
~150s Complete
```

**Net added latency:** ~3s before Scout. Likely offset by fewer Planner iterations (better first pass from richer context).

### 8. Cost Impact

**Multi-country trip (3 countries, 13 days):**

| Resource | Current | New | Delta |
|----------|---------|-----|-------|
| LLM calls pre-Scout | 1 (must-see) | 2 (must-see + allocator) | +$0.01 |
| Google Discovery queries | 4 | 12 (4 per country) | +$0.06 |
| Geocoding calls | 3-5 | 3-5 (same) | $0 |
| Expected Planner iterations | 1-2 | 0-1 | -$0.05-0.10 saved |
| **Net per trip** | | | **~neutral** |

**Single-country trips:** Zero change.

---

## Files Affected

| File | Change |
|------|--------|
| `app/models/journey.py` | Add `country` field to `MustSeeAttraction` |
| `app/prompts/journey/must_see_system.md` | Instruct LLM to include country per attraction |
| `app/prompts/journey/must_see_user.md` | Add country to output requirements |
| `app/orchestrators/journey.py` | Multi-country detection, Phase 1 call, per-country discovery, enhanced context wiring |
| `app/agents/scout.py` | Accept `country_allocation` parameter, pass to prompt |
| `app/prompts/journey/scout_system.md` | Add Rule 11 (country allocation constraint) |
| `app/prompts/journey/scout_user.md` | Add `{country_allocation}` placeholder |
| `app/prompts/journey/country_allocator_system.md` | New prompt |
| `app/prompts/journey/country_allocator_user.md` | New prompt |
| `app/config/planning.py` | Allocator LLM config, multi-country region set |
| `tests/test_agents.py` | Tests for detection, allocation, per-country discovery, fallbacks |

---

## Success Criteria

1. SE Asia 15-day trip: Scout produces plan with 3 countries, no backtracking, realistic day allocation on first pass
2. Europe 10-day trip: Scout covers 2-3 countries with proportional days
3. Japan 10-day trip (single-country): Zero change in behavior, identical pipeline
4. Phase 1 failure: Graceful fallback to single-shot Scout, trip still completes
5. All existing 259+ tests pass without modification
