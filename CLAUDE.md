# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Travel Companion AI (V2) -- a hybrid AI + deterministic travel planning app. LLMs handle creative decisions (place selection, theming, descriptions); deterministic layers handle calculations (distance, time, validation, scheduling).

Unified pipeline: multi-city journey planning with Scout -> Enrich -> Review -> Planner loop (~2-5min), iterating until quality threshold (min 70 score, max 3 iterations). Day plans are generated per-city with discover -> AI plan -> TSP optimize -> schedule -> route computation.

## Build & Run Commands

### Backend (FastAPI + Python)
```bash
cd backend
source venv/bin/activate          # Python virtual env
pip install -r requirements.txt   # Install deps
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

Test files: `backend/tests/test_api.py` (API endpoint tests with mocked dependencies). Fixtures in `conftest.py` provide `app` (FastAPI with overrides), `client` (httpx AsyncClient), in-memory SQLite, and MockLLMService.

## Architecture

### Code Flow
`routers/` -> `orchestrators/` -> `agents/` + `services/` + `algorithms/`

- **Routers** (`app/routers/`): FastAPI endpoints -- `trips.py` (journey plan, day plans, chat, CRUD), `places.py` (place search)
- **Orchestrators** (`app/orchestrators/`): Pipeline coordination
  - `journey.py` -- JourneyOrchestrator: Scout(LLM) -> Enrich(Google APIs) -> Review(LLM, score>=70?) -> Planner(LLM, fix issues) -> loop
  - `day_plan.py` -- DayPlanOrchestrator: discover -> AI plan -> TSP optimize -> schedule -> route computation per city
- **Agents** (`app/agents/`): LLM-powered components -- `scout.py`, `enricher.py`, `reviewer.py`, `planner.py`, `day_planner.py`
- **Services** (`app/services/`):
  - `llm/` -- Abstract `LLMService` base, `AzureOpenAILLMService`, `AnthropicLLMService`, `factory.py` for provider switching
  - `google/` -- `GooglePlacesService`, `GoogleRoutesService` (driving/walking), `GoogleDirectionsService` (transit/ferry)
  - `chat.py` -- ChatService for journey/day-plan editing via natural language
  - `tips.py` -- TipsService for activity tips generation
- **Algorithms** (`app/algorithms/`): Deterministic computation -- `tsp.py` (route optimizer), `scheduler.py` (time-slot builder), `quality/` (7-metric evaluator)
- **Models** (`app/models/`): Pydantic v2 models -- `common.py`, `journey.py`, `day_plan.py`, `trip.py`, `chat.py`, `progress.py`, `quality.py`, `internal.py`
- **Database** (`app/db/`): SQLAlchemy async + aiosqlite -- `engine.py`, `models.py` (SQLAlchemy models), `repository.py` (TripRepository)
- **Prompts** (`app/prompts/`): Markdown templates loaded via `PromptLoader` in `loader.py`
- **Config** (`app/config/`): Settings (Pydantic BaseSettings), planning configs (`planning.py`), regional transport guidance (`regional_transport.py`)
- **Core** (`app/core/`): Shared HTTP client (`http.py`), request tracing middleware (`middleware.py`)
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
llm = create_llm_service(settings)  # returns AzureOpenAI or Anthropic based on LLM_PROVIDER
data = await llm.generate_structured(system, user, schema=MyModel)
```

**Prompt Templates** -- centralized .md templates with category-based loaders:
```python
from app.prompts.loader import journey_prompts, day_plan_prompts
system = journey_prompts.load("scout_system")
user = day_plan_prompts.load("planning_user")
```

**SSE Streaming** -- endpoints yield `data: {json}\n\n` events via `ProgressEvent` model with phases: `scouting`, `enriching`, `reviewing`, `planning`, `complete`, `error`. Frontend consumes via async generator in `api.ts` with AbortController.

**Zustand Stores** -- frontend state management via two stores:
- `tripStore.ts` -- journey plan, day plans, saved trips CRUD
- `uiStore.ts` -- phase management (input -> planning -> preview -> day-plans), progress tracking, map/chat toggles

**Request Tracing** -- `RequestTracingMiddleware` adds `X-Request-ID` to every request/response with timing logs. `RequestLoggingFilter` injects `request_id` into log records.

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

All trip-related endpoints are under `/api/trips`:

- `POST /api/trips/plan/stream` -- stream journey planning (SSE)
- `POST /api/trips/{trip_id}/days/stream` -- stream day plan generation (SSE)
- `POST /api/trips/{trip_id}/chat` -- edit journey or day plans via chat
- `POST /api/trips/{trip_id}/tips` -- generate tips for activities
- `GET /api/trips` -- list saved trips
- `GET /api/trips/{trip_id}` -- get full trip details
- `DELETE /api/trips/{trip_id}` -- delete a trip
- `GET /api/places/search` -- search places (Google Places)
- `GET /health` -- health check (returns version 2.0.0)

## Environment Variables

**Backend** (`backend/.env`): `LLM_PROVIDER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `APP_ENV`, `DEBUG`, `CORS_ORIGINS`, `LOG_LEVEL`, `DATABASE_URL`

**Frontend** (`frontend/.env.local`): `VITE_API_BASE_URL` (defaults to `http://localhost:8000`), `VITE_GOOGLE_MAPS_API_KEY`

See `backend/.env.example` and `frontend/.env.example` for templates.
