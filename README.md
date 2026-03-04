# Travel Companion

AI-powered multi-city travel planner. Uses LLMs for creative planning decisions and Google APIs for real-time data — routes, distances, opening hours, and transport options.

## How It Works

**Hybrid AI + Deterministic architecture:**

| Layer | Responsibility | Tools |
|-------|---------------|-------|
| **AI (LLM)** | City selection, place curation, day theming, descriptions | Azure OpenAI / Anthropic |
| **Deterministic** | Route optimization, scheduling, time calculations, validation | TSP solver, Google APIs |

**Journey planning pipeline:**

```
Scout (LLM picks cities) → Enrich (Google APIs ground with real data)
  → Review (LLM scores quality ≥70) → Planner (LLM fixes issues) → loop
```

**Day plan pipeline (per city):**

```
Discover highlights → AI plans days → TSP optimizes routes
  → Schedule builder assigns time slots → Google Routes computes legs
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy + aiosqlite |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, Zustand |
| LLM | Azure OpenAI GPT-4o or Anthropic Claude (switchable via config) |
| APIs | Google Places, Google Routes, Google Directions (transit/ferry) |
| Streaming | Server-Sent Events (SSE) for real-time progress |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Edit with your API keys
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # Edit with your API keys
npm run dev                    # Opens at http://localhost:5173
```

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud account (Places, Routes, and Directions APIs enabled)
- Azure OpenAI or Anthropic API access

## Configuration

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `azure_openai` or `anthropic` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., `gpt-4o`) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) |
| `ANTHROPIC_MODEL` | Anthropic model name |
| `GOOGLE_PLACES_API_KEY` | Google Places API key |
| `GOOGLE_ROUTES_API_KEY` | Google Routes API key |
| `CORS_ORIGINS` | Allowed origins (default: `http://localhost:5173`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend URL (default: `http://localhost:8000`) |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key |

See `backend/.env.example` and `frontend/.env.example` for templates.

## API Endpoints

All trip endpoints are under `/api/trips`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/trips/plan/stream` | Stream journey planning (SSE) |
| POST | `/api/trips/{id}/days/stream` | Stream day plan generation (SSE) |
| POST | `/api/trips/{id}/chat` | Edit journey or day plans via chat |
| POST | `/api/trips/{id}/tips` | Generate activity tips |
| GET | `/api/trips` | List saved trips |
| GET | `/api/trips/{id}` | Get full trip details |
| DELETE | `/api/trips/{id}` | Delete a trip |
| GET | `/api/places/search` | Search places |
| GET | `/health` | Health check |

### Example Request

```json
{
  "origin": "Bangalore, India",
  "region": "Vietnam",
  "total_days": 14,
  "start_date": "2026-03-01",
  "interests": ["culture", "food", "history", "nature"],
  "pace": "moderate",
  "return_to_origin": false
}
```

## Project Structure

```
travel-companion/
├── backend/app/
│   ├── main.py                     # FastAPI application
│   ├── dependencies.py             # Depends() wiring for all services
│   ├── config/                     # Settings, planning configs, regional transport
│   ├── core/                       # HTTP client, request tracing middleware
│   ├── db/                         # SQLAlchemy models, engine, repository
│   ├── models/                     # Pydantic v2 models (common, journey, day_plan, trip, chat)
│   ├── routers/                    # trips.py (all trip endpoints), places.py
│   ├── orchestrators/              # journey.py, day_plan.py (pipeline coordination)
│   ├── agents/                     # scout, enricher, reviewer, planner, day_planner
│   ├── services/
│   │   ├── llm/                    # Abstract base + Azure OpenAI / Anthropic
│   │   ├── google/                 # Places, Routes, Directions
│   │   ├── chat.py                 # Chat-based plan editing
│   │   └── tips.py                 # Activity tips generation
│   ├── algorithms/                 # TSP solver, scheduler, quality scoring
│   └── prompts/                    # Markdown templates (journey, day_plan, chat, tips)
├── frontend/src/
│   ├── App.tsx                     # Main app with phase-based routing
│   ├── components/
│   │   ├── trip/                   # InputForm, JourneyPreview, CityCard, DayCard, etc.
│   │   ├── maps/                   # TripMap, DayMap (Google Maps)
│   │   ├── layout/                 # Header, PageContainer
│   │   └── ui/                     # shadcn/ui primitives
│   ├── stores/                     # Zustand (tripStore, uiStore)
│   ├── hooks/                      # useStreamingPlan, useStreamingDayPlans
│   ├── services/api.ts             # API client with SSE streaming
│   └── types/                      # TypeScript interfaces
├── CLAUDE.md                       # Claude Code project context
└── docs/plans/                     # Implementation plans
```

## Development

```bash
# Run backend tests
cd backend && source venv/bin/activate
pytest -v

# Type check frontend
cd frontend && npx tsc --noEmit

# Build frontend
cd frontend && npm run build

# Lint frontend
cd frontend && npm run lint
```

## License

MIT
