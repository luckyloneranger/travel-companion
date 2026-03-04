# Regular Everyday Traveller

AI-powered multi-city travel planner. Uses LLMs for creative planning decisions and Google APIs for real-time data — routes, distances, opening hours, weather, and transport options.

## How It Works

**Hybrid AI + Deterministic architecture:**

| Layer | Responsibility | Tools |
|-------|---------------|-------|
| **AI (LLM)** | City selection, place curation, day theming, cost estimation, descriptions | Azure OpenAI / Anthropic / Gemini |
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

- **Multi-city journey planning** with quality-scored iterative refinement (returns best attempt across iterations)
- **Group travel support** — plan for solo, couples, families (with children/infants), or friend groups with age-aware cost estimates
- **Guided wizard input** — 5-step form (Where → When & Who → Style → Budget → Review) with quick-start templates
- **Unified trip view** — journey overview and day plans on a single page, no context switching
- **Inline day plans** — generated in background, rendered per-city inside each city card
- **Per-day timeline** — activities with time, cost, rating, photos, address, weather, and tips shown inline (no clicks needed)
- **Smart transport selection** — walks short distances, drives or takes transit for longer legs (based on real Google travel times)
- **Weather integration** — daily forecasts on day plans, inline warnings for outdoor activities in bad weather
- **Budget tracking** — complete cost breakdown across all categories (accommodation, transport, dining, activities), per-city totals, journey total — all costs reflect total for the group
- **Interactive maps** — journey-level city map + per-day route maps in fullscreen overlay
- **Chat editing** — modify journeys and day plans via natural language with suggestion chips
- **User accounts** — OAuth login via Google or GitHub, trip ownership; all trip endpoints require authentication
- **Trip sharing** — shareable links for read-only access with inline day plans
- **Export** — PDF itinerary and .ics calendar export
- **Activity tips** — LLM-generated insider tips for each place, shown inline
- **Dark mode** — full component coverage with system preference detection
- **Session persistence** — refreshing the page restores your current trip
- **Quality filtering** — filters out closed/low-rated places, prefers current opening hours over regular

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy + asyncpg (PostgreSQL) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, Zustand |
| LLM | Azure OpenAI GPT-4o, Anthropic Claude, or Google Gemini (switchable via config) |
| APIs | Google Places, Routes, Directions, Weather |
| Auth | OAuth (Google/GitHub) via authlib, dual auth: JWT httpOnly cookies + Bearer tokens |
| Streaming | Server-Sent Events (SSE) for real-time progress |
| Export | weasyprint (PDF), icalendar (.ics) |

## Quick Start

### 1. Database

```bash
docker compose up -d db    # Start PostgreSQL
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Edit with your API keys
alembic upgrade head    # Run database migrations
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # Edit with your Google Maps API key
npm run dev                    # Opens at http://localhost:5173
```

> **Note:** Do not set `VITE_API_BASE_URL` in development. The Vite dev server proxies `/api` to `:8000`, which is required for OAuth cookies to work.

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for PostgreSQL and tests)
- Google Cloud account (Places, Routes, Directions, and Weather APIs enabled)
- Azure OpenAI, Anthropic, or Google Gemini API access
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
| `COOKIE_DOMAIN` | Cookie domain for cross-subdomain auth (e.g., `.example.com`) |
| `DATABASE_URL` | PostgreSQL connection string (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/ret`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key |
| `VITE_API_BASE_URL` | Backend URL for split deployment (leave empty in dev) |

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
  "total_days": 7,
  "start_date": "2026-07-01",
  "interests": ["food", "culture", "nature"],
  "pace": "moderate",
  "budget": "moderate",
  "budget_usd": 5000,
  "travelers": {"adults": 2, "children": 1, "infants": 0},
  "must_include": ["Mount Fuji", "Fushimi Inari"],
  "avoid": ["crowded malls"]
}
```

## Project Structure

```
travel-companion/
├── Dockerfile                        # Multi-stage build (Node + Python)
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
│   │   ├── llm/                    # Abstract base + Azure OpenAI / Anthropic / Gemini
│   │   ├── google/                 # Places, Routes, Directions, Weather
│   │   ├── chat.py                 # Chat-based plan editing
│   │   ├── tips.py                 # Activity tips generation
│   │   └── export.py               # PDF and calendar export
│   ├── algorithms/                 # TSP solver, scheduler, quality scoring (7 evaluators)
│   └── prompts/                    # Markdown templates (journey, day_plan, chat, tips)
├── backend/tests/                  # 164 tests (API, agents, algorithms, services, weather, auth)
├── frontend/src/
│   ├── App.tsx                     # Main app — wizard input → planning → unified trip view
│   ├── components/
│   │   ├── trip/                   # WizardForm, WizardStepper, TemplateGallery, PlanningDashboard,
│   │   │                          # JourneyDashboard, CompactCityCard, DayTimeline, BudgetSummary, ChatPanel
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

## Deployment

Supports multiple deployment modes via dual auth (cookie + Bearer token):

| Mode | Auth Method | Setup |
|------|-------------|-------|
| **Dev** | Cookie via Vite proxy | Default — no config needed |
| **Single container** | Cookie (same-origin) | `docker build -t ret .` then run with env vars |
| **Split deploy (same domain)** | Cookie (cross-subdomain) | Set `COOKIE_DOMAIN=.example.com` |
| **Split deploy (different domains)** | Bearer token | Set `VITE_API_BASE_URL`, `CORS_ORIGINS` |
| **Mobile app** | Bearer token | Use `Authorization: Bearer` header |

### Single Container (Docker)

```bash
docker build -t ret .
docker run -p 8000:8000 --env-file backend/.env ret
```

The multi-stage Dockerfile builds the frontend (Node 20) and serves it alongside the backend (Python 3.11). The backend auto-serves the built frontend from `static/` when present. Requires `DATABASE_URL` pointing to a PostgreSQL instance.

### Split Deployment

For separate frontend (e.g., Vercel, Azure Static Web Apps) and backend (e.g., Azure App Service):

1. Set `VITE_API_BASE_URL` in `frontend/.env.production` to the backend URL
2. Set `CORS_ORIGINS` on the backend to include the frontend URL
3. Auth works via Bearer tokens — the OAuth callback redirects with `?token=` in the URL, which the frontend captures and stores in localStorage

## Testing

> **Note:** Tests require Docker running — they spin up a PostgreSQL container via testcontainers.

```bash
# Run all backend tests (164 tests)
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
