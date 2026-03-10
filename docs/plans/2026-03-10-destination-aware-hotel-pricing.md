# Destination-Aware Hotel Budget & Alternatives Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace static USD price tables with LLM-generated destination-aware hotel budget ranges, provide 2-3 hotel options per city, and add aggregator booking guidance.

**Architecture:** Scout LLM returns a `budget_range_usd` per city and 2 additional alternative hotel names. Enricher validates all 3 hotels via Google Places. Frontend displays the primary hotel, budget range, alternatives, and a callout to use hotel aggregators. Static price mapping tables and clamping functions are removed.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, React 19, TypeScript, Tailwind CSS v4

---

### Task 1: Update Accommodation Model — Add Budget Range and Alternatives

Add `budget_range_usd` (LLM's destination-aware range) and `booking_hint` fields to the Accommodation model. Add `accommodation_alternatives` to CityStop.

**Files:**
- Modify: `backend/app/models/journey.py:6-17` (Accommodation) and `55-72` (CityStop)
- Modify: `frontend/src/types/index.ts:31-43` (Accommodation) and `66-81` (CityStop)
- Test: `backend/tests/test_budget.py`

**Step 1: Write failing tests**

Add to `backend/tests/test_budget.py`:

```python
class TestAccommodationBudgetRange:
    """Tests for destination-aware budget range fields."""

    def test_accommodation_budget_range(self):
        from app.models.journey import Accommodation
        acc = Accommodation(
            name="Hotel Granvia Kyoto",
            budget_range_usd=[120, 180],
            booking_hint="Search Booking.com for hotels in Kyoto Station area",
        )
        assert acc.budget_range_usd == [120, 180]
        assert acc.booking_hint is not None

    def test_accommodation_budget_range_optional(self):
        from app.models.journey import Accommodation
        acc = Accommodation(name="Some Hotel")
        assert acc.budget_range_usd is None
        assert acc.booking_hint is None

    def test_city_stop_alternatives(self):
        from app.models.journey import CityStop, Accommodation
        from app.models.common import Location
        city = CityStop(
            name="Kyoto", country="Japan", days=3,
            accommodation=Accommodation(name="Hotel A"),
            accommodation_alternatives=[
                Accommodation(name="Hotel B"),
                Accommodation(name="Hotel C"),
            ],
        )
        assert len(city.accommodation_alternatives) == 2

    def test_city_stop_alternatives_default_empty(self):
        from app.models.journey import CityStop
        city = CityStop(name="Tokyo", country="Japan", days=4)
        assert city.accommodation_alternatives == []
```

**Step 2: Implement model changes**

In `backend/app/models/journey.py`, update `Accommodation` (lines 6-17):

```python
class Accommodation(BaseModel):
    name: str
    why: str = ""
    address: str = ""
    location: Location | None = None
    place_id: str | None = None
    rating: float | None = None
    photo_url: str | None = None
    website: str | None = None
    editorial_summary: str | None = None
    price_level: int | None = None
    estimated_nightly_usd: float | None = None
    budget_range_usd: list[float] | None = None
    booking_hint: str | None = None
```

Update `CityStop` (lines 55-72), add after `accommodation`:

```python
    accommodation: Accommodation | None = None
    accommodation_alternatives: list[Accommodation] = []
```

Update `frontend/src/types/index.ts`, `Accommodation` interface:

```typescript
export interface Accommodation {
  name: string;
  why?: string;
  address: string;
  location: Location | null;
  place_id: string | null;
  rating: number | null;
  photo_url: string | null;
  price_level: number | null;
  estimated_nightly_usd: number | null;
  budget_range_usd?: number[] | null;
  booking_hint?: string | null;
  website?: string;
  editorial_summary?: string;
}
```

Update `CityStop` interface, add after `accommodation`:

```typescript
  accommodation: Accommodation | null;
  accommodation_alternatives?: Accommodation[];
```

**Step 3: Run tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_budget.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add backend/app/models/journey.py frontend/src/types/index.ts backend/tests/test_budget.py
git commit -m "feat(models): add budget_range_usd, booking_hint, and accommodation_alternatives"
```

---

### Task 2: Update Scout Prompt — 3 Hotels + Budget Range

Update the Scout prompt and example JSON to output `budget_range_usd`, `booking_hint`, and `accommodation_alternatives`.

**Files:**
- Modify: `backend/app/prompts/journey/scout_system.md:59-62` (Rule 7)
- Modify: `backend/app/prompts/journey/scout_user.md:56-61` (example) and `110-115` (format)

**Step 1: Update Rule 7 in scout_system.md**

Replace Rule 7 (lines 59-62):

```markdown
### Rule 7: Accommodation (MANDATORY)
- Every destination MUST have ONE primary accommodation and TWO alternatives — all with real property names
- Include `budget_range_usd` as [min, max] reflecting realistic nightly rates for THIS specific city and budget tier
  - Budget ranges MUST be destination-aware: $30-60/night in Bangkok is moderate, $150-250/night in Tokyo is moderate
- Include `booking_hint` with specific guidance: mention neighborhood, local booking platforms, and the budget range in local currency
- Include `why` explaining the location advantage
- The primary accommodation is used for day plan simulation; alternatives give the traveler options
```

**Step 2: Update example JSON in scout_user.md**

Replace the accommodation section in the example (around lines 56-61):

```json
      "accommodation": {{
        "name": "Hotel Granvia Kyoto",
        "why": "Connected to Kyoto Station, perfect base for day trips",
        "estimated_nightly_usd": 150,
        "budget_range_usd": [120, 200],
        "booking_hint": "Search Booking.com or Agoda for hotels near Kyoto Station, ¥18,000-30,000/night"
      }},
      "accommodation_alternatives": [
        {{
          "name": "Daiwa Roynet Hotel Kyoto-Shijo Karasuma",
          "why": "Central Shijo location near Nishiki Market, great value",
          "estimated_nightly_usd": 130
        }},
        {{
          "name": "The Thousand Kyoto",
          "why": "Premium hotel with onsen, opposite Kyoto Station",
          "estimated_nightly_usd": 200
        }}
      ]
```

Update the JSON output format template (around lines 110-115) similarly — add `budget_range_usd`, `booking_hint`, and `accommodation_alternatives` to the schema template.

**Step 3: Update strict rules** (around line 140)

Change: `1 accommodation with name + why + estimated_nightly_usd`
To: `1 accommodation with name + why + estimated_nightly_usd + budget_range_usd + booking_hint, plus 2 accommodation_alternatives`

**Step 4: Run tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/prompts/journey/scout_system.md backend/app/prompts/journey/scout_user.md
git commit -m "feat(scout): prompt for 3 hotels with destination-aware budget range and booking hint"
```

---

### Task 3: Enricher — Enrich All 3 Hotels

Update the enricher to validate all 3 accommodation options (primary + 2 alternatives) via Google Places.

**Files:**
- Modify: `backend/app/agents/enricher.py:190-201` (enrich_accommodations loop) and `202-310`

**Step 1: Update `_enrich_accommodations` to handle alternatives**

In `backend/app/agents/enricher.py`, find `_enrich_accommodations` (around line 190). Update it to also enrich alternatives:

```python
    async def _enrich_accommodations(self, plan: JourneyPlan, budget_tier: str = "moderate") -> None:
        tasks = []
        for city in plan.cities:
            if city.accommodation and city.accommodation.name:
                tasks.append(self._enrich_accommodation(city, budget_tier=budget_tier))
            # Enrich alternatives too
            for alt in city.accommodation_alternatives:
                if alt.name:
                    tasks.append(self._enrich_single_accommodation(alt, city, budget_tier=budget_tier))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

Add a simpler method for enriching a single Accommodation object (alternatives don't need the budget-mismatch search):

```python
    async def _enrich_single_accommodation(
        self, acc: Accommodation, city: CityStop, budget_tier: str = "moderate"
    ) -> None:
        """Enrich a single accommodation with Google Places metadata."""
        city_location = city.location
        if not city_location:
            return

        try:
            query = f"{acc.name} {city.name}"
            result = await self.places.search_lodging(query=query, location=city_location)
            if result and result.rating and result.rating >= 3.0:
                acc.address = result.address
                acc.location = result.location
                acc.place_id = result.place_id
                acc.rating = result.rating
                acc.website = result.website
                acc.editorial_summary = result.editorial_summary
                acc.photo_url = (
                    self.places.get_photo_url(result.photo_reference)
                    if result.photo_reference else None
                )
                logger.info("[Enricher] Enriched alternative for %s: %s", city.name, result.name)
        except Exception as e:
            logger.warning("[Enricher] Alternative enrichment failed for %s: %s", acc.name, e)
```

**Step 2: Simplify `_enrich_accommodation` — remove static price clamping**

In the existing `_enrich_accommodation` method, remove the `adjust_price_for_budget` call and the budget-mismatch alternative search. The LLM's `estimated_nightly_usd` and `budget_range_usd` are now the source of truth. Keep the Google Places lookup for metadata (address, rating, photo, place_id, website).

Replace the price adjustment block (around lines 259-273) with simply preserving the LLM values:

```python
                llm_nightly = city.accommodation.estimated_nightly_usd if city.accommodation else None
                llm_why = city.accommodation.why if city.accommodation else ""
                llm_budget_range = city.accommodation.budget_range_usd if city.accommodation else None
                llm_booking_hint = city.accommodation.booking_hint if city.accommodation else None
```

In the Accommodation constructor, pass through the LLM fields:

```python
                city.accommodation = Accommodation(
                    name=result.name,
                    why=llm_why,
                    address=result.address,
                    location=result.location,
                    place_id=result.place_id,
                    rating=result.rating,
                    price_level=result.price_level,
                    estimated_nightly_usd=llm_nightly,
                    budget_range_usd=llm_budget_range,
                    booking_hint=llm_booking_hint,
                    website=result.website,
                    editorial_summary=result.editorial_summary,
                    photo_url=(...),
                )
```

Remove the `price_level_matches_budget` check and the entire budget-filtered alternative search block that was added in Task 4 of the previous plan.

Remove the `from app.config.planning import adjust_price_for_budget` import.

**Step 3: Run tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS (some budget tests from earlier will need updating — see Task 4)

**Step 4: Commit**

```bash
git add backend/app/agents/enricher.py
git commit -m "feat(enricher): enrich all 3 hotel options, remove static price clamping"
```

---

### Task 4: Clean Up — Remove Static Price Tables and Update Tests

Remove the static price mapping infrastructure from planning.py and update/remove tests that depend on it.

**Files:**
- Modify: `backend/app/config/planning.py:403-479` (remove static tables and functions)
- Modify: `backend/tests/test_budget.py` (remove/update tests)
- Modify: `backend/app/services/google/places.py` (remove `_PRICE_LEVEL_STRINGS` if unused)

**Step 1: Remove from planning.py**

Delete everything from the `# ── Budget ↔ Price Level Mapping` comment (line 403) to the end of the file (line 479). This removes:
- `_PRICE_LEVEL_USD_RANGES`
- `_BUDGET_TARGET_PRICE_LEVELS`
- `_BUDGET_USD_RANGES`
- `get_target_price_levels()`
- `get_budget_usd_range()`
- `get_budget_fallback_nightly()`
- `adjust_price_for_budget()`
- `price_level_matches_budget()`

**Keep `get_budget_fallback_nightly` only** — rename/simplify it as a standalone function with hardcoded sensible defaults (not dependent on the removed tables):

```python
# ── Budget fallback ──────────────────────────────────────────────────

_BUDGET_FALLBACK_NIGHTLY: dict[str, int] = {
    "budget": 50,
    "moderate": 120,
    "expensive": 250,
    "luxury": 400,
}


def get_budget_fallback_nightly(budget: str) -> int:
    """Return a sensible fallback nightly USD when LLM omits accommodation."""
    return _BUDGET_FALLBACK_NIGHTLY.get(budget, 120)
```

**Step 2: Remove/update tests in test_budget.py**

Remove:
- `TestBudgetPriceMapping` class entirely (9 tests — tested functions that no longer exist)
- `TestAccommodationPriceAdjustment` class entirely (3 tests)
- `TestSearchLodgingPriceLevels` class entirely (1 test)

Add replacement test for the simplified fallback:

```python
class TestBudgetFallbackNightly:
    """Tests for budget fallback nightly rates."""

    def test_fallback_values(self):
        from app.config.planning import get_budget_fallback_nightly
        assert get_budget_fallback_nightly("budget") == 50
        assert get_budget_fallback_nightly("moderate") == 120
        assert get_budget_fallback_nightly("expensive") == 250
        assert get_budget_fallback_nightly("luxury") == 400

    def test_fallback_unknown_defaults_moderate(self):
        from app.config.planning import get_budget_fallback_nightly
        assert get_budget_fallback_nightly("unknown") == 120
```

**Step 3: Clean up places.py**

Remove `_PRICE_LEVEL_STRINGS` dict from `backend/app/services/google/places.py` if the enricher no longer uses it for budget-filtered searches. Also remove the `price_levels` parameter from `search_lodging()` if no callers use it anymore.

**Step 4: Run tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/config/planning.py backend/tests/test_budget.py backend/app/services/google/places.py
git commit -m "refactor: remove static price tables, simplify to LLM-driven budget ranges"
```

---

### Task 5: Frontend — Display Budget Range, Alternatives, and Booking Hint

Update the CompactCityCard to show the LLM's budget range, the booking hint callout, and the 2 alternatives from the Scout (instead of the lazy-loaded Google alternatives).

**Files:**
- Modify: `frontend/src/components/trip/CompactCityCard.tsx:165-240`

**Step 1: Update accommodation section in CompactCityCard**

Replace the accommodation display block (around lines 165-240) to:

1. Show primary hotel with budget range instead of just `$X/night`
2. Show a booking hint callout (aggregator guidance)
3. Show alternatives from `city.accommodation_alternatives` instead of the lazy-loaded Google alternatives

Update the price display (around line 186-188):

```tsx
{city.accommodation.budget_range_usd && city.accommodation.budget_range_usd.length === 2 ? (
  <span>${city.accommodation.budget_range_usd[0]}-${city.accommodation.budget_range_usd[1]}/night</span>
) : city.accommodation.estimated_nightly_usd ? (
  <span>${city.accommodation.estimated_nightly_usd}/night</span>
) : null}
```

After the primary hotel block, add the booking hint:

```tsx
{city.accommodation.booking_hint && (
  <p className="text-xs text-text-muted mt-1.5 italic">
    {city.accommodation.booking_hint}
  </p>
)}
```

Replace the lazy-loaded alternatives with `accommodation_alternatives`:

```tsx
{city.accommodation_alternatives && city.accommodation_alternatives.length > 0 && (
  <div className="mt-1.5">
    <button
      type="button"
      onClick={() => setShowAlts(!showAlts)}
      className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
    >
      <ArrowRightLeft className="h-3 w-3" />
      {showAlts ? 'Hide' : 'Show'} alternative hotels
    </button>
    {showAlts && (
      <div className="space-y-1 mt-1.5">
        {city.accommodation_alternatives.map((alt, idx) => (
          <div key={alt.place_id || idx} className="flex items-center gap-2 rounded-md border border-border-default bg-surface-muted/50 p-2 text-xs">
            {alt.photo_url && (
              <img src={photoUrl(alt.photo_url)} alt={alt.name} loading="lazy" className="h-8 w-8 rounded object-cover shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              <p className="font-medium text-text-primary truncate">{alt.name}</p>
              <div className="flex items-center gap-1.5 text-text-muted">
                {alt.rating && (
                  <span className="flex items-center gap-0.5">
                    <Star className="h-2.5 w-2.5 fill-accent-400 text-accent-400" />{alt.rating.toFixed(1)}
                  </span>
                )}
                {alt.estimated_nightly_usd && <span>${alt.estimated_nightly_usd}/night</span>}
              </div>
              {alt.why && <p className="text-text-muted mt-0.5 truncate" title={alt.why}>{alt.why}</p>}
            </div>
            {alt.website && (
              <a href={alt.website} target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline shrink-0">
                Website
              </a>
            )}
          </div>
        ))}
      </div>
    )}
  </div>
)}
```

Remove the `handleShowAlternatives` function and the `loadingAlts`/`alternatives` state that calls the `/api/places/alternatives` endpoint — alternatives now come from the Scout LLM, not a separate API call.

**Step 2: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/trip/CompactCityCard.tsx
git commit -m "feat(frontend): display budget range, booking hint, and LLM alternatives"
```

---

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Design Principles**

Replace the accommodation pricing paragraph added earlier with:

```
Accommodation pricing is destination-aware via LLM: Scout returns `budget_range_usd` ([min, max] nightly) calibrated to the specific city and budget tier (e.g., $30-60 moderate in Bangkok vs $150-250 moderate in Tokyo). Scout also returns 2 `accommodation_alternatives` with names and prices. Enricher validates all 3 hotels via Google Places (metadata only — Google has no hotel pricing API). `booking_hint` directs users to aggregators (Booking.com, Agoda) with destination-specific guidance. Fallback placeholder for missing accommodation uses `get_budget_fallback_nightly()`.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document destination-aware accommodation pricing with alternatives"
```

---

## Summary

| Task | Files Changed | Tests |
|------|---------------|-------|
| 1. Model: budget_range, alternatives | `journey.py`, `types/index.ts` | 4 new |
| 2. Scout prompt: 3 hotels + range | `scout_system.md`, `scout_user.md` | 0 |
| 3. Enricher: enrich 3 hotels | `enricher.py` | 0 |
| 4. Cleanup: remove static tables | `planning.py`, `test_budget.py`, `places.py` | -13 old, +2 new |
| 5. Frontend: display range + alternatives | `CompactCityCard.tsx` | 0 |
| 6. CLAUDE.md | `CLAUDE.md` | 0 |

**Net test change: -13 removed (static price tests) + 4 new (model) + 2 new (fallback) = -7 tests**
**Estimated final count: ~241 tests**
