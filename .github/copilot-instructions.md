# Regular Everyday Traveller - AI Agent Guidelines

## Architecture

Hybrid AI + deterministic approach: LLMs (Azure OpenAI, Anthropic, or Gemini) handle creative decisions (place selection, theming, descriptions, cost estimation); deterministic layers handle calculations (distance, time, validation, scheduling, quality scoring).

**Unified pipeline:** Multi-city journey planning with Landscape Discovery (Google) + Must-See Icons (LLM, parallel) -> Scout -> Enrich -> Review -> Planner loop (max 3 iterations, score ≥75, returns best attempt). Quality loop acceptance is decoupled: LLM reviewer's `is_acceptable` reflects only critical/feasibility issues (no score threshold in prompts); score threshold enforced purely in orchestrator code. Day plans generated per-city in background with quality pipeline: theme pre-mapping -> Day Scout -> Day Reviewer -> Day Fixer loop (max 2 iterations) -> TSP optimize -> schedule (culture-aware meal placement) -> pace-aware transport mode selection -> route computation -> weather integration. All free days in a city processed in a single Scout → Reviewer → Fixer pass (no intra-city batching).

**Service flow**: `routers/` -> `orchestrators/` -> `agents/` + `services/` + `algorithms/`

**Key directories:**
- `app/config/` - Settings (`settings.py` for env vars), planning constants (`planning.py` — pace configs, fallback durations, `MAX_CONCURRENT_CITIES`, `ROUTE_COMPUTATION_MODE`, score thresholds), regional transport (`regional_transport.py` — LLM-driven prompt guidance)
- `app/prompts/` - 16 centralized .md templates loaded via `PromptLoader` (journey, day_plan, chat, tips)
- `app/core/` - JWT auth (`auth.py`), shared HTTP client with retry/exponential backoff (`http.py`), request tracing middleware with security headers (`middleware.py`), per-user sliding window rate limiting (`rate_limit.py`)
- `app/services/llm/` - Abstract LLM base + Azure OpenAI (o1/o3/gpt-5 support), Anthropic (tool_use), Gemini (json_schema). All providers strip null characters from output
- `app/services/google/` - Places, Routes, Directions, Weather services
- `app/services/` - `chat.py` (ChatService), `tips.py` (TipsService), `export.py` (PDF trip book via weasyprint + .ics calendar)
- `app/agents/` - Journey: Scout, Enricher, Reviewer, Planner. Day plan: DayScout, DayReviewer, DayFixer, DayPlanner (legacy fallback)
- `app/orchestrators/` - Journey and DayPlan orchestrators
- `app/db/` - SQLAlchemy 2.0 async + asyncpg (PostgreSQL), auto-SSL for remote hosts. Alembic migrations
- `app/algorithms/` - TSP solver, scheduler (culture-aware meal placement, ~80 countries/10 regional profiles), quality scoring (7 weighted metrics)
- `app/dependencies.py` - FastAPI Depends() wiring for all services, auth, DB

**Config separation:**
- `settings.py` (env vars): external dependencies only (API keys, URLs, secrets, database, OAuth, rate limits)
- `planning.py` (constants): internal product decisions (`MAX_CONCURRENT_CITIES`, `ROUTE_COMPUTATION_MODE`, score thresholds, pace configs)

## Code Style

### Python
- **Types**: Generic hints (`list[str]`, `dict[str, Any]` — not `List`, `Dict`)
- **Docstrings**: Google-style with Args/Returns
- **Async**: All LLM/API calls `async` with `httpx.AsyncClient`
- **Enums**: `class Pace(str, Enum)` for JSON serialization
- **Pydantic v2**: `BaseModel` with `Field(...)`, `@field_validator`, `model_dump()`
- **App version**: `2.0.0`

### Pydantic Models (`app/models/`)
```python
class TripRequest(BaseModel):
    destination: str = Field(..., min_length=2, max_length=200)
    total_days: int = Field(..., ge=1, le=21)
    start_date: date
    pace: Pace = Pace.MODERATE
    budget: Budget | None = None
    travelers: Travelers | None = None
```

### TypeScript
- Strict mode (`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`)
- Functional components with hooks
- Zustand 5 for state management (`tripStore`, `uiStore`, `authStore`)
- shadcn/ui + Radix UI components with Tailwind CSS v4
- Path alias: `@/*` maps to `src/*`
- @dnd-kit for drag-and-drop activity reordering
- Design: Inter (body) + Plus Jakarta Sans (display), Indigo primary, Orange accent
- PWA: manifest.json for installability, theme-color meta tag

## Build and Test

```bash
# Backend
cd backend && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head             # Run database migrations
uvicorn app.main:app --reload --port 8000
pytest -v                        # Run all 223 tests (requires Docker)
pytest -k "test_health"          # Run specific tests

# Frontend
cd frontend && npm install
npm run dev              # Vite dev server (port 5173), proxies /api to :8000
npm run build && npm run lint
```

## Key Patterns

### Dependency Injection (`app/dependencies.py`)
```python
from app.dependencies import get_journey_orchestrator

@router.post("/plan/stream")
async def plan(
    request: TripRequest,
    orchestrator: JourneyOrchestrator = Depends(get_journey_orchestrator),
    user: dict = Depends(require_user),
):
```

### Prompt Templates (`app/prompts/loader.py`)
```python
from app.prompts.loader import journey_prompts, day_plan_prompts
system = journey_prompts.load("scout_system")
user = day_plan_prompts.load("planning_user")
```

### LLM Service (`app/services/llm/`)
```python
from app.services.llm.factory import create_llm_service
llm = create_llm_service(settings)  # Azure OpenAI, Anthropic, or Gemini
data = await llm.generate_structured(system, user, schema=MyModel)
```

Each provider implements structured output differently:
- Azure OpenAI: `response_format={"type": "json_object"}`, special handling for reasoning models (o1/o3/gpt-5: uses `max_completion_tokens`, omits temperature)
- Anthropic: tool_use pattern with `tool_choice={"type": "tool", "name": "submit"}`
- Gemini: `response_mime_type` + `response_json_schema` from Pydantic model

### SSE Streaming
Events use `ProgressEvent` model: `scouting`, `enriching`, `reviewing`, `planning`, `improving`, `complete`, `error`.
```python
yield f"data: {event.model_dump_json()}\n\n"
```

### Authentication (Dual Auth)
OAuth (Google/GitHub) via authlib. Cookie auth (same-origin) + Bearer token auth (cross-origin/mobile). `get_current_user()` checks Bearer header first, falls back to cookie.
```python
from app.dependencies import require_user, get_current_user
# require_user raises 401; get_current_user returns None if unauthenticated
```

### Configuration
```python
from app.config import get_settings  # lru_cached singleton
settings = get_settings()
```

### Tiered Route Computation
`ROUTE_COMPUTATION_MODE` in `planning.py`: `full` (distance matrix + compute_route, ~$2.40/trip), `efficient` (haversine mode selection + compute_route, ~$1.20/trip), `minimal` (haversine everything, $0/trip, no polylines). Only affects day plan activity-to-activity routing; journey city-to-city routing (GoogleDirectionsService) is unaffected.

## Design Principles

- Prefer LLM prompt updates and Google API grounding over hardcoded heuristics
- Deterministic layers serve as context-aware guardrails with generous defaults — accept overrides from LLM responses and API data via context dicts
- Duration estimation priority: 1) LLM estimate, 2) Google Places `suggested_duration_minutes`, 3) fallback table
- Must-see iconic attractions identified via parallel LLM call, injected into Reviewer/Planner as ground truth
- City processing parallelized via `asyncio.Queue` + `asyncio.Semaphore` (bounded by `MAX_CONCURRENT_CITIES`, default 5)
- Cross-day duplicate prevention passes full `already_used` set to both Day Scout and Day Fixer
- Excursion days render full activity timeline with excursion banner — no simplified stub card
- Lodging types (`LODGING_TYPES`) filtered from activity candidates at both discovery and scout levels

## Environment Variables

Backend (`.env`): `LLM_PROVIDER`, `AZURE_OPENAI_*`, `ANTHROPIC_*`, `GEMINI_*`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `GOOGLE_WEATHER_API_KEY`, `GOOGLE_OAUTH_*`, `GITHUB_OAUTH_*`, `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `COOKIE_DOMAIN`, `APP_URL`, `BACKEND_URL`, `APP_ENV`, `DEBUG`, `LOG_LEVEL`, `CORS_ORIGINS`, `DATABASE_URL`, `RATE_LIMIT_*`

Frontend (`.env.local`): `VITE_GOOGLE_MAPS_API_KEY` (do NOT set `VITE_API_BASE_URL` in dev — Vite proxy handles it)

Frontend production (`.env.production`): `VITE_API_BASE_URL` (backend URL for split deploy), `VITE_GOOGLE_MAPS_API_KEY`

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/trips/plan/stream` | Stream journey planning (SSE) |
| POST | `/api/trips/{id}/days/stream` | Stream day plan generation (SSE) |
| POST | `/api/trips/{id}/chat` | Chat-based editing |
| POST | `/api/trips/{id}/tips` | Generate activity tips |
| PUT | `/api/trips/{id}/quick-edit` | Quick activity edits (remove, ±duration) |
| PUT | `/api/trips/{id}/reorder` | Reorder activities within a day |
| GET | `/api/trips` | List saved trips (pagination: `limit`/`offset`) |
| GET | `/api/trips/{id}` | Get trip details |
| DELETE | `/api/trips/{id}` | Delete trip |
| POST | `/api/trips/{id}/share` | Create shareable link |
| DELETE | `/api/trips/{id}/share` | Revoke sharing |
| GET | `/api/trips/{id}/export/pdf` | Download PDF trip book |
| GET | `/api/trips/{id}/export/calendar` | Download .ics calendar |
| GET | `/api/auth/login/{provider}` | Initiate OAuth (google/github) |
| GET | `/api/auth/callback/{provider}` | OAuth callback |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user (public) |
| GET | `/api/places/search` | Search places |
| GET | `/api/places/photo/{ref}` | Proxy Google Places photos |
| GET | `/api/places/alternatives` | Get alternative hotels |
| GET | `/api/shared/{token}` | Get shared trip (public) |
| GET | `/health` | Health check |

All `/api/trips` endpoints require authentication. Public: `/health`, `/api/auth/me`, `/api/shared/{token}`.

## Integration Points

| Service | Purpose | Client |
|---------|---------|--------|
| Azure OpenAI / Anthropic / Gemini | LLM (switchable via `LLM_PROVIDER`) | `app/services/llm/` |
| Google Places | Place discovery, geocoding, lodging | `app/services/google/places.py` |
| Google Routes | Driving/walking times, distance matrices | `app/services/google/routes.py` |
| Google Directions | Transit & ferry routes, fares | `app/services/google/directions.py` |
| Google Weather | Daily forecasts | `app/services/google/weather.py` |

Frontend SSE consumption: `src/services/api.ts` (async generator pattern with AbortController, 180s stall timeout)
