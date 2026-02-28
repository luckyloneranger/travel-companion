# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Travel Companion AI — a hybrid AI + deterministic travel planning app. LLMs handle creative decisions (place selection, theming, descriptions); deterministic layers handle calculations (distance, time, validation, scheduling).

Two modes:
- **FAST:** Single-pass itinerary generation (~15-30s) for a single city
- **JOURNEY (V6):** Multi-city planning with Scout→Enrich→Review→Planner loop (~2-5min), iterating until quality threshold (min 70 score, max 3 iterations)

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
pytest                    # All tests
pytest -k "quality"       # Run specific tests
pytest --cov              # With coverage
```

Test files: `backend/tests/test_itinerary.py` (model validation), `test_quality.py` (quality scorer), `test_itinerary_quality.py` (7-metric evaluator tests), `test_journey_live.py` (integration, requires API keys), `test_chat_edit_enrichment_live.py` (chat edit enrichment, requires API keys). Fixtures in `conftest.py` provide `client` (TestClient) and `sample_itinerary_request`.

## Architecture

### Code Flow
`routers/` → `generators/` → `services/{external,internal}/`

- **Routers** (`app/routers/`): FastAPI endpoints, HTTP error handling
- **Generators** (`app/generators/`): Orchestration logic
  - `day_plan/fast/` — FastItineraryGenerator: geocode → discover → AI plan → TSP optimize → schedule → validate
  - `day_plan/quality/` — ItineraryScorer with 7 evaluators (meal timing, geographic clustering, travel efficiency, variety, opening hours, theme alignment, duration appropriateness)
  - `journey_plan/v6/` — V6Orchestrator: Scout(LLM) → Enrich(Google APIs) → Review(LLM, score≥70?) → Planner(LLM, fix issues) → loop
- **External Services** (`app/services/external/`): Azure OpenAI, Google Places, Google Routes (driving/walking via Routes API), Google Directions (transit/ferry/train via Directions API — separate service, instantiated ad-hoc, not in registry)
- **Internal Services** (`app/services/internal/`): Route optimizer (TSP), schedule builder, journey chat (journey edit via LLM), dayplan chat (day plan edit with place search)
- **Utilities** (`app/utils/`): Geo helpers, JSON parsing helpers, place classifier
- **Core Clients** (`app/core/clients/`): `HTTPClientPool` (shared httpx client) and `OpenAIClient` (shared Azure OpenAI client) singletons
- **Core Middleware** (`app/core/middleware/`): `RequestTracingMiddleware` (X-Request-ID + timing) and `RequestLoggingFilter` (request_id in logs)
- **Prompts** (`app/prompts/`): Markdown templates loaded via `app.prompts.loader`
- **Config** (`app/config/`): Settings (Pydantic BaseSettings), tuning params, planning configs (`planning.py` — pace/duration configs), regional transport (`regional_transport.py` — steers LLM toward region-appropriate transport)

### Key Patterns

**Service Registry** — lazy singletons via `app.core.registry` (covers Places + Routes only; `AzureOpenAIService` is instantiated directly in generators):
```python
from app.core import registry
places = registry.get_places()
routes = registry.get_routes()
await registry.close_all()  # cleanup on shutdown
```

**Prompt Templates** — centralized .md templates:
```python
from app.prompts.loader import journey_prompts, day_plan_prompts, tips_prompts
system = journey_prompts.load("scout_system")
user = day_plan_prompts.load("planning_user")
```

**Configuration** — settings and tuning params:
```python
from app.config import get_settings        # lru_cached singleton
from app.config.tuning import FAST_MODE    # dataclass with temperatures, max_tokens, etc.
```

**LLM Calls**:
```python
service = AzureOpenAIService()
data = await service.chat_completion_json(system, user)  # returns parsed JSON
```

**SSE Streaming** — endpoints yield `data: {json}\n\n` events with types: `progress`, `complete`, `error`. Frontend consumes via `AsyncGenerator` in `frontend/src/services/api.ts` with AbortController for cancellation.

**Async throughout** — all I/O (LLM calls, Google API calls) uses async/await with shared `httpx.AsyncClient`.

**Request Tracing** — `RequestTracingMiddleware` (defined in `app/core/middleware/`, registered in `main.py`) adds `X-Request-ID` to every request/response with timing logs. `RequestLoggingFilter` injects `request_id` into log records.

**Frontend state** — React hooks with `useState`/`useEffect`, no external state library. `App.tsx` manages dual-mode UI (`appMode: 'journey' | 'itinerary'`) with phase-based rendering (input → planning → preview → day-plans). `ErrorBoundary` wraps the app in `main.tsx`.

## Code Style

### Python (Backend)
- Generic type hints: `list[str]`, `dict[str, Any]` (not `List`, `Dict`)
- Pydantic v2: `BaseModel` with `Field(...)`, `@field_validator`, `model_dump()`
- Enums as `class Pace(str, Enum)` for JSON serialization
- Google-style docstrings
- Formatting: black + isort

### TypeScript (Frontend)
- Strict mode enabled
- Functional components with hooks
- Path alias: `@/*` maps to `src/*`
- Tailwind CSS for styling (custom primary purple/violet palette, Inter + Plus Jakarta Sans fonts)

## API Endpoints
- `POST /api/itinerary` — single-city itinerary
- `POST /api/itinerary/stream` — single-city with SSE streaming
- `POST /api/tips` — generate tips for activities
- `POST /api/quality/evaluate` — score itinerary quality (7 metrics)
- `GET /api/places/search` — search places (used by day plan chat)
- `POST /api/journey/plan` — multi-city journey plan (non-streaming)
- `POST /api/journey/plan/stream` — multi-city journey plan (SSE)
- `POST /api/journey/days/stream` — multi-city day details (SSE)
- `POST /api/journey/chat/edit` — edit journey via natural language chat
- `POST /api/journey/days/chat/edit` — edit day plans via chat
- `GET /health` — health check

**Legacy aliases** (hidden from schema, `include_in_schema=False`): `/api/journey/v6/plan`, `/api/journey/v6/plan/stream`, `/api/journey/v6/days/stream` — frontend currently hits these v6 paths.

## Environment Variables

**Backend** (`backend/.env`): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_ROUTES_API_KEY`, `APP_ENV`, `DEBUG`, `CORS_ORIGINS`, `LOG_LEVEL`

**Frontend** (`frontend/.env.local`): `VITE_API_BASE_URL` (defaults to `http://localhost:8000`), `VITE_GOOGLE_MAPS_API_KEY`
