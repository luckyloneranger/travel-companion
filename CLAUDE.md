# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Travel Companion AI (V2) -- a hybrid AI + deterministic travel planning app. LLMs handle creative decisions (place selection, theming, descriptions, cost estimation for groups); deterministic layers handle calculations (distance, time, validation, scheduling).

Unified pipeline: multi-city journey planning with Scout -> Enrich -> Review -> Planner loop (~2-5min), iterating until quality threshold (min 70 score, max 3 iterations, returns best attempt). Day plans are generated in background per-city with discover -> AI plan -> TSP optimize -> schedule -> route computation. All trip endpoints require authentication.

## Build & Run Commands

### Backend (FastAPI + Python)
```bash
docker compose up -d db            # Start PostgreSQL (first time)
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

Test files: `backend/tests/test_api.py` (API endpoint tests), `test_tsp.py` (TSP optimizer), `test_scheduler.py` (schedule builder), `test_quality.py` (quality evaluators), `test_agents.py` (Scout/Reviewer agents), `test_services.py` (TipsService/ChatService/Routes helpers), `test_validation.py` (request validation edge cases), `test_integration.py` (API lifecycle), `test_weather.py` (weather service/parsing/warnings). Fixtures in `conftest.py` provide `app` (FastAPI with overrides), `client` (httpx AsyncClient), testcontainers PostgreSQL, and MockLLMService. Tests require Docker running.

## Architecture

### Code Flow
`routers/` -> `orchestrators/` -> `agents/` + `services/` + `algorithms/`

- **Routers** (`app/routers/`): FastAPI endpoints -- `trips.py` (journey plan, day plans, chat, sharing, CRUD), `places.py` (place search), `auth.py` (OAuth login/callback/logout), `export.py` (PDF/calendar export)
- **Orchestrators** (`app/orchestrators/`): Pipeline coordination
  - `journey.py` -- JourneyOrchestrator: Scout(LLM) -> Enrich(Google APIs) -> Review(LLM, score>=70?) -> Planner(LLM, fix issues) -> loop (tracks best plan across iterations)
  - `day_plan.py` -- DayPlanOrchestrator: discover -> AI plan (with time constraints for arrival/departure days) -> TSP optimize -> schedule -> auto-select transport mode -> weather integration per city
- **Agents** (`app/agents/`): LLM-powered components -- `scout.py`, `enricher.py`, `reviewer.py`, `planner.py`, `day_planner.py`
- **Services** (`app/services/`):
  - `llm/` -- Abstract `LLMService` base, `AzureOpenAILLMService`, `AnthropicLLMService`, `GeminiLLMService`, `factory.py` for provider switching
  - `google/` -- `GooglePlacesService`, `GoogleRoutesService`, `GoogleDirectionsService` (transit/ferry), `GoogleWeatherService` (daily forecasts)
  - `chat.py` -- ChatService for journey/day-plan editing via natural language
  - `tips.py` -- TipsService for activity tips generation
  - `export.py` -- PDF (weasyprint) and calendar (.ics) export
- **Algorithms** (`app/algorithms/`): Deterministic computation -- `tsp.py` (route optimizer), `scheduler.py` (time-slot builder), `quality/` (7-metric evaluator)
- **Models** (`app/models/`): Pydantic v2 models -- `common.py`, `journey.py`, `day_plan.py`, `trip.py` (TripRequest with Travelers model), `chat.py`, `progress.py`, `quality.py`, `internal.py`
- **Database** (`app/db/`): SQLAlchemy async + asyncpg (PostgreSQL) -- `engine.py`, `models.py` (SQLAlchemy models), `repository.py` (TripRepository). Alembic for schema migrations (`backend/alembic/`)
- **Prompts** (`app/prompts/`): Markdown templates loaded via `PromptLoader` in `loader.py` (14 templates across journey, day_plan, chat, tips categories)
- **Config** (`app/config/`): Settings (Pydantic BaseSettings), planning configs (`planning.py`), regional transport guidance (`regional_transport.py`)
- **Core** (`app/core/`): Shared HTTP client with retry logic (`http.py`), request tracing middleware (`middleware.py`)
- **Dependencies** (`app/dependencies.py`): FastAPI `Depends()` wiring for all services and orchestrators

### Key Patterns

**Dependency Injection** -- all services and orchestrators are wired via FastAPI `Depends()` in `app/dependencies.py`:
```python
from app.dependencies import get_journey_orchestrator, get_trip_repository

@router.post("/plan/stream")
async def plan_trip_stream(
    request: TripRequest,
    orchestrator: JourneyOrchestrator = Depends(get_journey_orchestrator),
    repo: TripRepository = Depends(get_trip_repository),
):
```

**LLM Abstraction** -- provider-agnostic via abstract base class + factory:
```python
from app.services.llm.factory import create_llm_service
llm = create_llm_service(settings)  # returns AzureOpenAI, Anthropic, or Gemini based on LLM_PROVIDER
data = await llm.generate_structured(system, user, schema=MyModel)
```

**Prompt Templates** -- centralized .md templates with category-based loaders:
```python
from app.prompts.loader import journey_prompts, day_plan_prompts
system = journey_prompts.load("scout_system")
user = day_plan_prompts.load("planning_user")
```

**SSE Streaming** -- endpoints yield `data: {json}\n\n` events via `ProgressEvent` model with phases: `scouting`, `enriching`, `reviewing`, `planning`, `complete`, `error`. Day plan generation runs in background (no phase switch). Frontend consumes via async generator in `api.ts` with AbortController. Stall timeout (180s) warns users on slow connections.

**Zustand Stores** -- frontend state management via three stores:
- `tripStore.ts` -- journey plan, day plans, travelers (adults/children/infants), saved trips CRUD, cost breakdown (includes accommodation + transport + dining + activities, costs are total-for-group)
- `uiStore.ts` -- phase management (input -> planning -> preview), wizard step tracking, day plans generating state, progress tracking, chat toggles, browser history integration
- `authStore.ts` -- user authentication state, periodic token refresh

**Request Tracing** -- `RequestTracingMiddleware` adds `X-Request-ID` to every request/response with timing logs. `RequestLoggingFilter` injects `request_id` into log records.

**Authentication (Dual Auth)** -- OAuth (Google/GitHub) via authlib. Supports two auth mechanisms:
- **Cookie auth** (same-origin / web): JWT stored as httpOnly cookie, set during OAuth callback
- **Bearer token auth** (cross-origin / mobile): JWT returned as `?token=` query param in OAuth redirect, stored in localStorage by frontend, sent as `Authorization: Bearer` header

`get_current_user()` in `dependencies.py` checks Bearer header first, falls back to cookie. All trip API endpoints require authentication; only `/health`, `/api/auth/me`, and `/api/shared/{token}` are public. Frontend auto-logout on 401.

**Design Principles** -- Prefer LLM prompt updates and Google API grounding over hardcoded heuristics. Cost estimates, geographic diversity, destination validity, and activity planning are all LLM-driven via prompt guidance rather than deterministic rules.

## Code Style

### Python (Backend)
- Generic type hints: `list[str]`, `dict[str, Any]` (not `List`, `Dict`)
- Pydantic v2: `BaseModel` with `Field(...)`, `@field_validator`, `model_dump()`
- Enums as `class Pace(str, Enum)` for JSON serialization
- Google-style docstrings
- Async throughout: all I/O uses async/await with shared `httpx.AsyncClient`

### TypeScript (Frontend)
- Strict mode enabled
- Functional components with hooks
- Path alias: `@/*` maps to `src/*`
- Tailwind CSS v4 with shadcn/ui components
- Zustand for state management

## API Endpoints

### Trips (`/api/trips`)
- `POST /api/trips/plan/stream` -- stream journey planning (SSE)
- `POST /api/trips/{trip_id}/days/stream` -- stream day plan generation (SSE)
- `POST /api/trips/{trip_id}/chat` -- edit journey or day plans via chat
- `POST /api/trips/{trip_id}/tips` -- generate tips for activities
- `GET /api/trips` -- list saved trips
- `GET /api/trips/{trip_id}` -- get full trip details
- `DELETE /api/trips/{trip_id}` -- delete a trip
- `POST /api/trips/{trip_id}/share` -- create shareable link
- `DELETE /api/trips/{trip_id}/share` -- revoke sharing
- `GET /api/trips/{trip_id}/export/pdf` -- download PDF
- `GET /api/trips/{trip_id}/export/calendar` -- download .ics

### Auth (`/api/auth`)
- `GET /api/auth/login/{provider}` -- initiate OAuth (google/github)
- `GET /api/auth/callback/{provider}` -- OAuth callback
- `POST /api/auth/logout` -- logout (clear cookie)
- `GET /api/auth/me` -- get current user

### Other
- `GET /api/places/search` -- search places (Google Places)
- `GET /api/shared/{token}` -- get shared trip (no auth)
- `GET /health` -- health check (status, version, LLM provider)

## Environment Variables

**Backend** (`backend/.env`): `LLM_PROVIDER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `GOOGLE_WEATHER_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `JWT_SECRET_KEY`, `COOKIE_DOMAIN`, `APP_ENV`, `DEBUG`, `CORS_ORIGINS`, `LOG_LEVEL`, `DATABASE_URL`

**Frontend** (`frontend/.env.local`): `VITE_GOOGLE_MAPS_API_KEY`

**Frontend production** (`frontend/.env.production`): `VITE_API_BASE_URL` (set for split deploy, leave empty for single-container), `VITE_GOOGLE_MAPS_API_KEY`

See `backend/.env.example` and `frontend/.env.example` for templates.

Note: `VITE_API_BASE_URL` should NOT be set in development — the Vite dev server proxies `/api` to `:8000` automatically, which is required for httpOnly cookie same-origin to work with OAuth.

## Deployment

Supports multiple deployment modes via dual auth (cookie + Bearer token):

| Mode | Auth | Config |
|------|------|--------|
| **Dev (Vite proxy)** | Cookie (same-origin) | No changes needed |
| **Single container** | Cookie (same-origin) | `docker build .` — Dockerfile builds frontend + backend into one image, serves frontend from `static/` |
| **Split deploy (same domain)** | Cookie (cross-subdomain) | Set `COOKIE_DOMAIN=.example.com` |
| **Split deploy (different domains)** | Bearer token | Set `VITE_API_BASE_URL=https://api.example.com`, `CORS_ORIGINS=https://app.example.com` |
| **Mobile app** | Bearer token | Use `Authorization: Bearer` header from OAuth `?token=` redirect |

**Key settings:** `COOKIE_DOMAIN` (empty = same-origin only, `.example.com` = cross-subdomain), `APP_URL` (frontend URL for OAuth redirects), `CORS_ORIGINS` (allowed frontend origins).

**Dockerfile** (project root): Multi-stage build — Stage 1: Node 18 builds frontend, Stage 2: Python 3.11-slim runs backend + serves built frontend from `static/`. Backend auto-mounts `static/` as SPA when `static/index.html` exists.
