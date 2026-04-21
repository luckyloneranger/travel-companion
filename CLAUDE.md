# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Regular Everyday Traveller (RET) — a content-first travel planning platform. Pre-generates high-quality multi-day city plans offline via a batch pipeline (Discover -> Curate -> Route -> Schedule -> Review -> Store), fully grounded with Google APIs. Users browse a city catalog or input trips; a journey assembler stitches pre-made city plans with live transport + weather data. On-demand drafts handle cache misses. A PostgreSQL-based job queue coordinates all background work.

## Build & Run Commands

### Backend (FastAPI + Python)
```bash
docker compose up -d db            # Start PostgreSQL 16 (first time)
cd backend
source venv/bin/activate          # Python virtual env
pip install -r requirements.txt   # Install deps
alembic upgrade head              # Run database migrations
uvicorn app.main:app --reload --port 8000  # Dev server
```

### Frontend (React + TypeScript + Vite)
```bash
cd frontend
npm install
npm run dev       # Vite dev server (port 5173), proxies /api to :8000
npm run build     # TypeScript check + production build
npm run lint      # ESLint
```

### Tests (Backend only)
```bash
cd backend
source venv/bin/activate
pytest                    # All tests
pytest -v                 # Verbose
pytest -k "test_health"   # Run specific tests
pytest --cov              # With coverage
```

Fixtures in `conftest.py` provide `app` (FastAPI with overrides), `client` (httpx AsyncClient), testcontainers PostgreSQL, and MockLLMService. Tests require Docker running.

## Architecture

### Code Flow
`routers/` -> `assembler/` + `pipelines/` + `worker/` + `services/` + `algorithms/`

- **Routers** (`app/routers/`): FastAPI endpoints — `cities.py` (city catalog browsing, variant listing), `journeys.py` (journey assembly + CRUD), `admin.py` (city management, job queue, generation triggers, stats), `sharing.py` (shareable journey links), `places.py` (place search, photo proxy), `auth.py` (OAuth login/callback/logout)
- **Pipelines** (`app/pipelines/`): Offline batch content generation
  - `discovery.py` — Google Places discovery for a city (landmarks, attractions, restaurants, nature)
  - `curation.py` — LLM curates discovered places into themed day plans
  - `routing.py` — TSP optimization + route computation for each day
  - `scheduling.py` — time-slot builder with culture-aware meal placement
  - `review.py` — LLM quality review + scoring (7 dimensions)
  - `costing.py` — cost estimation per activity and day
  - `batch.py` — orchestrates full pipeline: Discover -> Curate -> Route -> Schedule -> Review -> Store
  - `draft.py` — on-demand draft generation for cache misses (same pipeline, inline)
- **Assembler** (`app/assembler/`): Journey assembly from pre-made city plans
  - `allocator.py` — allocates days across cities based on trip duration
  - `lookup.py` — finds best matching plan variants from city catalog
  - `connector.py` — stitches cities with live transport (directions, fares) + weather data
  - `assembler.py` — top-level assembler coordinating allocator -> lookup -> connector
- **Worker** (`app/worker/`): Background job processing
  - `runner.py` — async worker that polls job queue and runs pipelines
  - `queue.py` — PostgreSQL-based job queue (enqueue, dequeue, status updates)
  - `refresh.py` — scheduled refresh of stale city plans
  - CLI: `cli.py` — command-line interface for manual city generation and worker management
- **Services** (`app/services/`):
  - `llm/` — Abstract `LLMService` base, `AzureOpenAILLMService` (supports reasoning models: o1, o3, gpt-5, with exponential backoff retry for transient errors), `AnthropicLLMService` (tool_use for structured output), `GeminiLLMService` (response_json_schema), `factory.py` for provider switching. All providers strip null characters from output.
  - `google/` — `GooglePlacesService` (discovery, geocoding, lodging), `GoogleRoutesService` (single/batch routes, distance matrices), `GoogleDirectionsService` (transit details, fares, transfers), `GoogleWeatherService` (daily forecasts)
- **Algorithms** (`app/algorithms/`): Deterministic computation — `tsp.py` (nearest-neighbor route optimizer), `scheduler.py` (time-slot builder with culture-aware meal placement across ~80 countries/10 regional profiles, pace multipliers, LLM meal window overrides via `from_context()`), `quality/` (7 context-aware evaluators: meal timing 20%, clustering 15% with auto city-scale detection, efficiency 15%, variety 15%, opening hours 15%, theme 10%, duration 10%)
- **Models** (`app/models/`): Pydantic v2 models — `common.py` (Location, Pace, TravelMode, TransportMode, Budget enums), `journey.py` (Journey, CityAllocation, TravelLeg), `day_plan.py` (DayPlan, Activity, Place, Route, Weather), `city.py` (City, PlanVariant), `user.py`
- **Database** (`app/db/`): SQLAlchemy 2.0 async + asyncpg (PostgreSQL) — `engine.py` (auto-SSL for remote hosts), `models.py` (10 tables: cities, places, plan_variants, day_plans, activities, routes, users, journeys, journey_shares, generation_jobs), `repository.py` (CityRepository, JourneyRepository, JobRepository). Alembic for schema migrations (`backend/alembic/`)
- **Prompts** (`app/prompts/`): Markdown templates loaded via `PromptLoader` in `loader.py` — curation, review, costing prompts for batch pipeline
- **Config** (`app/config/`): Settings (Pydantic BaseSettings for env vars), planning configs (`planning.py` — pace configs, fallback duration-by-type table, interest-to-place-type seed mapping, adaptive place filters, haversine fallback computation, `LODGING_TYPES` filter set, `ROUTE_COMPUTATION_MODE`), regional transport guidance (`regional_transport.py`)
- **Core** (`app/core/`): JWT auth (`auth.py`), shared HTTP client with retry/exponential backoff (`http.py`), request tracing middleware with security headers (`middleware.py` — X-Request-ID, X-Content-Type-Options, X-Frame-Options, Referrer-Policy), global exception handler (`main.py`), per-user sliding window rate limiting (`rate_limit.py`)
- **Dependencies** (`app/dependencies.py`): FastAPI `Depends()` wiring for all services, assembler, repositories, auth, and DB sessions

### Key Patterns

**Dependency Injection** — all services and components are wired via FastAPI `Depends()` in `app/dependencies.py`:
```python
from app.dependencies import get_assembler, get_journey_repository

@router.post("/journeys")
async def create_journey(
    request: JourneyRequest,
    assembler: JourneyAssembler = Depends(get_assembler),
    repo: JourneyRepository = Depends(get_journey_repository),
):
```

**LLM Abstraction** — provider-agnostic via abstract base class + factory:
```python
from app.services.llm.factory import create_llm_service
llm = create_llm_service(settings)  # returns AzureOpenAI, Anthropic, or Gemini based on LLM_PROVIDER
data = await llm.generate_structured(system, user, schema=MyModel)
```

Each provider implements structured output differently:
- Azure OpenAI: `response_format={"type": "json_object"}`, special handling for reasoning models (o1/o3/gpt-5: uses `max_completion_tokens`, omits temperature)
- Anthropic: tool_use pattern with `tool_choice={"type": "tool", "name": "submit"}`
- Gemini: `response_mime_type` + `response_json_schema` from Pydantic model

**Prompt Templates** — centralized .md templates with category-based loaders:
```python
from app.prompts.loader import pipeline_prompts
system = pipeline_prompts.load("curation_system")
user = pipeline_prompts.load("review_user")
```

**Batch Pipeline** — offline content generation runs as background jobs:
```python
# Enqueue city generation
job_id = await queue.enqueue("generate_city", {"city": "Tokyo", "days": 3, "pace": "moderate"})
# Worker picks up and runs full pipeline
await batch.run_pipeline(city="Tokyo", days=3, pace="moderate")  # Discover -> Curate -> Route -> Schedule -> Review -> Store
```

**Journey Assembler** — stitches pre-made city plans into multi-city journeys:
```python
# Allocator distributes days, lookup finds best variants, connector adds transport + weather
journey = await assembler.assemble(cities=["Tokyo", "Kyoto", "Osaka"], total_days=10, start_date="2026-05-01")
```

**Job Queue** — PostgreSQL-based background job processing:
```python
# Jobs table tracks status: pending -> running -> completed/failed
job = await queue.enqueue("generate_city", payload)
status = await queue.get_status(job_id)  # {status, progress, result, error}
```

**Zustand Stores** — frontend state management via three stores:
- `catalogStore.ts` — city catalog browsing, variant selection, search/filter state
- `journeyStore.ts` — assembled journey, city allocations, transport legs, saved journeys CRUD
- `uiStore.ts` — phase management (browse -> assemble -> preview -> live), navigation state
- `authStore.ts` — user authentication state, JWT capture from OAuth redirect hash fragment (`#token=`), periodic token refresh (30 min), auto-logout on 401

**Request Tracing** — `RequestTracingMiddleware` adds `X-Request-ID` to every request/response with timing logs, plus security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`). `RequestLoggingFilter` injects `request_id` into log records. Global exception handler in `main.py` prevents stack trace leaks.

**Authentication (Dual Auth)** — OAuth (Google/GitHub) via authlib. Supports two auth mechanisms:
- **Cookie auth** (same-origin / web): JWT stored as httpOnly cookie, set during OAuth callback
- **Bearer token auth** (cross-origin / mobile): JWT returned as `#token=` hash fragment in OAuth redirect (not query param — hash fragments are never sent to servers), stored in localStorage by frontend, sent as `Authorization: Bearer` header

`get_current_user()` in `dependencies.py` checks Bearer header first, falls back to cookie. All journey API endpoints require authentication; only `/health`, `/api/auth/me`, and `/api/shared/{token}` are public. Frontend auto-logout on 401.

**Database SSL** — `engine.py` auto-enables SSL for remote PostgreSQL hosts (Azure, Supabase). Local connections (localhost) skip SSL.

**Rate Limiting** — per-user sliding window rate limiter (`app/core/rate_limit.py`) protects expensive endpoints. Configurable via env vars.

**Toast Notifications** — `showToast(message, type)` from `@/components/ui/toast` for user feedback on copy, share, export, errors. `<ToastContainer />` rendered in App root. Auto-dismisses after 4 seconds.

## Code Style

### Python (Backend)
- Generic type hints: `list[str]`, `dict[str, Any]` (not `List`, `Dict`)
- Pydantic v2: `BaseModel` with `Field(...)`, `@field_validator`, `model_dump()`
- Enums as `class Pace(str, Enum)` for JSON serialization
- Google-style docstrings
- Async throughout: all I/O uses async/await with shared `httpx.AsyncClient`
- App version: `3.0.0`

### TypeScript (Frontend)
- Strict mode enabled (`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`)
- Functional components with hooks
- Path alias: `@/*` maps to `src/*`
- Tailwind CSS v4 with shadcn/ui + Radix UI components
- Zustand 5 for state management
- Design: Instrument Sans (body) + Plus Jakarta Sans (display), Indigo primary, Orange accent
- UX animations: staggered entry (`.animate-stagger-in .stagger-1..8`), scroll-reveal (IntersectionObserver + `.scroll-reveal`), wizard slide transitions (`.animate-slide-right/left`), shimmer image loaders (`.animate-shimmer`), confetti celebration, weather-driven day gradients
- Dark mode: intentional deep navy tones (`#0f1219` surface), not mechanical inversion
- Photo-first activity cards: hero banner layout with gradient overlay + thumbnail gallery
- Touch: swipe navigation between days (50px threshold)
- PWA: manifest.json for installability, theme-color meta tag

## API Endpoints

### Cities (`/api/cities`) — public catalog
- `GET /api/cities` — list available cities (with search/filter)
- `GET /api/cities/:id` — get city details
- `GET /api/cities/:id/variants` — list plan variants for a city
- `GET /api/cities/:id/variants/:vid` — get full variant with day plans

### Journeys (`/api/journeys`) — require authentication
- `POST /api/journeys` — assemble a journey from city plans
- `GET /api/journeys` — list saved journeys
- `GET /api/journeys/:id` — get full journey details
- `DELETE /api/journeys/:id` — delete a journey

### Jobs (`/api/jobs`)
- `GET /api/jobs/:id` — get job status/progress

### Admin (`/api/admin`) — require admin role
- `POST /api/admin/cities` — add a city to the catalog
- `POST /api/admin/cities/:id/generate` — trigger plan generation for a city
- `POST /api/admin/cities/:id/refresh` — refresh stale plans
- `GET /api/admin/stats` — generation stats (jobs, cities, variants)

### Sharing
- `POST /api/journeys/:id/share` — create shareable link
- `DELETE /api/journeys/:id/share` — revoke sharing
- `GET /api/shared/:token` — get shared journey (no auth)

### Auth (`/api/auth`)
- `GET /api/auth/login/{provider}` — initiate OAuth (google/github)
- `GET /api/auth/callback/{provider}` — OAuth callback
- `POST /api/auth/logout` — logout (clear cookie)
- `GET /api/auth/me` — get current user (public)

### Other
- `GET /api/places/search` — search places (Google Places)
- `GET /api/places/photo/{ref}?w=800` — proxy Google Places photos (SSRF-validated, configurable width 100-1600)
- `GET /health` — health check (status, version, LLM provider)

## Environment Variables

**Backend** (`backend/.env`): `LLM_PROVIDER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `GOOGLE_WEATHER_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `COOKIE_DOMAIN`, `APP_URL`, `BACKEND_URL`, `APP_ENV`, `DEBUG`, `CORS_ORIGINS`, `LOG_LEVEL`, `DATABASE_URL`, `RATE_LIMIT_PLAN_REQUESTS`, `RATE_LIMIT_PLAN_WINDOW_SECONDS`, `RATE_LIMIT_DAY_PLAN_REQUESTS`, `RATE_LIMIT_DAY_PLAN_WINDOW_SECONDS`, `RATE_LIMIT_CHAT_REQUESTS`, `RATE_LIMIT_CHAT_WINDOW_SECONDS`, `RATE_LIMIT_TIPS_REQUESTS`, `RATE_LIMIT_TIPS_WINDOW_SECONDS`

**Frontend** (`frontend/.env.local`): `VITE_GOOGLE_MAPS_API_KEY`

**Frontend production** (`frontend/.env.production`): `VITE_API_BASE_URL` (set for split deploy, leave empty for single-container), `VITE_GOOGLE_MAPS_API_KEY`

See `backend/.env.example` and `frontend/.env.example` for templates.

Note: `VITE_API_BASE_URL` should NOT be set in development — the Vite dev server proxies `/api` to `:8000` automatically, which is required for httpOnly cookie same-origin to work with OAuth.

## Deployment

Supports multiple deployment modes via dual auth (cookie + Bearer token):

| Mode | Auth | Config |
|------|------|--------|
| **Dev (Vite proxy)** | Cookie (same-origin) | No changes needed |
| **Single container** | Cookie (same-origin) | `docker build .` — Dockerfile runs backend only; pre-build frontend and place in `static/` |
| **Split deploy (same domain)** | Cookie (cross-subdomain) | Set `COOKIE_DOMAIN=.example.com` |
| **Split deploy (different domains)** | Bearer token | Set `VITE_API_BASE_URL`, `CORS_ORIGINS`, `APP_URL` |
| **Mobile app** | Bearer token | Use `Authorization: Bearer` header from OAuth `#token=` hash fragment redirect |

**Key settings:** `COOKIE_DOMAIN` (empty = same-origin only, `.example.com` = cross-subdomain), `APP_URL` (frontend URL for OAuth redirects), `BACKEND_URL` (backend URL for OAuth callbacks, empty = auto-detect), `CORS_ORIGINS` (allowed frontend origins).

**Dockerfile** (project root): Single-stage Python 3.11-slim build — runs backend only, serves pre-built frontend from `static/` when `static/index.html` exists. Runs Alembic migrations on startup. System deps included for weasyprint (pango, cairo, gdk-pixbuf).

## Environment Quirks

- **Python**: zsh aliases `python3` to system Python — always use `./venv/bin/python` for backend scripts (e.g. generating JWT tokens for curl testing)
- **npm permissions**: If `npm install` fails with EACCES, run `sudo chown -R $(whoami) ~/.npm`
- **Generate test JWT**: `./venv/bin/python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'test','email':'t@t.com','name':'Test'}))"` (run from `backend/`)
- **Pre-push hook**: Runs `npm run build` in frontend — takes ~1-2s, blocks push until build passes

## Testing with curl

```bash
# Generate JWT token (run from backend/)
TOKEN=$(./venv/bin/python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'test','email':'t@t.com','name':'Test'}))")

# Create a journey
curl -s http://localhost:8000/api/journeys \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"cities":["Tokyo","Kyoto"],"total_days":7,"start_date":"2026-05-01","pace":"moderate","budget":"moderate","travelers":{"adults":2}}' \
  | python3 -m json.tool

# Browse city catalog
curl -s http://localhost:8000/api/cities | python3 -m json.tool

# Get city variants
curl -s http://localhost:8000/api/cities/1/variants | python3 -m json.tool

# Test health
curl -s http://localhost:8000/health | python3 -m json.tool

# Test place search
curl -s "http://localhost:8000/api/places/search?query=restaurants+Tokyo" -H "Authorization: Bearer $TOKEN"
```
