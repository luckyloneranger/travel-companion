# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Regular Everyday Traveller (RET) — a hybrid AI + deterministic travel planning app. LLMs handle creative decisions (place selection, theming, descriptions, cost estimation for groups); deterministic layers handle calculations (distance, time, validation, scheduling, quality scoring).

Unified pipeline: multi-city journey planning with Scout -> Enrich -> Review -> Planner loop (~2-5min), iterating until quality threshold (min 70 score, max 3 iterations, returns best attempt). Day plans are generated in background per-city with discover -> AI plan -> TSP optimize -> schedule -> auto-select transport mode -> route computation -> weather integration. All trip endpoints require authentication.

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

### Tests (Backend only, 199 tests)
```bash
cd backend
source venv/bin/activate
pytest                    # All tests
pytest -v                 # Verbose
pytest -k "test_health"   # Run specific tests
pytest --cov              # With coverage
```

Test files: `test_api.py` (API endpoints), `test_agents.py` (Scout/Reviewer agents), `test_tsp.py` (TSP optimizer), `test_scheduler.py` (schedule builder), `test_quality.py` (quality evaluators, 7 metrics), `test_services.py` (TipsService/ChatService/Routes helpers), `test_validation.py` (request validation), `test_integration.py` (API lifecycle), `test_weather.py` (weather service/parsing/warnings), `test_auth.py` (OAuth/JWT/dual auth), `test_budget.py` (cost breakdown/group pricing), `test_export.py` (PDF/calendar export), `test_sharing.py` (shareable links). Fixtures in `conftest.py` provide `app` (FastAPI with overrides), `client` (httpx AsyncClient), testcontainers PostgreSQL, and MockLLMService. Tests require Docker running.

## Architecture

### Code Flow
`routers/` -> `orchestrators/` -> `agents/` + `services/` + `algorithms/`

- **Routers** (`app/routers/`): FastAPI endpoints — `trips.py` (journey plan, day plans, chat, tips, sharing, quick-edit, reorder, CRUD), `places.py` (place search, photo proxy, hotel alternatives), `auth.py` (OAuth login/callback/logout), `export.py` (PDF trip book/calendar export)
- **Orchestrators** (`app/orchestrators/`): Pipeline coordination
  - `journey.py` — JourneyOrchestrator: Scout(LLM) -> Enrich(Google APIs) -> Review(LLM, score>=70?) -> Planner(LLM, fix issues) -> loop (tracks best plan across iterations, max 3)
  - `day_plan.py` — DayPlanOrchestrator: discover -> AI plan (with time constraints for arrival/departure days, regional meal guidance) -> TSP optimize -> schedule (culture-aware meal placement) -> pace-aware transport mode selection -> route computation -> graduated weather warnings per city
- **Agents** (`app/agents/`): LLM-powered components — `scout.py` (city selection + accommodation + travel legs, validates accommodation per city with placeholder fallback), `enricher.py` (Google API grounding, transit cap 4x driving, fallback geocoding with "{city}, {country}"), `reviewer.py` (quality scoring 0-100, score coercion for string/float), `planner.py` (fix review issues), `day_planner.py` (activity selection + day theming + regional meal guidance, logs orphan IDs and missing durations/costs)
- **Services** (`app/services/`):
  - `llm/` — Abstract `LLMService` base, `AzureOpenAILLMService` (supports reasoning models: o1, o3, gpt-5, with exponential backoff retry for transient errors), `AnthropicLLMService` (tool_use for structured output), `GeminiLLMService` (response_json_schema), `factory.py` for provider switching. All providers strip null characters from output.
  - `google/` — `GooglePlacesService` (discovery, geocoding, lodging), `GoogleRoutesService` (single/batch routes, distance matrices), `GoogleDirectionsService` (transit details, fares, transfers), `GoogleWeatherService` (daily forecasts)
  - `chat.py` — ChatService for journey/day-plan editing via natural language
  - `tips.py` — TipsService for activity tips generation
  - `export.py` — PDF trip book (weasyprint with cover page, daily spreads, weather) and calendar (.ics) export
- **Algorithms** (`app/algorithms/`): Deterministic computation — `tsp.py` (nearest-neighbor route optimizer), `scheduler.py` (time-slot builder with culture-aware meal placement across ~80 countries/10 regional profiles, pace multipliers, LLM meal window overrides via `from_context()`), `quality/` (7 context-aware evaluators: meal timing 20%, clustering 15% with auto city-scale detection, efficiency 15%, variety 15%, opening hours 15%, theme 10%, duration 10%)
- **Models** (`app/models/`): Pydantic v2 models — `common.py` (Location, Pace, TravelMode, TransportMode, Budget enums), `journey.py` (JourneyPlan, CityStop, TravelLeg, Accommodation, ReviewResult), `day_plan.py` (DayPlan, Activity, Place, Route, Weather), `trip.py` (TripRequest, TripResponse, TripSummary, Travelers), `chat.py`, `progress.py`, `quality.py`, `internal.py`, `user.py`
- **Database** (`app/db/`): SQLAlchemy 2.0 async + asyncpg (PostgreSQL) — `engine.py` (auto-SSL for remote hosts), `models.py` (Trip, User, TripShare tables), `repository.py` (TripRepository with CRUD + sharing). Alembic for schema migrations (`backend/alembic/`)
- **Prompts** (`app/prompts/`): 14 Markdown templates loaded via `PromptLoader` in `loader.py` — journey (scout_system/user, reviewer_system/user, planner_system/user), day_plan (planning_system/user), chat (journey_edit_system/user, day_plan_edit_system/user), tips (tips_system/user)
- **Config** (`app/config/`): Settings (Pydantic BaseSettings), planning configs (`planning.py` — pace configs, fallback duration-by-type table, interest-to-place-type seed mapping, adaptive place filters, haversine fallback computation), regional transport guidance (`regional_transport.py` — LLM-driven prompt guidance instead of hardcoded profiles)
- **Core** (`app/core/`): JWT auth (`auth.py`), shared HTTP client with retry/exponential backoff (`http.py`), request tracing middleware with security headers (`middleware.py` — X-Request-ID, X-Content-Type-Options, X-Frame-Options, Referrer-Policy), global exception handler (`main.py`), per-user sliding window rate limiting (`rate_limit.py` — plan, day_plan, chat, tips endpoints)
- **Dependencies** (`app/dependencies.py`): FastAPI `Depends()` wiring for all services, orchestrators, auth, and DB sessions

### Key Patterns

**Dependency Injection** — all services and orchestrators are wired via FastAPI `Depends()` in `app/dependencies.py`:
```python
from app.dependencies import get_journey_orchestrator, get_trip_repository

@router.post("/plan/stream")
async def plan_trip_stream(
    request: TripRequest,
    orchestrator: JourneyOrchestrator = Depends(get_journey_orchestrator),
    repo: TripRepository = Depends(get_trip_repository),
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
from app.prompts.loader import journey_prompts, day_plan_prompts
system = journey_prompts.load("scout_system")
user = day_plan_prompts.load("planning_user")
```

**SSE Streaming** — endpoints yield `data: {json}\n\n` events via `ProgressEvent` model with phases: `scouting`, `enriching`, `reviewing`, `planning`, `improving`, `complete`, `error`. Day plan generation runs in background (no phase switch). Frontend consumes via async generator in `api.ts` with AbortController. Stall timeout (180s) warns users on slow connections.

**Zustand Stores** — frontend state management via three stores:
- `tripStore.ts` — journey plan, day plans, travelers (adults/children/infants), saved trips CRUD, cost breakdown (accommodation + transport + dining + activities, costs are total-for-group), tips cache, recent changes tracking (visual diff after chat edits)
- `uiStore.ts` — phase management (input -> planning -> preview -> day-plans -> live), wizard step tracking, day plans generating state, progress tracking, chat toggles with prefill support, browser history integration, per-day map visibility
- `authStore.ts` — user authentication state, JWT capture from OAuth redirect hash fragment (`#token=`), periodic token refresh (30 min), auto-logout on 401

**Request Tracing** — `RequestTracingMiddleware` adds `X-Request-ID` to every request/response with timing logs, plus security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`). `RequestLoggingFilter` injects `request_id` into log records. Global exception handler in `main.py` prevents stack trace leaks.

**Authentication (Dual Auth)** — OAuth (Google/GitHub) via authlib. Supports two auth mechanisms:
- **Cookie auth** (same-origin / web): JWT stored as httpOnly cookie, set during OAuth callback
- **Bearer token auth** (cross-origin / mobile): JWT returned as `#token=` hash fragment in OAuth redirect (not query param — hash fragments are never sent to servers), stored in localStorage by frontend, sent as `Authorization: Bearer` header

`get_current_user()` in `dependencies.py` checks Bearer header first, falls back to cookie. All trip API endpoints require authentication; only `/health`, `/api/auth/me`, and `/api/shared/{token}` are public. Frontend auto-logout on 401.

**Database SSL** — `engine.py` auto-enables SSL for remote PostgreSQL hosts (Azure, Supabase). Local connections (localhost) skip SSL.

**Rate Limiting** — per-user sliding window rate limiter (`app/core/rate_limit.py`) protects expensive endpoints. Configurable via `RATE_LIMIT_{PLAN,DAY_PLAN,CHAT,TIPS}_{REQUESTS,WINDOW_SECONDS}` env vars (defaults: plan 5/10min, day_plan 10/10min, chat 30/10min, tips 30/10min). Trip list supports pagination via `limit`/`offset` query params (default 50, max 200).

**Routing & Navigation** — Frontend uses React Router with phase-based rendering (`input` → `planning` → `preview` → `day-plans` → `live`). Active tab persisted in URL via `?tab=cities` for deep-linking. TripLoader guards against loading when `phase='input'` to prevent race conditions. Logo click preserves trip data (just navigates home), "New Trip" requires confirmation then resets via `setTimeout(0)` to avoid TripLoader reload race. API catch-all at `/api/{path}` returns JSON 404 instead of SPA fallback. OAuth token delivered via hash fragment (`#token=`). CORS restricted to explicit methods/headers. ErrorBoundary wraps trip routes.

**Toast Notifications** — `showToast(message, type)` from `@/components/ui/toast` for user feedback on copy, share, export, errors. `<ToastContainer />` rendered in App root. Auto-dismisses after 4 seconds.

**Design Principles** — Prefer LLM prompt updates and Google API grounding over hardcoded heuristics. Deterministic layers (scheduler, quality evaluators, route selection) serve as context-aware guardrails with generous defaults — they accept overrides from LLM responses and API data via context dicts. Duration estimation priority: 1) LLM estimate, 2) Google Places `suggested_duration_minutes`, 3) fallback table. Meal windows adapt to ~80 countries via 10 regional profiles and accept LLM overrides via `ScheduleConfig.from_context()`. Place quality filters adapt to result density via `get_adaptive_place_filters()`. Walk/drive selection is pace-aware (relaxed=25min walk threshold, packed=15min). Prompt templates use `{meal_time_guidance}` placeholder for regional context injection rather than hardcoded meal times. Dining classification uses substring matching to catch all regional types (e.g. `sushi_restaurant`, `bar_and_grill`).

## Code Style

### Python (Backend)
- Generic type hints: `list[str]`, `dict[str, Any]` (not `List`, `Dict`)
- Pydantic v2: `BaseModel` with `Field(...)`, `@field_validator`, `model_dump()`
- Enums as `class Pace(str, Enum)` for JSON serialization
- Google-style docstrings
- Async throughout: all I/O uses async/await with shared `httpx.AsyncClient`
- App version: `2.0.0`

### TypeScript (Frontend)
- Strict mode enabled (`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`)
- Functional components with hooks
- Path alias: `@/*` maps to `src/*`
- Tailwind CSS v4 with shadcn/ui + Radix UI components
- Zustand 5 for state management
- @dnd-kit for drag-and-drop activity reordering
- Design: Inter (body) + Plus Jakarta Sans (display), Indigo primary, Orange accent
- PWA: manifest.json for installability, theme-color meta tag

## API Endpoints

### Trips (`/api/trips`) — all require authentication
- `POST /api/trips/plan/stream` — stream journey planning (SSE)
- `POST /api/trips/{trip_id}/days/stream` — stream day plan generation (SSE)
- `POST /api/trips/{trip_id}/chat` — edit journey or day plans via chat
- `POST /api/trips/{trip_id}/tips` — generate tips for activities
- `PUT /api/trips/{trip_id}/quick-edit` — quick activity edits (remove, ±duration)
- `PUT /api/trips/{trip_id}/reorder` — reorder activities within a day
- `GET /api/trips` — list saved trips
- `GET /api/trips/{trip_id}` — get full trip details
- `DELETE /api/trips/{trip_id}` — delete a trip
- `POST /api/trips/{trip_id}/share` — create shareable link
- `DELETE /api/trips/{trip_id}/share` — revoke sharing
- `GET /api/trips/{trip_id}/export/pdf` — download PDF trip book
- `GET /api/trips/{trip_id}/export/calendar` — download .ics

### Auth (`/api/auth`)
- `GET /api/auth/login/{provider}` — initiate OAuth (google/github)
- `GET /api/auth/callback/{provider}` — OAuth callback
- `POST /api/auth/logout` — logout (clear cookie)
- `GET /api/auth/me` — get current user (public)

### Other
- `GET /api/places/search` — search places (Google Places)
- `GET /api/places/photo/{ref}?w=800` — proxy Google Places photos (SSRF-validated, configurable width 100-1600)
- `GET /api/places/alternatives` — get alternative hotels near a location
- `GET /api/shared/{token}` — get shared trip (no auth)
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
- **TravelMode enum**: API accepts uppercase only (`WALK`, `DRIVE`, `TRANSIT`) — not lowercase transport modes like `train`, `bus`

## Testing with curl

```bash
# Generate JWT token (run from backend/)
TOKEN=$(./venv/bin/python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'test','email':'t@t.com','name':'Test'}))")

# Test SSE stream — save output, parse last event
curl -s --max-time 240 http://localhost:8000/api/trips/plan/stream \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"destination":"Spain","origin":"Madrid","total_days":5,"start_date":"2026-04-15","interests":["food"],"pace":"relaxed","travel_mode":"TRANSIT","budget":"moderate","travelers":{"adults":2}}' \
  > /tmp/sse.txt && grep "^data:" /tmp/sse.txt | tail -1 | sed 's/^data: //' | python3 -m json.tool

# Test health
curl -s http://localhost:8000/health | python3 -m json.tool

# Test place search
curl -s "http://localhost:8000/api/places/search?query=restaurants+Tokyo" -H "Authorization: Bearer $TOKEN"
```
