# Budget-Aware Accommodation Pricing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ground accommodation pricing with budget tier context and Google price_level validation so hotel prices are destination- and budget-appropriate.

**Architecture:** Add a budget config module with price_level↔USD mappings. Pass budget to Scout prompt so LLM calibrates upfront. Enricher validates/adjusts LLM price against Google price_level, and searches for budget-appropriate alternatives when mismatched. Fallback placeholder becomes budget-aware.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pytest

---

### Task 1: Add Budget-to-Price Config Module

Create the budget↔price_level mapping and price adjustment logic as pure functions in planning.py. This is the foundation for all other tasks.

**Files:**
- Modify: `backend/app/config/planning.py`
- Test: `backend/tests/test_budget.py`

**Step 1: Write failing tests**

Add to `backend/tests/test_budget.py`:

```python
class TestBudgetPriceMapping:
    """Tests for budget-to-price-level mapping and price adjustment."""

    def test_budget_to_price_levels(self):
        from app.config.planning import get_target_price_levels
        assert get_target_price_levels("budget") == [1, 2]
        assert get_target_price_levels("moderate") == [2, 3]
        assert get_target_price_levels("expensive") == [3, 4]
        assert get_target_price_levels("luxury") == [4]

    def test_budget_to_price_levels_default(self):
        from app.config.planning import get_target_price_levels
        assert get_target_price_levels("unknown") == [2, 3]

    def test_budget_usd_range(self):
        from app.config.planning import get_budget_usd_range
        lo, hi = get_budget_usd_range("budget")
        assert lo == 30 and hi == 80
        lo, hi = get_budget_usd_range("luxury")
        assert lo == 250 and hi == 600

    def test_budget_fallback_nightly(self):
        from app.config.planning import get_budget_fallback_nightly
        assert get_budget_fallback_nightly("budget") == 55
        assert get_budget_fallback_nightly("moderate") == 140
        assert get_budget_fallback_nightly("luxury") == 425

    def test_adjust_price_clamps_high(self):
        from app.config.planning import adjust_price_for_budget
        # price_level=1 (inexpensive) but LLM says $200 -> clamp to range ceiling
        adjusted = adjust_price_for_budget(200, price_level=1, budget="moderate")
        assert adjusted <= 80  # price_level=1 ceiling

    def test_adjust_price_raises_low(self):
        from app.config.planning import adjust_price_for_budget
        # price_level=4 (very expensive) but LLM says $80 -> raise to range floor
        adjusted = adjust_price_for_budget(80, price_level=4, budget="luxury")
        assert adjusted >= 250  # price_level=4 floor

    def test_adjust_price_no_price_level_keeps_estimate(self):
        from app.config.planning import adjust_price_for_budget
        # No price_level -> keep LLM estimate unchanged
        adjusted = adjust_price_for_budget(170, price_level=None, budget="moderate")
        assert adjusted == 170

    def test_adjust_price_within_range_unchanged(self):
        from app.config.planning import adjust_price_for_budget
        # price_level=2 and LLM says $120 -> within moderate range, keep it
        adjusted = adjust_price_for_budget(120, price_level=2, budget="moderate")
        assert adjusted == 120

    def test_price_level_matches_budget(self):
        from app.config.planning import price_level_matches_budget
        assert price_level_matches_budget(2, "moderate") is True
        assert price_level_matches_budget(1, "luxury") is False
        assert price_level_matches_budget(4, "budget") is False
        assert price_level_matches_budget(None, "moderate") is True  # unknown = match
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_budget.py::TestBudgetPriceMapping -v`
Expected: FAIL — functions don't exist yet

**Step 3: Implement in planning.py**

Add to `backend/app/config/planning.py`:

```python
# ── Budget ↔ Price Level Mapping ─────────────────────────────────────
# Google price_level: 0=free, 1=inexpensive, 2=moderate, 3=expensive, 4=very_expensive
# USD ranges are nightly accommodation estimates per price_level

_PRICE_LEVEL_USD_RANGES: dict[int, tuple[int, int]] = {
    0: (0, 30),
    1: (30, 80),
    2: (80, 200),
    3: (150, 350),
    4: (250, 600),
}

_BUDGET_TARGET_PRICE_LEVELS: dict[str, list[int]] = {
    "budget": [1, 2],
    "moderate": [2, 3],
    "expensive": [3, 4],
    "luxury": [4],
}

_BUDGET_USD_RANGES: dict[str, tuple[int, int]] = {
    "budget": (30, 80),
    "moderate": (80, 200),
    "expensive": (150, 350),
    "luxury": (250, 600),
}


def get_target_price_levels(budget: str) -> list[int]:
    """Return acceptable Google price_levels for a budget tier."""
    return _BUDGET_TARGET_PRICE_LEVELS.get(budget, [2, 3])


def get_budget_usd_range(budget: str) -> tuple[int, int]:
    """Return (min, max) nightly USD range for a budget tier."""
    return _BUDGET_USD_RANGES.get(budget, (80, 200))


def get_budget_fallback_nightly(budget: str) -> int:
    """Return midpoint nightly USD for a budget tier (used as fallback)."""
    lo, hi = get_budget_usd_range(budget)
    return (lo + hi) // 2


def adjust_price_for_budget(
    llm_estimate: float,
    price_level: int | None,
    budget: str,
) -> float:
    """Adjust LLM nightly estimate using Google's price_level as ground truth.

    If price_level is available, clamp the estimate to the USD range for
    that price_level. If not, return the LLM estimate unchanged.
    """
    if price_level is None:
        return llm_estimate

    usd_range = _PRICE_LEVEL_USD_RANGES.get(price_level)
    if not usd_range:
        return llm_estimate

    lo, hi = usd_range
    if llm_estimate < lo:
        return float(lo)
    if llm_estimate > hi:
        return float(hi)
    return llm_estimate


def price_level_matches_budget(
    price_level: int | None, budget: str
) -> bool:
    """Check if a Google price_level is acceptable for the given budget."""
    if price_level is None:
        return True  # unknown = don't reject
    return price_level in get_target_price_levels(budget)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_budget.py::TestBudgetPriceMapping -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/config/planning.py backend/tests/test_budget.py
git commit -m "feat(planning): add budget-to-price-level mapping and price adjustment"
```

---

### Task 2: Pass Budget Tier to Scout Prompt

The Scout prompt has no `{budget}` placeholder, so the LLM can't calibrate accommodation pricing. Add it.

**Files:**
- Modify: `backend/app/prompts/journey/scout_user.md`
- Modify: `backend/app/agents/scout.py:58-74`

**Step 1: Update scout_user.md**

In `backend/app/prompts/journey/scout_user.md`, add `- Budget: {budget}` to the Traveler Profile section (after line 7 "Group:"):

```markdown
**Traveler Profile:**
- Interests: {interests}
- Pace: {pace}
- Group: {travelers_description}
- Budget: {budget}
- Places to include (if any): {must_include}
- Places to avoid (if any): {avoid}
```

**Step 2: Pass budget in scout.py**

In `backend/app/agents/scout.py`, update the `user_prompt` formatting (around line 58-74). Add the budget parameter:

```python
user_prompt = journey_prompts.load("scout_user").format(
    region=request.destination,
    origin=request.origin or "not specified",
    total_days=request.total_days,
    travel_dates=str(request.start_date),
    interests=(
        ", ".join(request.interests) if request.interests else "general sightseeing"
    ),
    pace=request.pace.value,
    travelers_description=request.travelers.summary,
    budget=request.budget.value if request.budget else "moderate",
    must_include=(
        ", ".join(request.must_include) if request.must_include else "none"
    ),
    avoid=", ".join(request.avoid) if request.avoid else "none",
    transport_guidance=transport_guidance,
    landmarks_context=landmarks_context,
)
```

**Step 3: Update the fallback placeholder to be budget-aware**

In `backend/app/agents/scout.py`, update the fallback accommodation (around line 134-138):

Replace:
```python
city.accommodation = Accommodation(
    name=f"Central hotel in {city.name}",
    why="Fallback — LLM did not suggest a specific hotel. Please update manually.",
    estimated_nightly_usd=100,
)
```

With:
```python
from app.config.planning import get_budget_fallback_nightly
city.accommodation = Accommodation(
    name=f"Central hotel in {city.name}",
    why="Fallback — LLM did not suggest a specific hotel. Please update manually.",
    estimated_nightly_usd=get_budget_fallback_nightly(self._budget_tier),
)
```

This requires storing `budget_tier` on the scout. Update `generate_plan()` to accept and store it:

In the `generate_plan` method signature (around line 33), the method receives `request: TripRequest`. Store the budget tier:

```python
self._budget_tier = request.budget.value if request.budget else "moderate"
```

Add this line at the start of `generate_plan()`, before the prompt loading.

**Step 4: Run all tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS (prompt change is additive, schema unchanged)

**Step 5: Commit**

```bash
git add backend/app/prompts/journey/scout_user.md backend/app/agents/scout.py
git commit -m "feat(scout): pass budget tier to prompt and use budget-aware fallback"
```

---

### Task 3: Enricher — Validate and Adjust Accommodation Price

The enricher receives `budget_tier` but ignores it. Make it validate the LLM's price estimate against Google's `price_level` and adjust if mismatched.

**Files:**
- Modify: `backend/app/agents/enricher.py:256-275`
- Test: `backend/tests/test_budget.py`

**Step 1: Write failing tests**

Add to `backend/tests/test_budget.py`:

```python
class TestAccommodationPriceAdjustment:
    """Tests for enricher price adjustment logic."""

    def test_price_adjusted_when_price_level_mismatches(self):
        """LLM says $200 but Google says price_level=1 -> should clamp."""
        from app.config.planning import adjust_price_for_budget
        result = adjust_price_for_budget(200, price_level=1, budget="moderate")
        assert result <= 80

    def test_price_raised_for_luxury_low_estimate(self):
        """LLM says $80 for a luxury hotel (price_level=4) -> should raise."""
        from app.config.planning import adjust_price_for_budget
        result = adjust_price_for_budget(80, price_level=4, budget="luxury")
        assert result >= 250

    def test_price_level_mismatch_detected(self):
        """Budget=luxury but hotel is price_level=1 -> mismatch."""
        from app.config.planning import price_level_matches_budget
        assert price_level_matches_budget(1, "luxury") is False
        assert price_level_matches_budget(4, "luxury") is True
```

These tests mostly verify the functions from Task 1 in the context of enrichment — they should already pass.

**Step 2: Implement price adjustment in enricher**

In `backend/app/agents/enricher.py`, update `_enrich_accommodation()` (around line 256-275). After building the new Accommodation object, adjust the price:

Replace the section that creates the Accommodation (lines 259-275):

```python
            if result:
                # Validate accommodation quality before accepting
                if (result.rating is not None and result.rating < 3.5) or \
                   (result.user_ratings_total is not None and result.user_ratings_total < 20):
                    logger.warning(
                        "[Enricher] Low-quality lodging result for %s: %s (rating=%s, reviews=%s) — keeping LLM suggestion",
                        city.name, result.name, result.rating, result.user_ratings_total,
                    )
                    if city.accommodation:
                        city.accommodation.place_id = result.place_id
                        city.accommodation.location = result.location
                    return

                # Preserve LLM's cost estimate, then adjust using Google price_level
                llm_nightly = city.accommodation.estimated_nightly_usd if city.accommodation else None
                llm_why = city.accommodation.why if city.accommodation else ""

                # Adjust price using Google's price_level as ground truth
                from app.config.planning import adjust_price_for_budget
                adjusted_nightly = llm_nightly
                if llm_nightly is not None:
                    adjusted_nightly = adjust_price_for_budget(
                        llm_nightly,
                        price_level=result.price_level,
                        budget=budget_tier,
                    )
                    if adjusted_nightly != llm_nightly:
                        logger.info(
                            "[Enricher] Adjusted %s nightly rate: $%.0f -> $%.0f "
                            "(price_level=%s, budget=%s)",
                            city.name, llm_nightly, adjusted_nightly,
                            result.price_level, budget_tier,
                        )

                city.accommodation = Accommodation(
                    name=result.name,
                    why=llm_why,
                    address=result.address,
                    location=result.location,
                    place_id=result.place_id,
                    rating=result.rating,
                    price_level=result.price_level,
                    estimated_nightly_usd=adjusted_nightly,
                    website=result.website,
                    editorial_summary=result.editorial_summary,
                    photo_url=(
                        self.places.get_photo_url(result.photo_reference)
                        if result.photo_reference
                        else None
                    ),
                )
                logger.info(
                    "[Enricher] Enriched accommodation for %s: %s ($%.0f/night, pl=%s)",
                    city.name, result.name,
                    adjusted_nightly or 0, result.price_level,
                )
```

**Step 3: Run all tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add backend/app/agents/enricher.py backend/tests/test_budget.py
git commit -m "feat(enricher): adjust accommodation price using Google price_level"
```

---

### Task 4: Enricher — Budget-Filtered Alternative Lodging Search

When the LLM's hotel has a `price_level` that doesn't match the user's budget tier, search for a better alternative.

**Files:**
- Modify: `backend/app/agents/enricher.py:202-294`
- Modify: `backend/app/services/google/places.py:204-253` (add price_levels filter)
- Test: `backend/tests/test_budget.py`

**Step 1: Add price_levels parameter to search_lodging**

In `backend/app/services/google/places.py`, update `search_lodging()` to accept an optional `price_levels` filter:

```python
async def search_lodging(
    self,
    query: str,
    location: Location,
    radius_meters: int = 10_000,
    price_levels: list[str] | None = None,
) -> PlaceCandidate | None:
```

Add price level filtering to the request body. Google Places API v1 uses `priceLevels` field in the request:

After `"maxResultCount": 5,` add:

```python
if price_levels:
    body["priceLevels"] = price_levels
```

Google's API expects strings like `"PRICE_LEVEL_MODERATE"`, `"PRICE_LEVEL_EXPENSIVE"`, etc.

Add a helper to convert int price_levels to Google API strings:

```python
_PRICE_LEVEL_STRINGS = {
    0: "PRICE_LEVEL_FREE",
    1: "PRICE_LEVEL_INEXPENSIVE",
    2: "PRICE_LEVEL_MODERATE",
    3: "PRICE_LEVEL_EXPENSIVE",
    4: "PRICE_LEVEL_VERY_EXPENSIVE",
}
```

**Step 2: Add budget-filtered search in enricher**

In `backend/app/agents/enricher.py`, after the existing enrichment logic (after checking if `price_level_matches_budget`), add a fallback search for budget-appropriate hotels:

After the main enrichment block that creates `city.accommodation`, add a price-level mismatch check:

```python
                # Check if hotel matches budget tier
                from app.config.planning import price_level_matches_budget
                if result.price_level is not None and not price_level_matches_budget(result.price_level, budget_tier):
                    logger.info(
                        "[Enricher] Hotel %s price_level=%s doesn't match budget=%s, searching alternatives",
                        result.name, result.price_level, budget_tier,
                    )
                    # Search for budget-appropriate alternative
                    from app.config.planning import get_target_price_levels
                    target_levels = get_target_price_levels(budget_tier)
                    _PRICE_LEVEL_STRINGS = {
                        0: "PRICE_LEVEL_FREE", 1: "PRICE_LEVEL_INEXPENSIVE",
                        2: "PRICE_LEVEL_MODERATE", 3: "PRICE_LEVEL_EXPENSIVE",
                        4: "PRICE_LEVEL_VERY_EXPENSIVE",
                    }
                    google_levels = [_PRICE_LEVEL_STRINGS[pl] for pl in target_levels if pl in _PRICE_LEVEL_STRINGS]
                    alt = await self.places.search_lodging(
                        query=f"hotel {city.name}",
                        location=city_location,
                        radius_meters=15_000,
                        price_levels=google_levels,
                    )
                    if alt and alt.rating and alt.rating >= 3.5:
                        logger.info(
                            "[Enricher] Found budget-matched alternative for %s: %s (pl=%s, rating=%s)",
                            city.name, alt.name, alt.price_level, alt.rating,
                        )
                        # Use the alternative hotel
                        adjusted_nightly = adjust_price_for_budget(
                            llm_nightly or get_budget_fallback_nightly(budget_tier),
                            price_level=alt.price_level,
                            budget=budget_tier,
                        )
                        city.accommodation = Accommodation(
                            name=alt.name,
                            why=f"Selected to match {budget_tier} budget — {alt.editorial_summary or ''}".strip(),
                            address=alt.address,
                            location=alt.location,
                            place_id=alt.place_id,
                            rating=alt.rating,
                            price_level=alt.price_level,
                            estimated_nightly_usd=adjusted_nightly,
                            website=alt.website,
                            editorial_summary=alt.editorial_summary,
                            photo_url=(
                                self.places.get_photo_url(alt.photo_reference)
                                if alt.photo_reference
                                else None
                            ),
                        )
                        return  # Use alternative instead
```

Also add the import at the top of the method: `from app.config.planning import get_budget_fallback_nightly`

**Step 3: Write test for budget-filtered search**

Add to `backend/tests/test_budget.py`:

```python
class TestSearchLodgingPriceLevels:
    """Test that price_levels parameter is accepted by search_lodging."""

    def test_price_level_strings_mapping(self):
        """Verify the price level string mapping covers all levels."""
        from app.services.google.places import _PRICE_LEVEL_STRINGS
        assert _PRICE_LEVEL_STRINGS[1] == "PRICE_LEVEL_INEXPENSIVE"
        assert _PRICE_LEVEL_STRINGS[4] == "PRICE_LEVEL_VERY_EXPENSIVE"
        assert len(_PRICE_LEVEL_STRINGS) == 5
```

**Step 4: Run all tests**

Run: `cd backend && source venv/bin/activate && pytest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/agents/enricher.py backend/app/services/google/places.py backend/tests/test_budget.py
git commit -m "feat(enricher): search for budget-matched alternative hotels when price_level mismatches"
```

---

### Task 5: Update CLAUDE.md and Docs

Document the accommodation pricing changes.

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Design Principles**

In CLAUDE.md, find the section about accommodation in the Agents description (scout.py line mentioning "accommodation") and update. Also add to Design Principles after the duration estimation priority sentence:

Add after the opening hours enforcement paragraph:

```
Accommodation pricing uses LLM estimates validated by Google: Scout receives the `budget` tier in its prompt for upfront calibration. Enricher adjusts `estimated_nightly_usd` using Google's `price_level` (0-4) — if price_level is available, the estimate is clamped to the USD range for that level. If the hotel's price_level doesn't match the budget tier, enricher searches for a budget-appropriate alternative. Fallback placeholder uses the midpoint of the budget tier's USD range instead of hardcoded $100.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document budget-aware accommodation pricing"
```

---

## Summary of Changes

| Task | Priority | Files Changed | Tests Added |
|------|----------|---------------|-------------|
| 1. Budget-to-price config | Foundation | `planning.py` | 9 tests |
| 2. Pass budget to Scout | P0 | `scout.py`, `scout_user.md` | 0 (prompt) |
| 3. Enricher price adjustment | P0 | `enricher.py` | 3 tests |
| 4. Budget-filtered alt search | P1 | `enricher.py`, `places.py` | 1 test |
| 5. Update CLAUDE.md | P2 | `CLAUDE.md` | 0 |

**Total: 5 tasks, 13 new tests, 6 files modified**
