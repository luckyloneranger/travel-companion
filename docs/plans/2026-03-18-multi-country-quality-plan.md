# Multi-Country Journey Quality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve multi-country trip quality by adding a two-phase Scout pipeline — a lightweight Country Allocator decides countries/days/entry cities, then per-country landscape discovery runs in parallel, then the existing Scout plans within those constraints.

**Architecture:** Multi-country detection (from must-see results) gates a new pre-Scout phase. Phase 1 is a small structured LLM call (~1500 tokens) that outputs country allocations. Per-country discovery runs the existing `discover_destination_landscape()` once per country in parallel. Phase 2 is the existing Scout with richer per-country context and a hard allocation constraint. Single-country trips are completely unaffected.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, asyncio, Google Places API, Azure OpenAI / Anthropic / Gemini LLM providers

---

## Task 1: Add `country` field to `MustSeeAttraction` + update must-see prompts

**Files:**
- Modify: `backend/app/models/journey.py:33-37`
- Modify: `backend/app/prompts/journey/must_see_system.md:1-11`
- Modify: `backend/app/prompts/journey/must_see_user.md:1-21`
- Test: `backend/tests/test_agents.py` (TestMustSeeModels class, ~line 779)

**Step 1: Add `country` field to `MustSeeAttraction` model**

In `backend/app/models/journey.py`, add `country` field after `city_or_region`:

```python
class MustSeeAttraction(BaseModel):
    """A globally iconic, must-visit attraction at a destination."""
    name: str
    city_or_region: str
    country: str = ""
    why_iconic: str
```

**Step 2: Update must-see system prompt**

In `backend/app/prompts/journey/must_see_system.md`, add country instruction after line 8:

```markdown
- Include the `country` name for each attraction (e.g., "Thailand", "Cambodia")
```

**Step 3: Update must-see user prompt**

In `backend/app/prompts/journey/must_see_user.md`, add `country` to the JSON example schema:

```json
{
  "attractions": [
    {
      "name": "Specific Place Name",
      "city_or_region": "City or region where it is located",
      "country": "Country name",
      "why_iconic": "One sentence explaining why this is a must-see"
    }
  ]
}
```

**Step 4: Add test for country field**

In `backend/tests/test_agents.py`, add a test to `TestMustSeeModels`:

```python
def test_must_see_attraction_country_field(self):
    """MustSeeAttraction should accept optional country field."""
    from app.models.journey import MustSeeAttraction
    a = MustSeeAttraction(
        name="Angkor Wat",
        city_or_region="Siem Reap",
        country="Cambodia",
        why_iconic="Temple complex",
    )
    assert a.country == "Cambodia"

def test_must_see_attraction_country_defaults_empty(self):
    """MustSeeAttraction country should default to empty string."""
    from app.models.journey import MustSeeAttraction
    a = MustSeeAttraction(
        name="Grand Palace",
        city_or_region="Bangkok",
        why_iconic="Royal palace",
    )
    assert a.country == ""
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestMustSeeModels -v`
Expected: All tests pass including new country field tests.

**Step 6: Commit**

```bash
git add backend/app/models/journey.py backend/app/prompts/journey/must_see_system.md backend/app/prompts/journey/must_see_user.md backend/tests/test_agents.py
git commit -m "feat(models): add country field to MustSeeAttraction for multi-country detection"
```

---

## Task 2: Add `CountryPlan` + `CountryAllocation` models + allocator config

**Files:**
- Modify: `backend/app/models/journey.py:44` (after MustSeeAttractions)
- Modify: `backend/app/config/planning.py:64` (after must-see config)
- Test: `backend/tests/test_agents.py`

**Step 1: Add models to `journey.py`**

After the `MustSeeAttractions` class (line 44), add:

```python
class CountryPlan(BaseModel):
    """One country's allocation in a multi-country trip."""
    country: str
    days: int
    entry_city: str
    why: str = ""


class CountryAllocation(BaseModel):
    """LLM-determined country allocation for multi-country trips."""
    countries: list[CountryPlan] = Field(..., min_length=2, max_length=5)
    routing_order: list[str]
    reasoning: str = ""
```

**Step 2: Add allocator LLM config + multi-country region set to `planning.py`**

After the must-see config block (line 64), add:

```python
# Country allocator (lightweight, factual allocation)
LLM_ALLOCATOR_MAX_TOKENS: int = 1500
LLM_ALLOCATOR_TEMPERATURE: float = 0.3

# Multi-country region names — triggers two-phase pipeline
MULTI_COUNTRY_REGIONS: set[str] = {
    "Southeast Asia", "Europe", "Central America", "East Africa",
    "West Africa", "Middle East", "Scandinavia", "Balkans",
    "Caribbean", "South America", "Central Asia", "South Asia",
    "East Asia", "Pacific Islands",
}
```

**Step 3: Add tests for new models**

In `backend/tests/test_agents.py`, add a new test class:

```python
class TestCountryAllocationModels:
    """Country allocation models for multi-country pipeline."""

    def test_country_plan_basic(self):
        from app.models.journey import CountryPlan
        cp = CountryPlan(country="Thailand", days=5, entry_city="Bangkok", why="Gateway")
        assert cp.country == "Thailand"
        assert cp.days == 5

    def test_country_allocation_basic(self):
        from app.models.journey import CountryAllocation, CountryPlan
        ca = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok"),
                CountryPlan(country="Cambodia", days=3, entry_city="Siem Reap"),
            ],
            routing_order=["Thailand", "Cambodia"],
            reasoning="Efficient south-to-east routing",
        )
        assert len(ca.countries) == 2
        assert ca.routing_order == ["Thailand", "Cambodia"]

    def test_country_allocation_min_countries(self):
        """Must have at least 2 countries."""
        from app.models.journey import CountryAllocation, CountryPlan
        with pytest.raises(Exception):
            CountryAllocation(
                countries=[CountryPlan(country="Thailand", days=5, entry_city="Bangkok")],
                routing_order=["Thailand"],
            )
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestCountryAllocationModels -v`
Expected: All 3 tests pass.

**Step 5: Commit**

```bash
git add backend/app/models/journey.py backend/app/config/planning.py backend/tests/test_agents.py
git commit -m "feat(models): add CountryPlan/CountryAllocation models and allocator config"
```

---

## Task 3: Create country allocator prompts

**Files:**
- Create: `backend/app/prompts/journey/country_allocator_system.md`
- Create: `backend/app/prompts/journey/country_allocator_user.md`

**Step 1: Create system prompt**

Create `backend/app/prompts/journey/country_allocator_system.md`:

```markdown
You are a travel logistics expert. Your task is to allocate countries and days for a multi-country trip.

RULES:
- Minimum 3 days per country (depth over breadth)
- Maximum 4 countries for trips <=14 days, maximum 5 for 15-21 days
- Must include countries that contain must-see attractions
- Entry city should be the main international gateway or closest to previous country's exit
- Days should be proportional to attraction density and traveler interests
- Respect the traveler's avoid list (skip countries/cities mentioned)
- Consider border crossing logistics — prefer land borders when countries are adjacent
- Routing order should minimize total travel distance (no backtracking)
- Return ONLY the JSON object. No markdown fences, no text before or after.
```

**Step 2: Create user prompt**

Create `backend/app/prompts/journey/country_allocator_user.md`:

```markdown
Allocate countries and days for this multi-country trip:

**Region:** {destination}
**Total days:** {total_days}
**Origin:** {origin}
**Interests:** {interests}
**Pace:** {pace}
**Budget:** {budget}
**Group:** {travelers_description}

**Must-see attractions identified:**
{must_see_context}

**Places to include (if any):** {must_include}
**Places to avoid (if any):** {avoid}

Return JSON:
```json
{{{{
  "countries": [
    {{{{
      "country": "Country Name",
      "days": 5,
      "entry_city": "Main Gateway City",
      "why": "Brief reason for this allocation"
    }}}}
  ],
  "routing_order": ["Country1", "Country2", "Country3"],
  "reasoning": "Brief explanation of routing logic"
}}}}
```

**RULES:**
- Total days across all countries MUST equal {total_days}
- Minimum 3 days per country
- Maximum {max_countries} countries
- Must include countries containing the must-see attractions above
- routing_order must follow efficient geographic flow (no backtracking)
- Return ONLY valid JSON — no markdown fences, no text
```

**Step 3: Verify prompts load**

Run: `cd backend && python -c "from app.prompts import journey_prompts; print(journey_prompts.load('country_allocator_system')[:50])"`
Expected: First 50 chars of the system prompt.

**Step 4: Commit**

```bash
git add backend/app/prompts/journey/country_allocator_system.md backend/app/prompts/journey/country_allocator_user.md
git commit -m "feat(prompts): add country allocator system and user prompts"
```

---

## Task 4: Implement multi-country detection in orchestrator

**Files:**
- Modify: `backend/app/orchestrators/journey.py:108-124` (after must-see result unpacking)
- Test: `backend/tests/test_agents.py`

**Step 1: Add `_detect_multi_country` method to `JourneyOrchestrator`**

After `_build_geographic_context` method (~line 453), add:

```python
@staticmethod
def _detect_multi_country(
    must_see_raw: MustSeeAttractions | None,
    destination: str,
) -> bool:
    """Detect if this is a multi-country trip.

    Uses country field from must-see attractions when available,
    falls back to known multi-country region name set.
    """
    from app.config.planning import MULTI_COUNTRY_REGIONS

    # Primary: count distinct countries from must-see attractions
    if must_see_raw and must_see_raw.attractions:
        countries = {
            a.country.strip().lower()
            for a in must_see_raw.attractions
            if a.country and a.country.strip()
        }
        if len(countries) >= 2:
            logger.info(
                "[Orchestrator] Multi-country detected from must-see: %s",
                countries,
            )
            return True

    # Fallback: check destination against known multi-country regions
    dest_lower = destination.strip().lower()
    for region in MULTI_COUNTRY_REGIONS:
        if region.lower() in dest_lower or dest_lower in region.lower():
            logger.info(
                "[Orchestrator] Multi-country detected from region name: %s",
                destination,
            )
            return True

    return False
```

**Step 2: Add tests for multi-country detection**

```python
class TestMultiCountryDetection:
    """Multi-country detection from must-see attractions + region names."""

    def _make_orchestrator(self):
        from app.orchestrators.journey import JourneyOrchestrator
        llm = MagicMock()
        places = MagicMock()
        routes = MagicMock()
        directions = MagicMock()
        return JourneyOrchestrator(llm, places, routes, directions)

    def test_detect_from_must_see_countries(self):
        """Detects multi-country from distinct country fields."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        orch = self._make_orchestrator()
        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Grand Palace", city_or_region="Bangkok", country="Thailand", why_iconic="Palace"),
            MustSeeAttraction(name="Angkor Wat", city_or_region="Siem Reap", country="Cambodia", why_iconic="Temple"),
        ])
        assert orch._detect_multi_country(must_see, "Southeast Asia") is True

    def test_single_country_not_detected(self):
        """Single-country must-see should not trigger multi-country."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        orch = self._make_orchestrator()
        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Fushimi Inari", city_or_region="Kyoto", country="Japan", why_iconic="Gates"),
            MustSeeAttraction(name="Mt Fuji", city_or_region="Hakone", country="Japan", why_iconic="Mountain"),
        ])
        assert orch._detect_multi_country(must_see, "Japan") is False

    def test_fallback_to_region_name(self):
        """Falls back to region name set when must-see has no country field."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        orch = self._make_orchestrator()
        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Place", city_or_region="City", why_iconic="Reason"),
        ])
        assert orch._detect_multi_country(must_see, "Southeast Asia") is True
        assert orch._detect_multi_country(must_see, "Japan") is False

    def test_no_must_see_uses_region_fallback(self):
        """When must_see_raw is None, uses region name fallback."""
        orch = self._make_orchestrator()
        assert orch._detect_multi_country(None, "Europe") is True
        assert orch._detect_multi_country(None, "Italy") is False
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestMultiCountryDetection -v`
Expected: All 4 tests pass.

**Step 4: Commit**

```bash
git add backend/app/orchestrators/journey.py backend/tests/test_agents.py
git commit -m "feat(orchestrator): add multi-country detection from must-see attractions"
```

---

## Task 5: Implement Phase 1 Country Allocator call in orchestrator

**Files:**
- Modify: `backend/app/orchestrators/journey.py` (new method + wiring into plan_stream)
- Test: `backend/tests/test_agents.py`

**Step 1: Add `_allocate_countries` method**

After `_detect_multi_country`, add:

```python
async def _allocate_countries(
    self,
    request: TripRequest,
    must_see_context: str,
) -> "CountryAllocation | None":
    """Phase 1: Lightweight LLM call to allocate countries for multi-country trips.

    Returns None on failure (graceful degradation to single-shot Scout).
    """
    from app.config.planning import LLM_ALLOCATOR_MAX_TOKENS, LLM_ALLOCATOR_TEMPERATURE, should_use_search_grounding
    from app.models.journey import CountryAllocation
    from app.prompts import journey_prompts

    max_countries = 5 if request.total_days >= 15 else 4

    try:
        system_prompt = journey_prompts.load("country_allocator_system")
        user_prompt = journey_prompts.load("country_allocator_user").format(
            destination=request.destination,
            total_days=request.total_days,
            origin=request.origin or "not specified",
            interests=", ".join(request.interests) if request.interests else "general",
            pace=request.pace.value,
            budget=request.budget.value if request.budget else "moderate",
            travelers_description=request.travelers.summary,
            must_see_context=must_see_context,
            must_include=", ".join(request.must_include) if request.must_include else "none",
            avoid=", ".join(request.avoid) if request.avoid else "none",
            max_countries=max_countries,
        )

        if should_use_search_grounding("selective"):
            allocation, _citations = await self.llm.generate_structured_with_search(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=CountryAllocation,
                max_tokens=LLM_ALLOCATOR_MAX_TOKENS,
                temperature=LLM_ALLOCATOR_TEMPERATURE,
            )
        else:
            allocation = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=CountryAllocation,
                max_tokens=LLM_ALLOCATOR_MAX_TOKENS,
                temperature=LLM_ALLOCATOR_TEMPERATURE,
            )

        # Validate total days
        total_allocated = sum(c.days for c in allocation.countries)
        if total_allocated != request.total_days:
            logger.warning(
                "[Orchestrator] Allocator days mismatch: allocated=%d, requested=%d",
                total_allocated, request.total_days,
            )

        logger.info(
            "[Orchestrator] Country allocation: %s",
            " → ".join(f"{c.country}({c.days}d)" for c in allocation.countries),
        )
        return allocation

    except Exception as exc:
        logger.warning("[Orchestrator] Country allocation failed: %s — falling back to single-shot Scout", exc)
        return None
```

**Step 2: Add test for country allocation call**

```python
class TestCountryAllocation:
    """Country Allocator Phase 1 LLM call."""

    def _make_orchestrator(self):
        from app.orchestrators.journey import JourneyOrchestrator
        llm = MagicMock()
        places = MagicMock()
        routes = MagicMock()
        directions = MagicMock()
        return JourneyOrchestrator(llm, places, routes, directions)

    @pytest.mark.asyncio
    async def test_allocate_countries_basic(self):
        """Should call LLM and return CountryAllocation."""
        from app.models.journey import CountryAllocation, CountryPlan
        orch = self._make_orchestrator()

        mock_allocation = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok", why="Gateway"),
                CountryPlan(country="Cambodia", days=4, entry_city="Siem Reap", why="Temples"),
                CountryPlan(country="Vietnam", days=4, entry_city="Hanoi", why="Culture"),
            ],
            routing_order=["Thailand", "Cambodia", "Vietnam"],
            reasoning="South to north efficient routing",
        )
        orch.llm.generate_structured = AsyncMock(return_value=mock_allocation)

        request = _make_request(destination="Southeast Asia", total_days=13)
        result = await orch._allocate_countries(request, "Must-see context here")

        assert result is not None
        assert len(result.countries) == 3
        assert result.routing_order == ["Thailand", "Cambodia", "Vietnam"]
        orch.llm.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_allocate_countries_failure_returns_none(self):
        """LLM failure should return None (graceful fallback)."""
        orch = self._make_orchestrator()
        orch.llm.generate_structured = AsyncMock(side_effect=Exception("LLM error"))

        request = _make_request(destination="Southeast Asia", total_days=13)
        result = await orch._allocate_countries(request, "Must-see context here")

        assert result is None
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestCountryAllocation -v`
Expected: Both tests pass.

**Step 4: Commit**

```bash
git add backend/app/orchestrators/journey.py backend/tests/test_agents.py
git commit -m "feat(orchestrator): implement Phase 1 Country Allocator LLM call"
```

---

## Task 6: Implement per-country landscape discovery + wire into pipeline

**Files:**
- Modify: `backend/app/orchestrators/journey.py:87-147` (plan_stream method)
- Test: `backend/tests/test_agents.py`

**Step 1: Add `_discover_per_country` method**

After `_allocate_countries`, add:

```python
async def _discover_per_country(
    self,
    allocation: "CountryAllocation",
) -> str:
    """Run landscape discovery per country in parallel.

    Returns formatted landmarks grouped by country. Falls back to
    whatever succeeded if some countries fail.
    """
    from app.models.journey import CountryAllocation

    async def discover_one(country_plan):
        try:
            result = await self.places.discover_destination_landscape(country_plan.country)
            if result:
                return f"## {country_plan.country} — Landscape Discovery\n{result}"
        except Exception as exc:
            logger.warning(
                "[Orchestrator] Per-country discovery failed for %s: %s",
                country_plan.country, exc,
            )
        return ""

    results = await asyncio.gather(
        *(discover_one(cp) for cp in allocation.countries)
    )

    combined = "\n\n".join(r for r in results if r)
    if combined:
        logger.info(
            "[Orchestrator] Per-country discovery complete for %d countries",
            sum(1 for r in results if r),
        )
    return combined
```

**Step 2: Wire multi-country pipeline into `plan_stream`**

In `plan_stream`, between the existing geographic context block (line ~126-134) and the Scout call (line ~136), insert the multi-country detection and Phase 1/2 logic. Replace the section from `self._landmarks_context = landscape_context` (line 123) through the Scout call to:

```python
            self._landmarks_context = landscape_context
            self._must_see_context = must_see_context

            # ── Step 0.5: Multi-country detection + Phase 1 ──
            country_allocation = None
            is_multi_country = self._detect_multi_country(must_see_raw, request.destination)

            if is_multi_country:
                logger.info("[Orchestrator] Multi-country trip detected — running Phase 1 allocator")
                country_allocation = await self._allocate_countries(request, must_see_context)

                if country_allocation:
                    # Per-country landscape discovery (replaces region-wide discovery)
                    per_country_landmarks = await self._discover_per_country(country_allocation)
                    if per_country_landmarks:
                        self._landmarks_context = per_country_landmarks

            # ── Step 0.5b: Build geographic context ──
            geographic_context = ""
            if country_allocation:
                # Use Phase 1 entry cities for geographic context
                geographic_context = self._build_geographic_context_from_allocation(country_allocation)
            elif must_see_raw:
                try:
                    geographic_context = await self._build_geographic_context(
                        must_see_raw, request.origin
                    )
                except Exception as exc:
                    logger.warning("[Orchestrator] Geographic context failed: %s", exc)
```

**Step 3: Add `_build_geographic_context_from_allocation` method**

After `_discover_per_country`, add:

```python
@staticmethod
def _build_geographic_context_from_allocation(
    allocation: "CountryAllocation",
) -> str:
    """Build geographic context from Phase 1 allocation entry cities.

    Uses the routing_order and entry_cities from the allocation —
    no geocoding needed since the allocator already determined the order.
    """
    if len(allocation.countries) < 2:
        return ""

    lines = [
        "## GEOGRAPHIC CONTEXT (from country allocation)",
        "Route order determined by pre-planning phase:",
        "",
    ]

    # Build flow from routing order
    country_map = {cp.country: cp for cp in allocation.countries}
    flow_parts = []
    for country_name in allocation.routing_order:
        cp = country_map.get(country_name)
        if cp:
            flow_parts.append(f"{cp.entry_city}, {cp.country} ({cp.days}d)")

    lines.append(" → ".join(flow_parts))
    lines.append("")
    lines.append(
        "Follow this country order and entry cities. "
        "You may add secondary cities WITHIN a country but must NOT "
        "reorder countries or reallocate days between them."
    )

    return "\n".join(lines)
```

**Step 4: Add test for per-country discovery**

```python
class TestPerCountryDiscovery:
    """Per-country landscape discovery for multi-country trips."""

    def _make_orchestrator(self):
        from app.orchestrators.journey import JourneyOrchestrator
        llm = MagicMock()
        places = MagicMock()
        routes = MagicMock()
        directions = MagicMock()
        return JourneyOrchestrator(llm, places, routes, directions)

    @pytest.mark.asyncio
    async def test_per_country_discovery_basic(self):
        """Should discover landmarks per country in parallel."""
        from app.models.journey import CountryAllocation, CountryPlan
        orch = self._make_orchestrator()

        allocation = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok"),
                CountryPlan(country="Cambodia", days=4, entry_city="Siem Reap"),
            ],
            routing_order=["Thailand", "Cambodia"],
        )

        async def mock_discover(destination):
            return f"### Landmarks for {destination}\n- Place 1\n- Place 2"

        orch.places.discover_destination_landscape = AsyncMock(side_effect=mock_discover)

        result = await orch._discover_per_country(allocation)
        assert "Thailand" in result
        assert "Cambodia" in result
        assert "Place 1" in result
        # Called once per country
        assert orch.places.discover_destination_landscape.call_count == 2

    @pytest.mark.asyncio
    async def test_per_country_discovery_partial_failure(self):
        """Should return results from successful countries when some fail."""
        from app.models.journey import CountryAllocation, CountryPlan
        orch = self._make_orchestrator()

        allocation = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok"),
                CountryPlan(country="Cambodia", days=4, entry_city="Siem Reap"),
            ],
            routing_order=["Thailand", "Cambodia"],
        )

        call_count = 0
        async def mock_discover(destination):
            nonlocal call_count
            call_count += 1
            if destination == "Cambodia":
                raise ValueError("API error")
            return f"### Landmarks for {destination}\n- Place 1"

        orch.places.discover_destination_landscape = AsyncMock(side_effect=mock_discover)

        result = await orch._discover_per_country(allocation)
        assert "Thailand" in result
        assert "Cambodia" not in result

    def test_geographic_context_from_allocation(self):
        """Should build context from allocation entry cities."""
        from app.orchestrators.journey import JourneyOrchestrator
        from app.models.journey import CountryAllocation, CountryPlan

        allocation = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok"),
                CountryPlan(country="Cambodia", days=3, entry_city="Siem Reap"),
                CountryPlan(country="Vietnam", days=5, entry_city="Hanoi"),
            ],
            routing_order=["Thailand", "Cambodia", "Vietnam"],
        )

        context = JourneyOrchestrator._build_geographic_context_from_allocation(allocation)
        assert "Bangkok, Thailand (5d)" in context
        assert "Siem Reap, Cambodia (3d)" in context
        assert "Hanoi, Vietnam (5d)" in context
        assert "reorder countries" in context.lower() or "must NOT" in context
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestPerCountryDiscovery -v`
Expected: All 3 tests pass.

**Step 6: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All 245+ tests pass (no regression).

**Step 7: Commit**

```bash
git add backend/app/orchestrators/journey.py backend/tests/test_agents.py
git commit -m "feat(orchestrator): per-country discovery + multi-country pipeline wiring"
```

---

## Task 7: Add `country_allocation` parameter to Scout + update prompts

**Files:**
- Modify: `backend/app/agents/scout.py:33,76-78`
- Modify: `backend/app/prompts/journey/scout_system.md:88` (add Rule 11)
- Modify: `backend/app/prompts/journey/scout_user.md:16` (add `{country_allocation}` placeholder)
- Test: `backend/tests/test_agents.py`

**Step 1: Add `country_allocation` parameter to Scout**

In `backend/app/agents/scout.py`, modify line 33:

```python
async def generate_plan(self, request: TripRequest, landmarks_context: str = "", geographic_context: str = "", country_allocation: str = "") -> JourneyPlan:
```

Add to the format call (line 76-78), adding `country_allocation`:

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
            geographic_context=geographic_context,
            country_allocation=country_allocation,
        )
```

**Step 2: Add `{country_allocation}` placeholder to Scout user prompt**

In `backend/app/prompts/journey/scout_user.md`, add after `{geographic_context}` (line 16):

```
{country_allocation}
```

**Step 3: Add Rule 11 to Scout system prompt**

In `backend/app/prompts/journey/scout_system.md`, before the `## OUTPUT` section (line 91), add:

```markdown
### Rule 11: Country Allocation Constraint
- If a "COUNTRY ALLOCATION" section is provided, treat it as a HARD constraint
- Do NOT add, remove, or reorder countries
- Do NOT reallocate days between countries
- You MAY add secondary cities within a country (e.g., Chiang Mai within Thailand's 5 days)
- Entry city must be the first base in that country
- If no COUNTRY ALLOCATION is provided, you decide countries freely (single-country trips)
```

**Step 4: Wire `country_allocation` in orchestrator**

In `backend/app/orchestrators/journey.py`, update the Scout call (currently line ~143) to pass `country_allocation`:

```python
            # ── Step 1: Scout ────────────────────────────────────────
            yield ProgressEvent(
                phase="scouting",
                message="Creating your journey...",
                progress=10,
            )
            logger.info("[Orchestrator] Scouting plan for %s", request.destination)

            # Format country allocation as Scout constraint
            country_allocation_text = ""
            if country_allocation:
                country_allocation_text = self._format_country_allocation(country_allocation)

            plan: JourneyPlan = await self.scout.generate_plan(
                request,
                landmarks_context=self._landmarks_context,
                geographic_context=geographic_context,
                country_allocation=country_allocation_text,
            )
```

**Step 5: Add `_format_country_allocation` method**

After `_build_geographic_context_from_allocation`, add:

```python
@staticmethod
def _format_country_allocation(allocation: "CountryAllocation") -> str:
    """Format country allocation as a hard constraint for the Scout."""
    lines = [
        "## COUNTRY ALLOCATION (from pre-planning)",
        "You MUST follow this allocation:",
    ]
    for i, cp in enumerate(allocation.countries, 1):
        lines.append(f"{i}. {cp.country} — {cp.days} days, enter via {cp.entry_city}")

    lines.append("")
    lines.append(f"Route order: {' → '.join(allocation.routing_order)}")
    lines.append(f"Total: {sum(cp.days for cp in allocation.countries)} days")
    lines.append("")
    lines.append("Do NOT add, remove, or reorder countries.")
    lines.append("Do NOT reallocate days between countries.")
    lines.append("You MAY add secondary cities within a country.")
    lines.append("Entry city must be the first base in that country.")

    return "\n".join(lines)
```

**Step 6: Add test for Scout receiving country_allocation**

```python
class TestScoutCountryAllocation:
    """Scout agent receiving country allocation constraint."""

    @pytest.mark.asyncio
    async def test_scout_passes_country_allocation_to_prompt(self):
        """Scout should include country_allocation in user prompt."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(return_value=_make_journey_plan())

        agent = ScoutAgent(llm=mock_llm)
        request = _make_request(destination="Southeast Asia", total_days=13)
        allocation_text = "## COUNTRY ALLOCATION\n1. Thailand — 5 days"

        await agent.generate_plan(
            request,
            landmarks_context="",
            geographic_context="",
            country_allocation=allocation_text,
        )

        call_kwargs = mock_llm.generate_structured.call_args
        user_prompt = call_kwargs.kwargs.get("user_prompt", call_kwargs[1].get("user_prompt", ""))
        assert "COUNTRY ALLOCATION" in user_prompt

    @pytest.mark.asyncio
    async def test_scout_works_without_country_allocation(self):
        """Scout should work fine with empty country_allocation (single-country)."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(return_value=_make_journey_plan())

        agent = ScoutAgent(llm=mock_llm)
        request = _make_request(destination="Japan", total_days=10)

        result = await agent.generate_plan(request, country_allocation="")
        assert result is not None
        assert len(result.cities) > 0

    def test_format_country_allocation(self):
        """Country allocation should format as readable constraint text."""
        from app.orchestrators.journey import JourneyOrchestrator
        from app.models.journey import CountryAllocation, CountryPlan

        allocation = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok"),
                CountryPlan(country="Cambodia", days=3, entry_city="Siem Reap"),
            ],
            routing_order=["Thailand", "Cambodia"],
        )
        text = JourneyOrchestrator._format_country_allocation(allocation)
        assert "COUNTRY ALLOCATION" in text
        assert "Thailand — 5 days" in text
        assert "Bangkok" in text
        assert "Do NOT add, remove" in text
```

**Step 7: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestScoutCountryAllocation -v`
Expected: All 3 tests pass.

**Step 8: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass (no regression). Existing Scout tests pass because `country_allocation` defaults to `""`.

**Step 9: Commit**

```bash
git add backend/app/agents/scout.py backend/app/orchestrators/journey.py backend/app/prompts/journey/scout_system.md backend/app/prompts/journey/scout_user.md backend/tests/test_agents.py
git commit -m "feat(scout): accept country allocation constraint for multi-country trips"
```

---

## Task 8: Integration — wire full pipeline + end-to-end test

**Files:**
- Modify: `backend/app/orchestrators/journey.py` (final pipeline assembly)
- Test: `backend/tests/test_agents.py`

This task ensures the full pipeline is wired: detection → allocation → per-country discovery → enhanced Scout.

**Step 1: Verify the `plan_stream` wiring**

The `plan_stream` method should now have this flow after must-see result unpacking:

1. `self._landmarks_context = landscape_context`
2. Multi-country detection: `is_multi_country = self._detect_multi_country(...)`
3. If multi-country: `country_allocation = await self._allocate_countries(...)`
4. If allocation succeeded: `per_country_landmarks = await self._discover_per_country(allocation)`
5. Geographic context: from allocation (if available) or from must-see (existing)
6. Scout call with `country_allocation=country_allocation_text`

Review the assembled code to ensure all pieces connect. Make any adjustments needed.

**Step 2: Add integration test for multi-country pipeline**

```python
class TestMultiCountryPipeline:
    """End-to-end multi-country pipeline integration."""

    @pytest.mark.asyncio
    async def test_multi_country_pipeline_full_flow(self):
        """Multi-country trip should run allocation + per-country discovery + constrained Scout."""
        from app.orchestrators.journey import JourneyOrchestrator
        from app.models.journey import (
            CountryAllocation, CountryPlan,
            MustSeeAttraction, MustSeeAttractions,
        )

        mock_llm = MagicMock()
        mock_places = MagicMock()
        mock_routes = MagicMock()
        mock_directions = MagicMock()

        # Must-see returns multi-country attractions
        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Grand Palace", city_or_region="Bangkok", country="Thailand", why_iconic="Palace"),
            MustSeeAttraction(name="Angkor Wat", city_or_region="Siem Reap", country="Cambodia", why_iconic="Temple"),
            MustSeeAttraction(name="Ha Long Bay", city_or_region="Hanoi", country="Vietnam", why_iconic="Bay"),
        ])

        allocation = CountryAllocation(
            countries=[
                CountryPlan(country="Thailand", days=5, entry_city="Bangkok", why="Gateway"),
                CountryPlan(country="Cambodia", days=3, entry_city="Siem Reap", why="Temples"),
                CountryPlan(country="Vietnam", days=5, entry_city="Hanoi", why="Culture"),
            ],
            routing_order=["Thailand", "Cambodia", "Vietnam"],
            reasoning="South to north",
        )

        se_asia_plan = _make_journey_plan(
            theme="Southeast Asia Discovery",
            summary="13 days across 3 countries",
            cities=[
                CityStop(name="Bangkok", country="Thailand", days=5, why_visit="Gateway",
                         accommodation=Accommodation(name="Hotel BKK", estimated_nightly_usd=80)),
                CityStop(name="Siem Reap", country="Cambodia", days=3, why_visit="Temples",
                         accommodation=Accommodation(name="Hotel SR", estimated_nightly_usd=50)),
                CityStop(name="Hanoi", country="Vietnam", days=5, why_visit="Culture",
                         accommodation=Accommodation(name="Hotel HN", estimated_nightly_usd=60)),
            ],
            travel_legs=[
                TravelLeg(from_city="Bangkok", to_city="Siem Reap", mode=TransportMode.FLIGHT, duration_hours=1),
                TravelLeg(from_city="Siem Reap", to_city="Hanoi", mode=TransportMode.FLIGHT, duration_hours=2),
            ],
            total_days=13,
        )

        review_result = ReviewResult(
            is_acceptable=True, score=85, summary="Good plan",
            issues=[], dimension_scores={"route_logic": 90},
        )

        # Wire mocks — LLM returns must-see, then allocation, then Scout plan, then review
        call_count = 0
        async def mock_generate_structured(**kwargs):
            nonlocal call_count
            call_count += 1
            schema = kwargs.get("schema")
            if schema == MustSeeAttractions:
                return must_see
            if schema == CountryAllocation:
                return allocation
            if schema == JourneyPlan:
                return se_asia_plan
            if schema == ReviewResult:
                return review_result
            return MagicMock()

        mock_llm.generate_structured = AsyncMock(side_effect=mock_generate_structured)

        # Landscape discovery
        async def mock_discover(destination):
            return f"### {destination} landmarks\n- Place 1"
        mock_places.discover_destination_landscape = AsyncMock(side_effect=mock_discover)
        mock_places.geocode = AsyncMock(return_value={"lat": 13.0, "lng": 100.0})

        orch = JourneyOrchestrator(mock_llm, mock_places, mock_routes, mock_directions)
        request = _make_request(destination="Southeast Asia", origin="Bangkok", total_days=13)

        events = []
        async for event in orch.plan_stream(request):
            events.append(event)

        # Should have completed successfully
        phases = [e.phase for e in events]
        assert "complete" in phases
        assert "error" not in phases

        # discover_destination_landscape should be called per country (3x) + initial (1x)
        # The initial region-wide call happens in parallel with must-see
        assert mock_places.discover_destination_landscape.call_count >= 3
```

**Step 3: Add test for single-country bypass**

```python
    @pytest.mark.asyncio
    async def test_single_country_skips_allocation(self):
        """Single-country trips should not call the allocator."""
        from app.orchestrators.journey import JourneyOrchestrator
        from app.models.journey import MustSeeAttraction, MustSeeAttractions

        mock_llm = MagicMock()
        mock_places = MagicMock()
        mock_routes = MagicMock()
        mock_directions = MagicMock()

        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Fushimi Inari", city_or_region="Kyoto", country="Japan", why_iconic="Gates"),
            MustSeeAttraction(name="Mt Fuji", city_or_region="Hakone", country="Japan", why_iconic="Mount"),
        ])

        review_result = ReviewResult(
            is_acceptable=True, score=85, summary="Good plan",
        )

        call_schemas = []
        async def mock_generate_structured(**kwargs):
            schema = kwargs.get("schema")
            call_schemas.append(schema.__name__ if schema else "unknown")
            if schema == MustSeeAttractions:
                return must_see
            if schema == JourneyPlan:
                return _make_journey_plan()
            if schema == ReviewResult:
                return review_result
            return MagicMock()

        mock_llm.generate_structured = AsyncMock(side_effect=mock_generate_structured)
        mock_places.discover_destination_landscape = AsyncMock(return_value="landmarks")
        mock_places.geocode = AsyncMock(return_value={"lat": 35.0, "lng": 139.0})

        orch = JourneyOrchestrator(mock_llm, mock_places, mock_routes, mock_directions)
        request = _make_request(destination="Japan", origin="Tokyo", total_days=10)

        events = []
        async for event in orch.plan_stream(request):
            events.append(event)

        # CountryAllocation should NOT have been called
        assert "CountryAllocation" not in call_schemas
        assert "complete" in [e.phase for e in events]
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_agents.py::TestMultiCountryPipeline -v`
Expected: Both tests pass.

**Step 5: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass (no regression).

**Step 6: Commit**

```bash
git add backend/app/orchestrators/journey.py backend/tests/test_agents.py
git commit -m "feat(orchestrator): wire full multi-country pipeline — detection, allocation, discovery, constrained Scout"
```

---

## Task 9: Update model imports + final cleanup

**Files:**
- Modify: `backend/app/orchestrators/journey.py` (imports at top)
- Modify: `backend/app/models/journey.py` (ensure exports)

**Step 1: Verify imports**

Ensure `journey.py` orchestrator imports include:

```python
from app.models.journey import JourneyPlan, MustSeeAttractions, ReviewResult, CountryAllocation
```

**Step 2: Run full test suite one final time**

Run: `cd backend && python -m pytest -v`
Expected: All 250+ tests pass (original 245 + ~15 new tests from this feature).

**Step 3: Commit any cleanup**

```bash
git add -u
git commit -m "chore: import cleanup for multi-country pipeline"
```

---

## Verification Checklist

1. `cd backend && pytest -v -k "test_must_see_attraction_country"` — country field tests pass
2. `cd backend && pytest -v -k "TestCountryAllocationModels"` — allocation model tests pass
3. `cd backend && pytest -v -k "TestMultiCountryDetection"` — detection tests pass
4. `cd backend && pytest -v -k "TestCountryAllocation"` — allocator call tests pass
5. `cd backend && pytest -v -k "TestPerCountryDiscovery"` — per-country discovery tests pass
6. `cd backend && pytest -v -k "TestScoutCountryAllocation"` — Scout constraint tests pass
7. `cd backend && pytest -v -k "TestMultiCountryPipeline"` — integration tests pass
8. `cd backend && pytest` — ALL tests pass (no regression)
9. Run SE Asia 15-day trip → Scout should produce 3 countries with no backtracking
10. Run Japan 10-day trip → completely unchanged behavior (single-country bypass)
