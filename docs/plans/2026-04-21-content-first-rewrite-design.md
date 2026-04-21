# Content-First Platform Rewrite — Design Document

**Date:** 2026-04-21
**Status:** Approved
**Scope:** Full rewrite of travel-companion from per-request LLM generation to pre-generated content library

---

## Problem

The current system generates every trip from scratch via a multi-agent LLM pipeline (Scout → Enrich → Review → Planner, 2-5 minutes, ~$2-3 per request). Most travelers visit the same ~200 popular cities. Generating fresh plans per request is wasteful — identical LLM + Google API calls repeat for every user who visits Tokyo, Paris, or Barcelona.

## Solution

Pre-generate a content library of high-quality city plans, fully grounded with Google APIs. At request time, assemble journeys from this library — near-zero latency, near-zero LLM cost for repeat cities. The LLM's role shifts from per-request generation to offline curation and quality review.

## Core Principles

1. **Every activity has a `place_id`.** No LLM-hallucinated places. Google Places API is the single source of truth for location data.
2. **LLM curates, never invents.** The LLM selects from Google-grounded candidates, writes descriptions, themes days, and reviews quality. It does not create places.
3. **Immutable published variants.** Once a plan variant is published, it's never edited — only replaced by a new generation. User journeys reference stable snapshots.
4. **Offline quality, online speed.** Batch pipeline spends 5-10 minutes per city variant with 5 review iterations. Users get results in 2-5 seconds.

---

## Content Library Structure

```
City (e.g., "Tokyo")
├── metadata: location, country, timezone, currency, population tier
├── places[]: Google Places-grounded POIs (top 30-50 per city, shared across variants)
├── variants[]:
│   ├── (relaxed, moderate, 3 days)
│   ├── (moderate, moderate, 3 days)
│   ├── (packed, moderate, 3 days)
│   └── each variant:
│       ├── day_plans[]: themed days with activities, routes, schedules, meals
│       ├── accommodation: hotel + 2 alternatives (Google Places verified)
│       └── cost_breakdown: per-day and total
└── refresh_metadata: last_generated, data_hash for diff detection
```

### Initial scope: 20-30 cities, 3 variants each (relaxed/moderate/packed at moderate budget, 3 days). Expand based on demand.

---

## Google API Grounding Matrix

Every data point in the content library traces to a Google API source. This is the grounding guarantee.

| Data Point | Google API Source | Field Used | Fallback |
|---|---|---|---|
| Activity location | Places `searchNearby` / `searchText` | `location.latLng` | None — required |
| Activity name, address | Places | `displayName`, `formattedAddress` | None — required |
| Rating, review count | Places | `rating`, `userRatingCount` | None — required |
| Opening hours | Places | `regularOpeningHours` | LLM estimate (flagged as unverified) |
| Photos | Places | `photos[].name` | None — activity has no photo |
| Editorial summary | Places | `editorialSummary` | None — nullable |
| Price level | Places | `priceLevel` | LLM estimate for dining; null for others |
| Place types | Places | `types[]` | None — required |
| Business status | Places | `businessStatus` | Assumed OPERATIONAL |
| Website | Places | `websiteUri` | None — nullable |
| Routes between activities | Routes API `computeRoutes` | `duration`, `distanceMeters`, `polyline` | Haversine estimate |
| Walk vs drive decision | Routes API | Compare walk/drive durations | Pace-based threshold |
| City-to-city transport | Directions API (legacy) | `routes[].legs[].steps[]` with transit details | LLM estimate |
| Transit fares | Directions API | `fare` | None — nullable |
| Transit line details | Directions API | `transit_details.line` | None — nullable |
| Weather forecasts | Weather API `forecast/days` | `forecastDays[]` | None — fetched at journey assembly time |
| Hotel metadata | Places `searchText` (lodging) | Same fields as above | None — required |
| Hotel pricing | **LLM** (Google has no lodging pricing) | N/A | Budget fallback table |
| Dining cost estimates | **LLM** (city + budget aware) | N/A | Generic per-tier estimate |
| Day themes, descriptions | **LLM** (curation) | N/A | None — required from LLM |
| Activity descriptions | **LLM** (contextual to day theme) | N/A | Editorial summary fallback |

**LLM-sourced fields are clearly marked.** They are the minority — most data is Google-grounded.

---

## Database Schema

### Content Library Tables

```sql
-- Cities in the catalog
CREATE TABLE cities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    country_code VARCHAR(3) NOT NULL,
    location JSONB NOT NULL,              -- {lat, lng}
    timezone VARCHAR(100) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    population_tier VARCHAR(20) NOT NULL,  -- mega / large / medium / small
    region VARCHAR(100),                   -- "East Asia", "Western Europe", etc.
    data_hash VARCHAR(64),                 -- SHA-256 of latest discovery results
    last_discovered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, country_code)
);

-- Google Places-grounded POIs (shared across variants within a city)
CREATE TABLE places (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    google_place_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(500) NOT NULL,
    address VARCHAR(1000),
    location JSONB NOT NULL,              -- {lat, lng}
    types VARCHAR(100)[] NOT NULL,
    rating FLOAT,
    user_rating_count INT,
    price_level SMALLINT,                 -- 0-4 or NULL
    opening_hours JSONB,                  -- [{day: 0-6, open: "HH:MM", close: "HH:MM"}]
    photo_references VARCHAR(500)[],      -- up to 5
    editorial_summary TEXT,
    website_url VARCHAR(1000),
    is_lodging BOOLEAN DEFAULT FALSE,
    business_status VARCHAR(50) DEFAULT 'OPERATIONAL',
    last_verified_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_places_city ON places(city_id);
CREATE INDEX idx_places_google_id ON places(google_place_id);
CREATE INDEX idx_places_lodging ON places(city_id, is_lodging) WHERE is_lodging = TRUE;

-- Pre-generated plan variants
CREATE TABLE plan_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    pace VARCHAR(20) NOT NULL,            -- relaxed / moderate / packed
    budget VARCHAR(20) NOT NULL,          -- budget / moderate / luxury
    day_count SMALLINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'generating',  -- generating / draft / published / stale / archived
    quality_score SMALLINT,               -- 0-100 from reviewer
    accommodation_id UUID REFERENCES places(id),
    accommodation_alternatives JSONB,     -- [{place_id, name, nightly_usd}]
    booking_hint TEXT,
    cost_breakdown JSONB,                 -- {accommodation, transport, dining, activities, total, per_day}
    generation_metadata JSONB,            -- {llm_provider, model, iterations, duration_ms, candidate_count}
    data_hash VARCHAR(64),                -- hash of candidates used to generate
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(city_id, pace, budget, day_count, status)
);

CREATE INDEX idx_variants_lookup ON plan_variants(city_id, pace, budget, day_count, status);

-- Day plans within a variant
CREATE TABLE day_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID NOT NULL REFERENCES plan_variants(id) ON DELETE CASCADE,
    day_number SMALLINT NOT NULL,         -- 1-indexed
    theme VARCHAR(255) NOT NULL,
    theme_description TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(variant_id, day_number)
);

-- Activities within a day plan (every activity grounded to a place)
CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day_plan_id UUID NOT NULL REFERENCES day_plans(id) ON DELETE CASCADE,
    place_id UUID NOT NULL REFERENCES places(id),  -- NOT NULL = grounding guarantee
    sequence SMALLINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    duration_minutes SMALLINT NOT NULL,
    category VARCHAR(50) NOT NULL,        -- cultural, dining, nature, shopping, etc.
    description TEXT,                     -- LLM-written, contextual to day theme
    is_meal BOOLEAN DEFAULT FALSE,
    meal_type VARCHAR(20),                -- breakfast / lunch / dinner / NULL
    estimated_cost_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(day_plan_id, sequence)
);

CREATE INDEX idx_activities_day ON activities(day_plan_id);

-- Routes between consecutive activities
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day_plan_id UUID NOT NULL REFERENCES day_plans(id) ON DELETE CASCADE,
    from_activity_id UUID NOT NULL REFERENCES activities(id),
    to_activity_id UUID NOT NULL REFERENCES activities(id),
    travel_mode VARCHAR(20) NOT NULL,     -- walk / drive / transit
    distance_meters INT NOT NULL,
    duration_seconds INT NOT NULL,
    polyline TEXT,                         -- encoded polyline for map rendering
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_routes_day ON routes(day_plan_id);
```

### User-Facing Tables

```sql
-- Users (same as current)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(20) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    avatar_url VARCHAR(1000),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(provider, provider_id)
);

-- Assembled journeys (lightweight — references content library)
CREATE TABLE journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    destination VARCHAR(500) NOT NULL,     -- original user input
    origin VARCHAR(500),
    start_date DATE NOT NULL,
    total_days SMALLINT NOT NULL,
    pace VARCHAR(20) NOT NULL,
    budget VARCHAR(20) NOT NULL,
    travelers JSONB,                       -- {adults, children, infants}
    city_sequence JSONB NOT NULL,           -- [{city_id, city_name, day_count, variant_id, start_day}]
    transport_legs JSONB,                  -- [{from_city, to_city, mode, duration_s, fare, polyline, details}]
    weather_forecasts JSONB,               -- [{city_id, date, condition, temp_high, temp_low, precip_chance}]
    cost_breakdown JSONB,                  -- {accommodation, transport, dining, activities, total}
    status VARCHAR(20) DEFAULT 'complete', -- complete / generating / partial
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_journeys_user ON journeys(user_id);

-- Shareable journey links
CREATE TABLE journey_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journey_id UUID NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    token VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Job Queue Table

```sql
-- PostgreSQL-based job queue (replaces Redis/arq)
CREATE TABLE generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(30) NOT NULL,        -- batch_generate / on_demand / refresh / upgrade_draft
    city_id UUID REFERENCES cities(id),
    parameters JSONB NOT NULL,            -- {pace, budget, day_count} or {refresh_scope: "all"}
    status VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued / running / completed / failed
    priority SMALLINT NOT NULL DEFAULT 0, -- higher = sooner (on_demand gets priority 10)
    progress_pct SMALLINT DEFAULT 0,      -- 0-100 for polling
    result JSONB,                         -- {variant_id} on success
    error TEXT,
    locked_by VARCHAR(100),               -- worker ID (prevents double-pickup)
    locked_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_jobs_queue ON generation_jobs(status, priority DESC, created_at)
    WHERE status = 'queued';
CREATE INDEX idx_jobs_city ON generation_jobs(city_id, job_type);
```

### Job Queue Worker Protocol

The PostgreSQL job queue uses `SELECT ... FOR UPDATE SKIP LOCKED` for safe concurrent worker pickup:

```sql
-- Worker picks next job
UPDATE generation_jobs
SET status = 'running', locked_by = :worker_id, locked_at = now(), started_at = now()
WHERE id = (
    SELECT id FROM generation_jobs
    WHERE status = 'queued'
    ORDER BY priority DESC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING *;

-- Worker completes job
UPDATE generation_jobs
SET status = 'completed', completed_at = now(), progress_pct = 100, result = :result
WHERE id = :job_id;

-- Stale job recovery (locked > 15 min with no completion)
UPDATE generation_jobs
SET status = 'queued', locked_by = NULL, locked_at = NULL, started_at = NULL
WHERE status = 'running' AND locked_at < now() - INTERVAL '15 minutes';
```

---

## Pipelines

### Pipeline 1: Batch Generation (offline, high quality)

Runs offline with no time pressure. Spends 5-10 minutes per city variant to maximize quality.

```
Input: (city_name, pace, budget, day_count)

Step 1 — DISCOVER (Google APIs only, no LLM)
├── Geocode city → location, country, timezone, currency
├── Places searchNearby → 100-150 candidates across all interest categories
│   Categories: cultural, dining, nature, shopping, nightlife, entertainment, religious, markets
│   Parallel queries per category via asyncio.gather
├── Places searchText × 4 → landmarks, "best places in {city}", entertainment, nature
├── Places searchText (lodging) → 10-15 hotels, filter by budget-appropriate types
├── Deduplicate all candidates by google_place_id
├── Quality filter: adaptive thresholds (rating ≥ 3.5, reviews ≥ 30, adjust for density)
├── Upsert all candidates into `places` table (shared across variants)
└── Output: PlaceCandidate[] with full metadata (every candidate has google_place_id)

Step 2 — CURATE (LLM, structured output)
├── Input: all candidates as JSON + city metadata + pace/budget/day_count
├── System prompt instructs:
│   - Select activities ONLY from provided candidates (reference by google_place_id)
│   - Theme each day (e.g., "Ancient Temples & Zen Gardens")
│   - Place meals at culture-appropriate times
│   - Respect pace: relaxed=4-5 activities/day, moderate=5-7, packed=7-9
│   - Select 1 accommodation + 2 alternatives from lodging candidates
│   - Write contextual descriptions for each activity
│   - Estimate costs (accommodation nightly rate, dining per meal tier)
├── Output schema: structured JSON with day plans referencing candidate IDs
└── Constraint: LLM output is validated — any activity ID not in candidate set is rejected

Step 3 — ROUTE (Google APIs only, no LLM)
├── Per day: compute_route() between consecutive activities via Routes API
├── Walk vs drive selection using pace-aware thresholds:
│   - Relaxed: walk if ≤ 25 min, else drive
│   - Moderate: walk if ≤ 20 min, else drive
│   - Packed: walk if ≤ 15 min, else drive
├── Run TSP optimization (nearest-neighbor) to minimize total travel time
├── Recompute routes after TSP reorder
└── Output: Route[] with distance, duration, polyline per leg

Step 4 — SCHEDULE (deterministic, no LLM)
├── Assign time slots respecting:
│   - Opening hours (hard constraint — truncate or skip violations)
│   - Culture-aware meal windows (~80 countries, 10 regional profiles)
│   - Pace multipliers: relaxed=1.3× duration, moderate=1.0×, packed=0.8×
│   - Transit time between activities (from Step 3)
├── Enforce closing time: activities ending after close are truncated or dropped
└── Output: fully timed schedule (start_time, end_time per activity)

Step 5 — REVIEW (LLM, quality scoring)
├── 7-dimension scoring:
│   1. Theme coverage (10%) — do activities match the day theme?
│   2. Landmark inclusion (15%) — are iconic spots included?
│   3. Variety (15%) — mix of categories across days?
│   4. Duration realism (10%) — are time allocations reasonable?
│   5. Pacing (15%) — appropriate gaps, no marathon days?
│   6. Meals (20%) — breakfast/lunch/dinner at right times?
│   7. Activity count (15%) — matches pace tier?
├── Score threshold: 80 (higher than current 75 — no time pressure)
├── If fails: LLM Fixer swaps activities from candidate pool
│   → re-route (Step 3) → re-schedule (Step 4) → re-review
├── Max 5 iterations (up from current 3)
├── Track best-scoring plan across iterations
└── Output: final plan (best of up to 5 attempts)

Step 6 — COST (deterministic + LLM estimates)
├── Accommodation: from LLM curation step (city + budget calibrated nightly rate)
├── Activities: from Google Places priceLevel where available, else LLM estimate
├── Dining: LLM estimate per meal tier (street food / mid-range / fine dining × city)
├── Transport: mode-based estimate from route durations
└── Output: cost_breakdown {accommodation, transport, dining, activities, total, per_day[]}

Step 7 — STORE
├── Insert plan_variant (status: 'draft' or 'published' if score ≥ 80)
├── Insert day_plans, activities, routes
├── Store data_hash (SHA-256 of candidate google_place_ids used)
├── Update generation_job status
└── If upgrading a draft: archive old variant, publish new one
```

### Pipeline 2: On-Demand Draft (real-time, for cache misses)

When a user requests a city with no published variant. Stripped-down single-pass, optimized for speed.

```
Input: (city_name, pace, budget, day_count) — from cache miss during journey assembly

Step 1 — DISCOVER (parallel, reduced scope)
├── Geocode + searchNearby + searchText in parallel
├── 40-60 candidates (fewer category queries than batch)
├── Top 3 hotels only (skip exhaustive lodging search)
└── Upsert candidates to places table

Step 2 — CURATE (single LLM call, no review/fix loop)
├── Same prompt as batch but with instruction for single-pass quality
└── Accept output as-is (no iteration)

Step 3 — ROUTE + SCHEDULE (same as batch)

Step 4 — STORE
├── Insert plan_variant with status: 'draft'
├── Create upgrade job: {job_type: 'upgrade_draft', priority: 5}
└── Return variant_id to assembler immediately

Latency target: 15-30 seconds
```

### Pipeline 3: Journey Assembler (real-time, mostly deterministic)

Stitches pre-made city plans into a multi-city journey. This is the primary user-facing flow.

```
Input: {destination, origin, start_date, total_days, pace, budget, travelers}

Step 1 — ALLOCATE
├── Lightweight LLM call (or deterministic for well-known routes):
│   Input: destination, total_days, pace, interests
│   Output: ordered city list + days per city
│   Example: "Japan 10 days" → Tokyo(4d) → Kyoto(3d) → Osaka(3d)
├── For multi-country destinations:
│   First: Country Allocator (which countries, how many days each)
│   Then: City allocation within each country
└── Deterministic fallback: popular fixed itineraries (Japan, Italy, etc.)

Step 2 — LOOKUP
├── For each city in sequence:
│   Query: SELECT * FROM plan_variants
│          WHERE city_id = :city AND pace = :pace AND budget = :budget
│          AND day_count = :days AND status = 'published'
│   ├── Exact match → use directly
│   ├── Close match (have 3d, need 4d) → use closest + flag for future generation
│   ├── No match → trigger Pipeline 2 (on-demand draft)
│   └── Parallel lookups for all cities via asyncio.gather
└── Output: variant_id per city (or job_id for pending generation)

Step 3 — CONNECT (Google Directions API)
├── For each consecutive city pair:
│   get_all_transport_options(city_a, city_b)
│   → driving route + transit routes with fares, line details, transfers
├── Parallel API calls for all city pairs
└── Output: TransportLeg[] between cities

Step 4 — WEATHER (Google Weather API)
├── For each city: get_daily_forecast(location, trip_dates)
├── Attach weather to corresponding day plans
├── Generate warnings for rain/storm days
└── Parallel API calls for all cities

Step 5 — ASSEMBLE
├── Stitch: city_sequence + variant day_plans + transport_legs + weather
├── Stamp actual dates (day plans are date-agnostic in content library)
├── Compute total cost_breakdown (sum city costs + transport)
├── Adjust traveler multiplier (costs × adults, reduced for children)
├── Save assembled journey to `journeys` table
└── Return complete journey to user

Latency: 2-5 seconds (all cached) / 15-30 seconds (one city generating)
```

### Pipeline 4: Smart Weekly Refresh

Detects changes in Google Places data and regenerates affected variants.

```
Trigger: PostgreSQL-based cron job (generation_job with type 'refresh', scheduled weekly)

For each published city:
├── 1. Re-run Discovery queries (same searchNearby + searchText as batch)
├── 2. Compute new data_hash (SHA-256 of sorted google_place_ids + ratings + hours)
├── 3. Compare to stored cities.data_hash
├── If match → skip (no changes detected)
├── If mismatch:
│   ├── Diff analysis:
│   │   - New places added? (new popular restaurants, attractions)
│   │   - Places removed? (closed businesses — business_status != OPERATIONAL)
│   │   - Rating changes? (significant = ±0.3 or ±50 reviews)
│   │   - Opening hours changes?
│   ├── Minor changes (hours/rating shift):
│   │   Update places table in-place
│   │   No variant regeneration needed
│   ├── Major changes (place closed, new landmark, >20% candidate turnover):
│   │   Mark all published variants for this city as 'stale'
│   │   Queue batch_generate jobs for each stale variant
│   └── Update cities.data_hash and cities.last_discovered_at
└── Log refresh report (cities checked, changes found, jobs queued)

Cost: ~$0.01-0.02 per city per week (Places API calls only for unchanged cities)
Total for 30 cities: ~$0.30-0.60/week
```

---

## API Design

### Public APIs (user-facing, all require auth except where noted)

```
# Browse catalog
GET  /api/cities                              → paginated city list
     query: ?region=East+Asia&sort=name&limit=20&offset=0
     response: {cities: [{id, name, country, photo_url, variant_count}], total}

GET  /api/cities/:city_id                     → city detail
     response: {id, name, country, location, timezone, currency, landmarks: [...],
                available_variants: [{pace, budget, day_count, quality_score}]}

GET  /api/cities/:city_id/variants            → list variants for a city
     query: ?pace=relaxed&budget=moderate
     response: {variants: [{id, pace, budget, day_count, quality_score, cost_total}]}

GET  /api/cities/:city_id/variants/:variant_id → full variant detail
     response: {variant with day_plans, activities (with place details), routes, costs}

# Journey assembly
POST /api/journeys                            → assemble a journey
     body: {destination, origin, start_date, total_days, pace, budget, travelers}
     response (cached): {journey_id, status: "complete", journey: {...}}
     response (generating): {journey_id, status: "generating", job_ids: [...]}

GET  /api/journeys/:id                        → get journey
     response: full assembled journey with day plans, routes, weather, costs

GET  /api/journeys                            → list user's journeys
     query: ?limit=50&offset=0
     response: {journeys: [{id, destination, start_date, total_days, city_count}], total}

DELETE /api/journeys/:id                      → delete journey

# Job polling (on-demand generation)
GET  /api/jobs/:job_id                        → check generation status
     response: {status, progress_pct, estimated_seconds_remaining}

# Sharing
POST /api/journeys/:id/share                  → create shareable link
     response: {token, url}
DELETE /api/journeys/:id/share                → revoke sharing
GET  /api/shared/:token                       → get shared journey (no auth)

# Export
GET  /api/journeys/:id/export/pdf             → PDF trip book
GET  /api/journeys/:id/export/calendar        → .ics calendar

# Places (unchanged)
GET  /api/places/search                       → Google Places search proxy
GET  /api/places/photo/:ref                   → Google Places photo proxy

# Auth (unchanged)
GET  /api/auth/login/:provider
GET  /api/auth/callback/:provider
POST /api/auth/logout
GET  /api/auth/me                             → (no auth required)

# Health
GET  /health                                  → {status, version, cities_count, variants_count}
```

### Admin APIs (batch pipeline management, require admin role)

```
POST /api/admin/cities                        → add city to catalog
     body: {name, country}
     → geocodes city, creates record, queues initial discovery

POST /api/admin/cities/:id/generate           → trigger batch generation
     body: {pace, budget, day_count}
     → creates generation_job

POST /api/admin/cities/:id/refresh            → trigger refresh check
     → creates refresh job

GET  /api/admin/jobs                          → list jobs
     query: ?status=running&job_type=batch_generate
     response: {jobs: [...], total}

POST /api/admin/jobs/refresh-all              → trigger weekly refresh for all cities
     → creates one refresh job per published city

GET  /api/admin/stats                         → dashboard stats
     response: {cities_count, published_variants, draft_variants, jobs_pending,
                jobs_running, total_places, last_refresh_at}
```

---

## Tech Stack

### Backend (changes from current)

| Component | Current | New | Rationale |
|---|---|---|---|
| Framework | FastAPI | **FastAPI** | No change needed |
| Python | 3.14 | **3.14** | No change needed |
| Database | PostgreSQL 16 | **PostgreSQL 16** | No change needed |
| ORM | SQLAlchemy 2.0 async | **SQLAlchemy 2.0 async** | No change needed |
| Migrations | Alembic | **Alembic** | No change needed |
| Job Queue | None (inline async) | **PostgreSQL-based** (`SELECT FOR UPDATE SKIP LOCKED`) | Simple, no extra infra, transactional consistency |
| LLM | Multi-provider (Azure/Anthropic/Gemini) | **Same multi-provider** | Called far less frequently (batch only) |
| HTTP Client | httpx async | **httpx async** | No change needed |
| PDF Export | weasyprint | **weasyprint** | No change needed |

### Frontend (changes from current)

| Component | Current | New | Rationale |
|---|---|---|---|
| Framework | React 19 + Vite | **React 19 + Vite** | No change needed |
| State | Zustand 5 | **Zustand 5** | No change needed |
| Styling | Tailwind v4 + shadcn/ui | **Tailwind v4 + shadcn/ui** | No change needed |
| Routing | React Router | **React Router** | No change needed |
| Maps | Google Maps JS | **Google Maps JS** | No change needed |
| DnD | @dnd-kit | **Drop for MVP** | No activity reorder in MVP |

### Infrastructure

| Component | Choice | Rationale |
|---|---|---|
| Job queue | PostgreSQL table + `SKIP LOCKED` | Zero additional infrastructure |
| Cron scheduling | generation_jobs table with scheduled `created_at` | Worker checks for due jobs periodically |
| Worker process | Separate Python process (same codebase, CLI entrypoint) | `python -m app.worker` |

### Dropped from current system

| Component | Why |
|---|---|
| SSE streaming | Pre-generated content serves instantly; on-demand uses simple polling |
| Complex orchestrators (`journey.py`, `day_plan.py`) | Replaced by batch pipeline + assembler |
| Review/Planner iteration loop at request time | Moved entirely to offline batch pipeline |
| Chat editing | Deferred to post-MVP (future LLM customization layer) |
| Tips generation | Deferred to post-MVP |
| Quick edit / reorder | Deferred to post-MVP |
| Rate limiting on plan endpoints | Negligible cost for cached lookups |

### Reused from current system

| Component | How it's reused |
|---|---|
| `app/services/google/places.py` | Discovery in batch + on-demand pipelines (near-identical API calls) |
| `app/services/google/routes.py` | Route computation in batch + on-demand pipelines |
| `app/services/google/directions.py` | City-to-city transport in journey assembler |
| `app/services/google/weather.py` | Weather in journey assembler |
| `app/services/llm/` (all providers) | Curation + review in batch pipeline, allocation in assembler |
| `app/algorithms/tsp.py` | TSP optimization in batch pipeline |
| `app/algorithms/scheduler.py` | Schedule building in batch pipeline |
| `app/algorithms/quality/` | 7-dimension scoring in batch review step |
| `app/core/auth.py` | OAuth + JWT (unchanged) |
| `app/core/http.py` | Shared httpx client with retry |
| `app/core/middleware.py` | Request tracing, security headers |
| `app/prompts/loader.py` | Prompt template loading (new prompts, same infrastructure) |

---

## Frontend UX Flow

### Two entry points

**1. Browse Mode — explore the city catalog**

```
Home
└── City Catalog Grid
    ├── Search bar + region filter + sort (name / rating / popular)
    ├── City cards: hero photo, name, country, "X-day plans available"
    └── Click city →
        City Detail Page
        ├── Hero image, map, key landmarks list
        ├── Variant picker: pace × budget matrix (highlight available)
        ├── Selected variant preview: day themes, activity count, cost
        └── "View Full Plan" →
            Plan View (day-by-day timeline)
            ├── Day tabs / swipe navigation
            ├── Activity cards (photo-first, same component as current)
            ├── Route lines on map
            ├── Cost breakdown
            └── "Plan a trip here" → pre-fills journey wizard
```

**2. Journey Mode — input a full trip**

```
Home
└── Trip Wizard
    ├── Destination, origin, dates, pace, budget, travelers
    └── Submit →
        Loading Screen
        ├── If all cities cached: 2-5 seconds, simple spinner
        ├── If generating: progress bar + "Preparing your trip..."
        │   Poll GET /api/jobs/:id every 3 seconds
        └── Done →
            Journey Dashboard
            ├── City cards in sequence with transport legs between them
            ├── Total cost breakdown
            ├── Weather forecasts per city
            └── Click city → same Plan View as browse mode
```

### Shared components (reused from current frontend)

- Photo-first activity cards (hero banner layout with gradient overlay)
- Day timeline with time slots
- Google Maps with route polylines
- Budget breakdown (stacked bar chart)
- Weather day atmosphere gradients (amber=sunny, blue=rain, gray=clouds)
- Dark mode (deep navy tones)
- Mobile swipe navigation between days
- Toast notifications
- Auth flow (OAuth login, JWT capture)

### New components

- City catalog grid with search/filter/sort
- Variant picker (pace × budget interactive matrix)
- Journey builder (multi-city sequence visualization)
- Simple loading screen with progress indicator (replaces SSE streaming UI)
- Admin dashboard (job queue, city management — optional for MVP)

### Dropped UX (deferred to post-MVP)

- Chat-based plan editing
- Activity tips panel
- Quick edit (±duration, remove)
- Activity drag-and-drop reorder
- Confetti celebration animation
- Contextual planning facts
- Celebration banner

---

## Cost Analysis

### Per-variant generation cost (batch pipeline)

| Step | API Calls | Estimated Cost |
|---|---|---|
| Discovery | ~15-20 Places API calls | ~$0.10-0.15 |
| Routing | ~10-20 Routes API calls per day × 3 days | ~$0.30-0.60 |
| LLM curation | 1 structured output call | ~$0.05-0.15 |
| LLM review | Up to 5 review + fix cycles | ~$0.25-0.75 |
| **Total per variant** | | **~$0.70-1.65** |

### Initial content library (20 cities × 3 variants)

```
60 variants × ~$1.00 average = ~$60 one-time cost
```

### Ongoing costs (monthly, assuming 1000 trips/month)

| Item | Current System | New System |
|---|---|---|
| LLM calls (per-request generation) | ~$2,000-3,000 | $0 (pre-generated) |
| LLM calls (batch pipeline) | $0 | ~$10-20 (refresh regenerations) |
| Google API (per-request) | ~$500-1,000 | ~$30-50 (weather + directions at assembly) |
| Google API (refresh) | $0 | ~$2-5 (weekly discovery checks) |
| On-demand drafts (~5% miss rate) | $0 | ~$25-50 |
| **Monthly total** | **~$2,500-4,000** | **~$70-125** |

**~97% cost reduction** at scale, assuming most users visit pre-generated cities.

---

## MVP Phases

### Phase 1 — Content Library + Browse (target: week 1-2)

**Backend:**
- New database schema + Alembic migrations (fresh DB, no migration from old schema)
- `places` table CRUD with Google Places upsert logic
- `cities` table with geocoding
- Batch generation pipeline (all 7 steps)
- `plan_variants`, `day_plans`, `activities`, `routes` CRUD
- Admin CLI: `python -m app.cli generate --city "Tokyo" --pace relaxed --budget moderate --days 3`
- City + variant read APIs
- Photo proxy (reuse existing)

**Frontend:**
- City catalog page (grid, search, filter)
- City detail page (landmarks, variant picker)
- Plan view page (day timeline, activity cards, map, costs)
- Dark mode, responsive design

**Content:**
- Generate variants for initial 20-30 cities

### Phase 2 — Journey Assembly (target: week 3)

**Backend:**
- Journey assembler (allocator + lookup + connect + weather + assemble)
- On-demand draft pipeline (for cache misses)
- PostgreSQL job queue + worker process
- Job polling API
- Journey CRUD APIs
- Auth integration (reuse existing OAuth + JWT)

**Frontend:**
- Trip wizard (destination, dates, pace, budget, travelers)
- Loading screen with polling
- Journey dashboard (city cards, transport legs, costs, weather)
- Saved journeys list

### Phase 3 — Refresh + Polish (target: week 4)

**Backend:**
- Smart weekly refresh pipeline
- Sharing (shareable links)
- PDF + calendar export (adapted to new schema)
- Admin stats API

**Frontend:**
- Share + export buttons
- Mobile polish
- Animations (staggered entry, scroll-reveal — reuse existing CSS)
- Error states, empty states

### Deferred (post-MVP)

- LLM-based customization (swap activities per user interests)
- Chat editing
- Tips generation
- Activity quick-edit / reorder / drag-and-drop
- Excursion day support
- City-specific seasonal variants
- User ratings/feedback on variants

---

## Project Structure (new)

```
travel-companion/
├── backend/
│   ├── app/
│   │   ├── main.py                    — FastAPI app setup
│   │   ├── dependencies.py            — DI wiring
│   │   ├── config/
│   │   │   ├── settings.py            — env vars (API keys, DB, OAuth)
│   │   │   └── planning.py            — product constants (thresholds, pace configs, meal profiles)
│   │   ├── core/
│   │   │   ├── auth.py                — JWT + OAuth (reused)
│   │   │   ├── http.py                — shared httpx client (reused)
│   │   │   └── middleware.py          — request tracing, security headers (reused)
│   │   ├── db/
│   │   │   ├── engine.py              — async SQLAlchemy engine
│   │   │   ├── models.py             — SQLAlchemy table models (new schema)
│   │   │   └── repository.py         — DB access layer
│   │   ├── routers/
│   │   │   ├── cities.py              — catalog browse APIs
│   │   │   ├── journeys.py            — journey assembly + CRUD
│   │   │   ├── admin.py               — batch pipeline management
│   │   │   ├── places.py              — photo proxy, search (reused)
│   │   │   ├── auth.py                — OAuth endpoints (reused)
│   │   │   └── export.py              — PDF + calendar
│   │   ├── services/
│   │   │   ├── google/                — places, routes, directions, weather (reused)
│   │   │   └── llm/                   — multi-provider abstraction (reused)
│   │   ├── pipelines/
│   │   │   ├── discovery.py           — Step 1: Google API discovery
│   │   │   ├── curation.py            — Step 2: LLM curation
│   │   │   ├── routing.py             — Step 3: route computation
│   │   │   ├── scheduling.py          — Step 4: time slot assignment
│   │   │   ├── review.py              — Step 5: quality review + fix loop
│   │   │   ├── costing.py             — Step 6: cost estimation
│   │   │   ├── batch.py               — full batch pipeline orchestration
│   │   │   └── draft.py               — on-demand draft pipeline
│   │   ├── assembler/
│   │   │   ├── allocator.py           — city allocation (LLM or deterministic)
│   │   │   ├── lookup.py              — variant lookup + close-match logic
│   │   │   ├── connector.py           — city-to-city transport
│   │   │   └── assembler.py           — final journey assembly
│   │   ├── worker/
│   │   │   ├── queue.py               — PostgreSQL job queue client
│   │   │   ├── runner.py              — worker loop (poll + execute)
│   │   │   └── refresh.py             — smart refresh logic
│   │   ├── algorithms/                — tsp, scheduler, quality evaluators (reused)
│   │   ├── models/                    — Pydantic models (new, matching new schema)
│   │   └── prompts/                   — new prompt templates
│   │       ├── curation/              — curator_system.md, curator_user.md
│   │       ├── review/                — reviewer_system.md, reviewer_user.md
│   │       ├── allocator/             — allocator_system.md, allocator_user.md
│   │       └── loader.py             — prompt loader (reused pattern)
│   ├── cli.py                         — admin CLI entrypoint
│   ├── alembic/                       — migrations (fresh)
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── CityCatalog.tsx
│   │   │   ├── CityDetail.tsx
│   │   │   ├── PlanView.tsx
│   │   │   ├── TripWizard.tsx
│   │   │   ├── JourneyDashboard.tsx
│   │   │   ├── SavedJourneys.tsx
│   │   │   └── SharedJourney.tsx
│   │   ├── components/
│   │   │   ├── ui/                    — shadcn/ui (reused)
│   │   │   ├── ActivityCard.tsx       — photo-first card (reused design)
│   │   │   ├── DayTimeline.tsx
│   │   │   ├── CityCard.tsx
│   │   │   ├── VariantPicker.tsx      — pace × budget matrix
│   │   │   ├── JourneyMap.tsx
│   │   │   ├── CostBreakdown.tsx
│   │   │   ├── WeatherBadge.tsx
│   │   │   └── LoadingScreen.tsx
│   │   ├── stores/
│   │   │   ├── catalogStore.ts        — city catalog state
│   │   │   ├── journeyStore.ts        — assembled journey state
│   │   │   ├── uiStore.ts             — UI state (phase, loading)
│   │   │   └── authStore.ts           — auth (reused)
│   │   ├── lib/
│   │   │   ├── api.ts                 — API client
│   │   │   └── utils.ts
│   │   └── App.tsx
│   └── ...
└── docs/plans/
```

---

## Open Questions (to resolve during implementation)

1. **Variant matrix expansion** — When do we expand beyond 3 variants per city? Demand-driven (track which pace/budget/day combos are requested but missing)?
2. **Close-match strategy** — If user needs 4 days but we have 3-day variant, do we: (a) extend by duplicating a day, (b) add a "free day" placeholder, (c) trigger on-demand generation?
3. **Admin UI** — Build a web admin dashboard for city/job management, or CLI-only for MVP?
4. **Old codebase** — Archive on a branch or delete entirely?
