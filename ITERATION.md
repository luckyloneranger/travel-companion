# Iteration Log

## V0.30 — Data Flow: Return-to-Origin & Streaming Transit Data

**Status:** Complete

### Changes from V0.29

**Code & Data Path Flow**
- `return_to_origin` flag is now wired through to the Scout LLM prompt — when enabled, Scout includes a final travel leg from the last city back to origin. Previously the flag was accepted by the API but silently ignored
- Fixed transit data serialization gap in `orchestrator.py` SSE streaming path: `_format_final_result()` now includes `fare`, `num_transfers`, `departure_time`, `arrival_time`, and `estimated_cost` on travel legs — was missing from the streaming serialization despite being added to `_format_journey_response()` in V0.22

---

## V0.29 — Frontend: Transit Details in TravelLegCard

**Status:** Complete

### Changes from V0.28

**Frontend UI**
- `V6TravelLeg` TypeScript interface now includes `fare`, `num_transfers`, `departure_time`, `arrival_time` fields — matches the enriched backend data from V0.22
- `TravelLegCard` displays departure/arrival times as a blue pill badge (e.g., "6:00 AM → 2:30 PM") and transfer count as an amber pill badge (e.g., "1 transfer")
- Card now shows fare from Google Directions API (e.g., "₹445") when available, falling back to LLM-estimated cost — real fares take priority over estimates

---

## V0.28 — Prompt Quality: Enriched Reviewer Context

**Status:** Complete

### Changes from V0.27

**Prompt Engineering**
- Reviewer now receives enriched travel leg data: distance (km), fare, transfer count, and departure/arrival times — previously only saw mode and duration. This allows the reviewer to make better judgments about transport feasibility (e.g., flagging a 12-hour bus with 3 transfers when a direct train exists)
- City detail in reviewer prompt now includes highlight count — helps assess whether a city has enough activities for its allocated days
- Reviewer travel detail format: `"Mumbai → Goa: train (10.5h, 588km) [fare: ₹445, 1 transfer(s), 06:00 AM → 04:30 PM]"`

---

## V0.27 — Google API Leverage: Editorial Summaries for Places

**Status:** Complete

### Changes from V0.26

**Google API Data Flow**
- Added `editorialSummary` to Google Places nearby search field mask — famous places now include a Google-authored one-sentence description (e.g., "Iconic 17th-century white marble mausoleum") at no additional API cost
- Added `editorial_summary` field to `PlaceCandidate` model
- LLM planning prompt now includes `description` field for places that have editorial summaries — gives the AI planner richer context for selection decisions (e.g., understanding what makes a place special beyond just its type and rating)

---

## V0.26 — Data Flow: Complete Activity Data in V6 Day Plans

**Status:** Complete

### Changes from V0.25

**Code & Data Path Flow**
- V6 journey day plan stream now serializes complete activity data — previously only sent `name`, `category`, `address`, `location`, `rating` to the frontend; now includes `place_id`, `photo_url`, `website`, `opening_hours`, `notes`, and `route_to_next`
- `route_to_next` (walking/driving distance and duration between activities) is now included in the SSE payload — enables frontend to show travel times between activities in journey mode
- Activity `id` field now included — enables frontend to reference specific activities for chat editing
- Photo URLs that were already computed by `_candidate_to_place()` but dropped at the serialization boundary now flow through to the frontend

---

## V0.25 — Prompt Quality: Scout Constraints & Consistency

**Status:** Complete

### Changes from V0.24

**Prompt Engineering**
- Added highlight duration constraints to Scout system prompt: total highlight hours per city must not exceed 70% of available day hours (10 active hours/day). A 2-day city caps at ~14h of activities, 3-day at ~21h. Prevents Scout from overloading cities with infeasible activity counts
- Fixed conflicting origin city guidance: user prompt now aligns with system prompt — origin is departure point, only included in cities if it matches destination type AND has tourist value (was: "should be FIRST city if it has tourist value")
- Added travel legs count validation in `scout.py`: logs warning when LLM returns wrong number of travel legs (should be N-1 for N cities)

---

## V0.24 — Google API Leverage: Place Website URLs

**Status:** Complete

### Changes from V0.23

**Google API Data Flow**
- Added `websiteUri` to Google Places nearby search field mask — no additional API cost, same request now returns website URLs for places that have them
- Added `website` field to `PlaceCandidate` model to carry the URL through the pipeline
- `_candidate_to_place()` in `generator.py` now passes `website` through to the finalized `Place` model — previously `Place.website` was always `None`
- Frontend `ActivityCard` already renders a "Website" link when `website` is present; this change makes it actually receive data

---

## V0.23 — Data Flow: Real Distances in TSP Optimizer

**Status:** Complete

### Changes from V0.22

**Code & Data Path Flow**
- `get_distance_matrix()` now returns both duration and distance matrices (was returning only durations despite already fetching `distanceMeters` from Google Routes API)
- TSP optimizer `_calculate_totals()` uses real Google-provided distances instead of estimating from duration via `duration * 5000 / 3600` (assumed 5 km/h walking speed)
- `_build_distance_matrix()` and `_optimize_tsp()` updated to thread the distance matrix through the optimization pipeline alongside the duration matrix

---

## V0.22 — Google API Leverage: Surface Transit Data

**Status:** Complete

### Changes from V0.21

**Google API Data Flow**
- Transit fare, transfers, departure/arrival times are now surfaced on `TravelLeg` — these were already parsed from the Google Directions API but discarded in the enricher. Added `fare`, `num_transfers`, `departure_time`, `arrival_time` fields to `TravelLeg` dataclass
- Enricher `_populate_transit_details()` now extracts all transit metadata (agency name, line names, fare text) instead of only the first step's line name
- Multi-step transit routes produce richer notes: `"Shatabdi Express (Indian Railways) → Metro Line 2 | 6:00 AM → 2:30 PM"` instead of just `"Shatabdi Express - 6:00 AM → 2:30 PM"`
- Journey response serialization (`_format_journey_response`) and round-trip deserialization (`_parse_journey_dict`) now include all transit fields — frontend receives fare, transfers, and times in the JSON payload

---

## V0.21 — Prompt Quality: Better Place Selection

**Status:** Complete

### Changes from V0.2

**Prompt Engineering**
- Places are now sorted by quality score (`rating × log(reviews)`) before truncation in `planning.py` prompt builder — ensures the LLM sees the highest-quality attractions and dining options first, even when discovery finds 50+ candidates and only 25 can fit in the prompt
- Validation prompt alternatives now include `rating`, `reviews`, `lat`, `lng` data — the LLM can make informed substitution decisions (choose a 4.8★ restaurant with 2000 reviews over a 3.9★ one with 12 reviews, and pick geographically proximate replacements)

---

## V0.2 — Robustness & Performance

**Status:** Complete

### Changes from V0.1

**Backend Bug Fixes**
- Fixed unchecked LLM response crash: `azure_openai.py` now validates `response.choices` is non-empty before accessing, preventing IndexError on malformed LLM responses
- Fixed fragile duration string parsing in `google_routes.py`: replaced brittle `rstrip("s")` with regex-based `_parse_duration()` that handles empty strings and malformed responses gracefully
- Fixed silent day skipping in `fast/generator.py`: days with no valid places now produce an empty "Free Day" entry instead of being silently dropped from the itinerary
- Consolidated duplicate pace multipliers: removed `PACE_MULTIPLIERS` dict from `schedule_builder.py`, now uses `PACE_CONFIGS.duration_multiplier` from `planning.py` as single source of truth

**Backend Performance**
- Parallelized place discovery: `google_places.py` `discover_places()` now runs all searches (essential types, dining, user interests) concurrently via `asyncio.gather()` instead of sequentially — reduces discovery phase from ~15-30s to ~3-5s
- Deduplicated travel mode mapping in `google_routes.py`: extracted `_TRAVEL_MODE_MAP` as module-level constant, removing duplicate inline dicts

**Backend Resilience**
- Added 15-second request timeouts to all external API calls across `google_places.py`, `google_routes.py`, and `google_directions.py` — prevents requests from hanging indefinitely on slow API responses

**Frontend Improvements**
- Added cancel button to `GenerationProgress` component: users can now abort long-running generations (journey planning ~2-5min, day plans) with visible cancel button in progress header
- Added `aria-live="polite"` to progress status messages for screen reader accessibility
- Moved render constants (phase emoji maps, step messages) to module level in `App.tsx` to prevent unnecessary object re-creation on every render

### Known Limitations (carried from V0.1)

- No frontend state persistence — plans are lost on page reload
- Budget field exists in models but is not deeply integrated into generation logic
- No frontend tests
- Chat editing capabilities are functional but basic

---

## V0.1 — Initial Release

**Status:** Complete

### What's Working

**Multi-City Journey Planning (V6 Architecture)**
- Region or specific destination input with origin city
- AI-driven city selection via Scout agent (Azure OpenAI GPT-4o)
- Google APIs enrichment for real transport times, coordinates, and distances
- Iterative quality refinement: Scout → Enrich → Review → Planner loop (up to 3 iterations, min score 70)
- Multi-modal transport: flight, bus, train, ferry, car
- SSE streaming with real-time progress updates
- Day plan generation for each city stop
- Natural language chat editing for both journey structure and day plans

**Single-City Itinerary (FAST Mode)**
- Single-pass generation in ~15-30s
- Google Places discovery for real venue data (ratings, hours, photos)
- LLM-driven place selection and theming
- TSP-based route optimization to minimize backtracking
- Time-slotted schedule builder with conflict validation
- 7-metric quality scoring (meal timing, geographic efficiency, travel efficiency, variety, opening hours, theme alignment, duration balance)

**Frontend**
- Dual-mode UI: toggle between Journey and Itinerary planning
- Journey phase flow: input → planning → preview → day-plans
- Real-time SSE progress display with phase tracking
- Journey visualization: city cards, travel leg cards, route arrows
- Itinerary visualization: day cards with activity timelines
- Chat interface for editing plans via natural language
- Side panel UX for day plan generation
- Tailwind CSS styling with glass-morphism cards and gradient backgrounds
- Cancellation support via AbortController

**Backend**
- FastAPI with async throughout (httpx.AsyncClient)
- Service registry for lazy singleton clients
- Centralized prompt templates (Markdown files)
- Pydantic v2 models with validation
- Backend pytest suite (model validation, quality scoring, integration tests)

### Known Limitations

- No frontend state persistence — plans are lost on page reload
- Budget field exists in models but is not deeply integrated into generation logic
- Limited error recovery if external APIs (Google, Azure) fail mid-generation
- No frontend tests
- Chat editing capabilities are functional but basic — limited to single-turn regeneration
- Destination type constraints (e.g., "islands only") are supported but not exhaustive
