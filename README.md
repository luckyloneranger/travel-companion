# Travel Companion

AI-powered multi-city travel planner. Uses LLMs for creative planning decisions and Google APIs for real-time data — routes, distances, opening hours, weather, and transport options.

## How It Works

**Hybrid AI + Deterministic architecture:**

| Layer | Responsibility | Tools |
|-------|---------------|-------|
| **AI (LLM)** | City selection, place curation, day theming, cost estimation, descriptions | Azure OpenAI / Anthropic |
| **Deterministic** | Route optimization, scheduling, time calculations, validation | TSP solver, Google APIs |

**Journey planning pipeline:**

```
Scout (LLM picks cities + estimates costs) → Enrich (Google APIs ground with real data)
  → Review (LLM scores quality ≥70) → Planner (LLM fixes issues) → loop (best attempt returned)
```

**Day plan pipeline (per city):**

```
Discover places → AI plans days (with time constraints) → TSP optimizes routes
  → Schedule builder assigns time slots → Auto-select best transport mode
  → Attach weather forecasts → Add weather warnings for outdoor activities
```

## Features

- **Multi-city journey planning** with quality-scored iterative refinement
- **Guided wizard input** — 5-step form with quick-start templates, visual interest/pace/budget cards
- **Per-day itineraries** with timeline view, themed days, meal timing, and pace control
- **Smart transport selection** — walks short distances, drives or takes transit for longer legs (based on real Google travel times)
- **Weather integration** — daily forecasts on day plans, warnings for outdoor activities in bad weather
- **Budget tracking** — LLM-estimated costs per activity, daily aggregation, accommodation and transport costs from journey plan
- **Interactive maps** — journey-level city map + per-day activity maps with route polylines
- **Chat editing** — modify journeys and day plans via natural language with suggestion chips (asks clarifying questions for vague requests)
- **User accounts** — OAuth login via Google or GitHub, trip ownership
- **Trip sharing** — shareable links for read-only access
- **Export** — PDF itinerary and .ics calendar export
- **Activity tips** — LLM-generated insider tips for each place
- **Dark mode** — full component coverage with system preference detection
- **Session persistence** — refreshing the page restores your current trip and phase
- **Browser navigation** — back/forward buttons navigate between app phases
- **Quality filtering** — filters out closed/low-rated places, prefers current opening hours over regular

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy + aiosqlite |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, Zustand |
| LLM | Azure OpenAI GPT-4o, Anthropic Claude, or Google Gemini (switchable via config) |
| APIs | Google Places, Routes, Directions, Weather |
| Auth | OAuth (Google/GitHub) via authlib, JWT httpOnly cookies |
| Streaming | Server-Sent Events (SSE) for real-time progress |
| Export | weasyprint (PDF), icalendar (.ics) |

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
cp .env.example .env.local    # Edit with your Google Maps API key
npm run dev                    # Opens at http://localhost:5173
```

> **Note:** Do not set `VITE_API_BASE_URL` in development. The Vite dev server proxies `/api` to `:8000`, which is required for OAuth cookies to work.

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud account (Places, Routes, Directions, and Weather APIs enabled)
- Azure OpenAI or Anthropic API access
- OAuth credentials (Google and/or GitHub) for user accounts

### System Dependencies (PDF export)

```bash
# macOS
brew install pango glib

# Ubuntu/Debian
apt-get install libpango-1.0-0 libglib2.0-0
```

## Configuration

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `azure_openai`, `anthropic`, or `gemini` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., `gpt-4o`) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) |
| `ANTHROPIC_MODEL` | Anthropic model name |
| `GEMINI_API_KEY` | Google Gemini API key (if using Gemini) |
| `GEMINI_MODEL` | Gemini model name (default: `gemini-2.5-flash`) |
| `GOOGLE_PLACES_API_KEY` | Google Places API key |
| `GOOGLE_ROUTES_API_KEY` | Google Routes API key |
| `GOOGLE_WEATHER_API_KEY` | Google Weather API key |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth 2.0 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth 2.0 client secret |
| `GITHUB_OAUTH_CLIENT_ID` | GitHub OAuth app client ID |
| `GITHUB_OAUTH_CLIENT_SECRET` | GitHub OAuth app client secret |
| `JWT_SECRET_KEY` | Secret key for JWT token signing |
| `CORS_ORIGINS` | Allowed origins (default: `http://localhost:5173`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key |

See `backend/.env.example` and `frontend/.env.example` for templates.

## API Endpoints

### Trips (`/api/trips`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/trips/plan/stream` | Stream journey planning (SSE) |
| POST | `/api/trips/{id}/days/stream` | Stream day plan generation (SSE) |
| POST | `/api/trips/{id}/chat` | Edit journey or day plans via chat |
| POST | `/api/trips/{id}/tips` | Generate activity tips |
| GET | `/api/trips` | List saved trips |
| GET | `/api/trips/{id}` | Get full trip details |
| DELETE | `/api/trips/{id}` | Delete a trip |
| POST | `/api/trips/{id}/share` | Create shareable link |
| DELETE | `/api/trips/{id}/share` | Revoke sharing |
| GET | `/api/trips/{id}/export/pdf` | Download PDF itinerary |
| GET | `/api/trips/{id}/export/calendar` | Download .ics calendar |

### Auth (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/auth/login/{provider}` | Initiate OAuth (google/github) |
| GET | `/api/auth/callback/{provider}` | OAuth callback |
| POST | `/api/auth/logout` | Logout (clear cookie) |
| GET | `/api/auth/me` | Get current user |

### Other

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/places/search` | Search places (Google Places) |
| GET | `/api/shared/{token}` | Get shared trip (no auth required) |
| GET | `/health` | Health check (status, version, provider) |

### Example Request

```json
{
  "destination": "Japan",
  "origin": "London",
  "total_days": 5,
  "start_date": "2026-07-01",
  "interests": ["food", "culture", "nature"],
  "pace": "moderate",
  "budget": "moderate",
  "budget_usd": 3000,
  "must_include": ["Mount Fuji", "Fushimi Inari"],
  "avoid": ["crowded malls"]
}
```

## Project Structure

```
travel-companion/
├── backend/app/
│   ├── main.py                     # FastAPI application
│   ├── dependencies.py             # Depends() wiring for all services
│   ├── config/                     # Settings, planning configs, regional transport
│   ├── core/                       # HTTP client (with retry), request tracing middleware
│   ├── db/                         # SQLAlchemy models, engine, repository
│   ├── models/                     # Pydantic v2 models (common, journey, day_plan, trip, chat)
│   ├── routers/                    # trips.py, places.py, auth.py, export.py
│   ├── orchestrators/              # journey.py, day_plan.py (pipeline coordination)
│   ├── agents/                     # scout, enricher, reviewer, planner, day_planner
│   ├── services/
│   │   ├── llm/                    # Abstract base + Azure OpenAI / Anthropic
│   │   ├── google/                 # Places, Routes, Directions, Weather
│   │   ├── chat.py                 # Chat-based plan editing
│   │   ├── tips.py                 # Activity tips generation
│   │   └── export.py               # PDF and calendar export
│   ├── algorithms/                 # TSP solver, scheduler, quality scoring (7 evaluators)
│   └── prompts/                    # Markdown templates (journey, day_plan, chat, tips)
├── backend/tests/                  # 163 tests (API, agents, algorithms, services, weather)
├── frontend/src/
│   ├── App.tsx                     # Main app with phase routing, wizard → dashboard → timeline
│   ├── components/
│   │   ├── trip/                   # WizardForm, WizardStepper, TemplateGallery, PlanningDashboard,
│   │   │                          # JourneyDashboard, CompactCityCard, DayPlansView, DayNav,
│   │   │                          # DayTimeline, BudgetSummary, ChatPanel
│   │   │   └── wizard/            # WizardStepWhere/When/Style/Budget/Review
│   │   ├── maps/                   # TripMap, DayMap (Google Maps)
│   │   ├── layout/                 # Header, PageContainer
│   │   └── ui/                     # shadcn/ui primitives
│   ├── stores/                     # Zustand (tripStore, uiStore, authStore)
│   ├── hooks/                      # useStreamingPlan, useStreamingDayPlans
│   ├── pages/                      # SharedTrip (public shared trip view)
│   ├── services/api.ts             # API client with SSE streaming + 401 handling
│   └── types/                      # TypeScript interfaces
└── CLAUDE.md                       # Claude Code project context
```

## Testing

```bash
# Run all backend tests (163 tests)
cd backend && source venv/bin/activate
pytest -v

# Run with coverage
pytest --cov=app

# Type check frontend
cd frontend && npx tsc --noEmit

# Build frontend
cd frontend && npm run build

# Lint frontend
cd frontend && npm run lint
```

## License

MIT
