# Regular Everyday Traveller - AI Agent Guidelines

## Architecture

Hybrid AI + deterministic approach: LLMs (Azure OpenAI, Anthropic, or Gemini) handle creative decisions, Google APIs provide real-time data.

**Unified pipeline:** Multi-city journey planning with Scout -> Enrich -> Review -> Planner loop (max 3 iterations, score ≥70, returns best attempt). Day plans generated per-city in background with discover -> AI plan -> TSP optimize -> schedule (smart meal placement) -> auto-select transport mode -> weather integration.

**Service flow**: `routers/` -> `orchestrators/` -> `agents/` + `services/` + `algorithms/`

**Key directories:**
- `app/config/` - Settings (`settings.py`), planning constants (`planning.py`), regional transport (`regional_transport.py` — 45+ profiles)
- `app/prompts/` - 14 centralized .md templates loaded via `PromptLoader` (journey, day_plan, chat, tips)
- `app/core/` - JWT auth (`auth.py`), shared HTTP client with retry (`http.py`), request tracing middleware (`middleware.py`)
- `app/services/llm/` - Abstract LLM base + Azure OpenAI (o1/o3/gpt-5 support), Anthropic (tool_use), Gemini (json_schema)
- `app/services/google/` - Places, Routes, Directions, Weather services
- `app/agents/` - Scout, Enricher, Reviewer, Planner, DayPlanner agents
- `app/orchestrators/` - Journey and DayPlan orchestrators
- `app/db/` - SQLAlchemy 2.0 async + asyncpg (PostgreSQL), auto-SSL for remote hosts
- `app/algorithms/` - TSP solver, scheduler, quality scoring (7 weighted metrics)
- `app/dependencies.py` - FastAPI Depends() wiring for all services, auth, DB

## Code Style

### Python
- **Types**: Generic hints (`list[str]`, `dict[str, Any]`)
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
- Design: Inter (body) + Plus Jakarta Sans (display), Indigo primary, Orange accent

## Build and Test

```bash
# Backend
cd backend && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head             # Run database migrations
uvicorn app.main:app --reload --port 8000
pytest -v                        # Run all 164 tests (requires Docker)

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

### SSE Streaming
Events use `ProgressEvent` model: `scouting`, `enriching`, `reviewing`, `planning`, `improving`, `complete`, `error`.
```python
yield f"data: {event.model_dump_json()}\n\n"
```

### Authentication (Dual Auth)
OAuth (Google/GitHub) via authlib. Cookie auth (same-origin) + Bearer token auth (cross-origin/mobile).
```python
from app.dependencies import require_user, get_current_user
# require_user raises 401; get_current_user returns None if unauthenticated
```

### Configuration
```python
from app.config import get_settings  # lru_cached singleton
settings = get_settings()
```

## Environment Variables

Backend (`.env`): `LLM_PROVIDER`, `AZURE_OPENAI_*`, `ANTHROPIC_*`, `GEMINI_*`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `GOOGLE_WEATHER_API_KEY`, `GOOGLE_OAUTH_*`, `GITHUB_OAUTH_*`, `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `COOKIE_DOMAIN`, `APP_URL`, `BACKEND_URL`, `APP_ENV`, `DEBUG`, `LOG_LEVEL`, `CORS_ORIGINS`, `DATABASE_URL`

Frontend (`.env.local`): `VITE_GOOGLE_MAPS_API_KEY` (do NOT set `VITE_API_BASE_URL` in dev — Vite proxy handles it)

Frontend production (`.env.production`): `VITE_API_BASE_URL` (backend URL for split deploy)

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/trips/plan/stream` | Stream journey planning (SSE) |
| POST | `/api/trips/{id}/days/stream` | Stream day plan generation (SSE) |
| POST | `/api/trips/{id}/chat` | Chat-based editing |
| POST | `/api/trips/{id}/tips` | Generate activity tips |
| GET | `/api/trips` | List saved trips |
| GET | `/api/trips/{id}` | Get trip details |
| DELETE | `/api/trips/{id}` | Delete trip |
| POST | `/api/trips/{id}/share` | Create shareable link |
| DELETE | `/api/trips/{id}/share` | Revoke sharing |
| GET | `/api/trips/{id}/export/pdf` | Download PDF itinerary |
| GET | `/api/trips/{id}/export/calendar` | Download .ics calendar |
| GET | `/api/auth/login/{provider}` | Initiate OAuth (google/github) |
| GET | `/api/auth/callback/{provider}` | OAuth callback |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user (public) |
| GET | `/api/places/search` | Search places |
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
