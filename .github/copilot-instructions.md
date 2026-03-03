# Travel Companion V2 - AI Agent Guidelines

## Architecture

Hybrid AI + deterministic approach: LLMs (Azure OpenAI or Anthropic) handle creative decisions, Google APIs provide real-time data.

**Unified pipeline:** Multi-city journey planning with Scout -> Enrich -> Review -> Planner loop. Day plans generated per-city with discover -> AI plan -> TSP optimize -> schedule -> route computation.

**Service flow**: `routers/` -> `orchestrators/` -> `agents/` + `services/` + `algorithms/`

**Key directories:**
- `app/config/` - Settings (`settings.py`), planning constants (`planning.py`), regional transport (`regional_transport.py`)
- `app/prompts/` - Centralized .md templates loaded via `PromptLoader`
- `app/core/` - Shared HTTP client (`http.py`), request tracing middleware (`middleware.py`)
- `app/services/llm/` - Abstract LLM base + Azure OpenAI and Anthropic implementations
- `app/services/google/` - Places, Routes, Directions services
- `app/agents/` - Scout, Enricher, Reviewer, Planner, DayPlanner agents
- `app/orchestrators/` - Journey and DayPlan orchestrators
- `app/db/` - SQLAlchemy async + aiosqlite persistence
- `app/dependencies.py` - FastAPI Depends() wiring

## Code Style

### Python
- **Types**: Generic hints (`list[str]`, `dict[str, Any]`)
- **Docstrings**: Google-style with Args/Returns
- **Async**: All LLM/API calls `async` with `httpx.AsyncClient`
- **Enums**: `class Pace(str, Enum)` for JSON serialization

### Pydantic Models (`app/models/`)
```python
class TripRequest(BaseModel):
    destination: str = Field(..., min_length=2, max_length=200)
    total_days: int = Field(..., ge=1, le=21)
    start_date: date
    pace: Pace = Pace.MODERATE
```

### TypeScript
- Functional components with hooks
- Zustand for state management (`tripStore`, `uiStore`)
- shadcn/ui components with Tailwind CSS v4
- Path alias: `@/*` maps to `src/*`

## Build and Test

```bash
# Backend
cd backend && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -v                # Run all tests

# Frontend
cd frontend && npm install
npm run dev              # Vite dev server (port 5173)
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
llm = create_llm_service(settings)  # Azure OpenAI or Anthropic
data = await llm.generate_structured(system, user, schema=MyModel)
```

### SSE Streaming
Events use `ProgressEvent` model: `scouting`, `enriching`, `reviewing`, `planning`, `complete`, `error`.
```python
yield f"data: {event.model_dump_json()}\n\n"
```

### Configuration
```python
from app.config import get_settings  # lru_cached singleton
settings = get_settings()
```

## Environment Variables

Backend (`.env`): `LLM_PROVIDER`, `AZURE_OPENAI_*`, `ANTHROPIC_*`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `APP_ENV`, `DEBUG`, `LOG_LEVEL`, `CORS_ORIGINS`, `DATABASE_URL`

Frontend (`.env.local`): `VITE_API_BASE_URL`, `VITE_GOOGLE_MAPS_API_KEY`

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
| GET | `/api/places/search` | Search places |
| GET | `/health` | Health check |

## Integration Points

| Service | Purpose | Client |
|---------|---------|--------|
| Azure OpenAI / Anthropic | LLM | `app/services/llm/` |
| Google Places | Place discovery | `app/services/google/places.py` |
| Google Routes | Driving/walking times | `app/services/google/routes.py` |
| Google Directions | Transit & ferry routes | `app/services/google/directions.py` |

Frontend SSE consumption: `src/services/api.ts` (async generator pattern with AbortController)
