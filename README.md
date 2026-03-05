# Regular Everyday Traveller

AI-powered multi-city travel planner that combines LLMs for creative planning decisions with Google APIs for real-time data — routes, distances, opening hours, weather, and transport options.

## How It Works

**Hybrid AI + Deterministic architecture:**

| Layer | Responsibility | Tools |
|-------|---------------|-------|
| **AI (LLM)** | City selection, place curation, day theming, cost estimation, descriptions | Azure OpenAI / Anthropic / Gemini |
| **Deterministic** | Route optimization, scheduling, time calculations, quality scoring, validation | TSP solver, Google APIs, 7-metric evaluator |

**Journey planning pipeline:**

```
Scout (LLM picks cities + estimates costs) → Enrich (Google APIs ground with real data)
  → Review (LLM scores quality ≥70) → Planner (LLM fixes issues) → loop (max 3 iterations, best attempt returned)
```

**Day plan pipeline (per city, runs in background):**

```
Discover places (Google) → AI plans days (with arrival/departure time constraints)
  → TSP optimizes routes → Schedule builder assigns time slots (smart meal placement)
  → Auto-select best transport mode → Attach weather forecasts → Weather warnings for outdoor activities
```

## Features

- **Multi-city journey planning** with quality-scored iterative refinement (score ≥70, max 3 iterations, returns best attempt)
- **Group travel support** — solo, couples, families (with children/infants), or friend groups with group-aware cost estimates
- **Guided wizard input** — 5-step form (Where → When & Who → Style → Budget → Review) with 6 quick-start templates
- **Unified trip view** — journey overview and day plans on a single page, no context switching
- **Inline day plans** — generated in background, rendered per-city inside collapsible city cards
- **Per-day timeline** — activities with time, duration, cost, rating, photos, address, weather, and tips shown inline
- **Smart transport selection** — walks short distances, drives or transits for longer legs (based on real Google travel times)
- **Regional transport guidance** — 45+ region profiles with mode recommendations, operators, and booking tips for inter-city travel
- **Weather integration** — daily forecasts per city, inline warnings for outdoor activities in bad weather
- **Budget tracking** — cost breakdown across accommodation, transport, dining, and activities — all costs reflect total for the group
- **Interactive maps** — journey-level city map + per-day route maps with color-coded transport modes
- **Chat editing** — modify journeys and day plans via natural language with context-aware suggestion chips
- **User accounts** — OAuth login via Google or GitHub, trip ownership; all trip endpoints require authentication
- **Trip sharing** — shareable links for read-only access with inline day plans
- **Export** — PDF itinerary and .ics calendar export
- **Activity tips** — LLM-generated insider tips for each place, shown inline
- **Dark mode** — full component coverage with system preference detection
- **Session persistence** — refreshing the page restores your current trip
- **Quality scoring** — 7 weighted metrics: meal timing (20%), geographic clustering (15%), route efficiency (15%), activity variety (15%), theme alignment (15%), opening hours (10%), duration realism (10%)
- **Place filtering** — filters out closed/low-rated places, prefers current opening hours over regular

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI 0.109+, Python 3.11+, Pydantic v2, SQLAlchemy 2.0 async + asyncpg (PostgreSQL 16) |
| Frontend | React 19, TypeScript (strict), Vite 6, Tailwind CSS v4, shadcn/ui + Radix UI, Zustand 5 |
| LLM | Azure OpenAI (GPT-4o/GPT-5/o1/o3), Anthropic Claude, or Google Gemini (switchable via config) |
| APIs | Google Places (New), Routes, Directions (transit/ferry), Weather |
| Auth | OAuth (Google/GitHub) via authlib, dual auth: JWT httpOnly cookies + Bearer tokens |
| Maps | Google Maps via @vis.gl/react-google-maps |
| Streaming | Server-Sent Events (SSE) with AbortController + 180s stall timeout |
| Export | weasyprint (PDF), icalendar (.ics) |
| Testing | pytest + pytest-asyncio, testcontainers (PostgreSQL), 164 tests |

## Quick Start

### 1. Database

```bash
docker compose up -d db    # Start PostgreSQL 16
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # Edit with your API keys
alembic upgrade head       # Run database migrations
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # Edit with your Google Maps API key
npm run dev                    # Opens at http://localhost:5173
```

> **Note:** Do not set `VITE_API_BASE_URL` in development. The Vite dev server proxies `/api` to `:8000`, which is required for OAuth cookies to work (same-origin).

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
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., `gpt-4o`, `gpt-5.2-chat`) |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-02-15-preview`) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) |
| `ANTHROPIC_MODEL` | Model name (default: `claude-sonnet-4-20250514`) |
| `GEMINI_API_KEY` | Google Gemini API key (if using Gemini) |
| `GEMINI_MODEL` | Model name (default: `gemini-2.5-flash`) |
| `GOOGLE_PLACES_API_KEY` | Google Places API key |
| `GOOGLE_ROUTES_API_KEY` | Google Routes API key |
| `GOOGLE_WEATHER_API_KEY` | Google Weather API key |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth 2.0 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth 2.0 client secret |
| `GITHUB_OAUTH_CLIENT_ID` | GitHub OAuth app client ID |
| `GITHUB_OAUTH_CLIENT_SECRET` | GitHub OAuth app client secret |
| `JWT_SECRET_KEY` | Secret key for JWT token signing |
| `JWT_EXPIRE_MINUTES` | Token expiry (default: 10080 = 7 days) |
| `APP_URL` | Frontend URL for OAuth redirects (default: `http://localhost:5173`) |
| `BACKEND_URL` | Backend URL for OAuth callbacks (empty = auto-detect) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `COOKIE_DOMAIN` | Cookie domain for cross-subdomain auth (empty = same-origin) |
| `DATABASE_URL` | PostgreSQL connection string |
| `APP_ENV` | `development`, `production`, or `test` |
| `DEBUG` | Enable debug mode (default: `true`) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key |
| `VITE_API_BASE_URL` | Backend URL for split deployment (leave empty in dev) |

See `backend/.env.example` and `frontend/.env.example` for templates.

## API Endpoints

### Trips (`/api/trips`) — all require authentication

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
| GET | `/api/auth/me` | Get current user (public) |

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
├── Dockerfile                         # Multi-stage build (Node 20 + Python 3.11)
├── docker-compose.yml                 # PostgreSQL 16 for local dev
├── CLAUDE.md                          # Claude Code project context
├── backend/
│   ├── alembic/                       # Database migrations (asyncpg + SSL)
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory (v2.0.0)
│   │   ├── dependencies.py           # Depends() wiring for all services
│   │   ├── config/
│   │   │   ├── settings.py            # Pydantic BaseSettings (env vars)
│   │   │   ├── planning.py            # Pace configs, durations by place type, interest mappings
│   │   │   └── regional_transport.py  # 45+ regional transport profiles
│   │   ├── core/
│   │   │   ├── auth.py                # JWT create/decode
│   │   │   ├── http.py                # Shared httpx client with retry (exponential backoff)
│   │   │   └── middleware.py          # Request tracing (X-Request-ID) + timing logs
│   │   ├── db/
│   │   │   ├── engine.py              # Async SQLAlchemy engine (auto-SSL for remote hosts)
│   │   │   ├── models.py             # Trip, User, TripShare tables
│   │   │   └── repository.py         # TripRepository (CRUD + sharing)
│   │   ├── models/                    # Pydantic v2 schemas
│   │   │   ├── common.py             # Location, Pace, TravelMode, TransportMode, Budget enums
│   │   │   ├── journey.py            # JourneyPlan, CityStop, TravelLeg, Accommodation, ReviewResult
│   │   │   ├── day_plan.py           # DayPlan, Activity, Place, Route, Weather
│   │   │   ├── trip.py               # TripRequest, TripResponse, TripSummary, Travelers
│   │   │   ├── chat.py               # ChatEditRequest/Response
│   │   │   ├── progress.py           # ProgressEvent (SSE phases)
│   │   │   ├── quality.py            # QualityReport, QualityMetric
│   │   │   ├── internal.py           # Internal pipeline models
│   │   │   └── user.py               # UserResponse
│   │   ├── routers/
│   │   │   ├── trips.py              # Journey plan, day plans, chat, tips, CRUD, sharing
│   │   │   ├── auth.py               # OAuth login/callback/logout/me
│   │   │   ├── places.py             # Place search
│   │   │   └── export.py             # PDF + calendar export
│   │   ├── orchestrators/
│   │   │   ├── journey.py            # Scout → Enrich → Review → Planner loop
│   │   │   └── day_plan.py           # Discover → AI plan → TSP → Schedule → Routes → Weather
│   │   ├── agents/
│   │   │   ├── scout.py              # LLM: city selection + accommodation + travel legs
│   │   │   ├── enricher.py           # Google APIs: geocode, validate, enrich places
│   │   │   ├── reviewer.py           # LLM: score plan quality (0-100)
│   │   │   ├── planner.py            # LLM: fix review issues
│   │   │   └── day_planner.py        # LLM: activity selection + day theming
│   │   ├── services/
│   │   │   ├── llm/                   # Abstract LLMService + Azure OpenAI / Anthropic / Gemini
│   │   │   ├── google/                # Places, Routes, Directions (transit), Weather
│   │   │   ├── chat.py               # Chat-based journey/day-plan editing
│   │   │   ├── tips.py               # Activity tips generation
│   │   │   └── export.py             # PDF (weasyprint) + calendar (.ics) generation
│   │   ├── algorithms/
│   │   │   ├── tsp.py                # Nearest-neighbor TSP with custom distance functions
│   │   │   ├── scheduler.py          # Time-slot builder (smart meal placement, pace multipliers)
│   │   │   └── quality/              # 7-metric evaluator (meal timing, clustering, efficiency, variety, hours, theme, duration)
│   │   └── prompts/                   # 14 Markdown templates (journey, day_plan, chat, tips)
│   └── tests/                         # 164 tests (pytest + testcontainers PostgreSQL)
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Phase-based SPA (input → planning → preview/day-plans)
│   │   ├── components/
│   │   │   ├── trip/                  # WizardForm, PlanningDashboard, JourneyDashboard, ChatPanel
│   │   │   │   └── wizard/           # 5 wizard steps (Where/When/Style/Budget/Review)
│   │   │   ├── maps/                  # TripMap (cities), DayMap (activities + routes)
│   │   │   ├── layout/               # Header, PageContainer
│   │   │   └── ui/                    # shadcn/ui primitives (button, card, input, sheet, etc.)
│   │   ├── stores/                    # Zustand: tripStore, uiStore, authStore
│   │   ├── hooks/                     # useStreamingPlan, useStreamingDayPlans (SSE + AbortController)
│   │   ├── pages/                     # SharedTrip (public shared trip view)
│   │   ├── services/api.ts           # API client with SSE streaming, dual auth, 401 auto-logout
│   │   └── types/                     # TypeScript interfaces (38 types)
│   └── vercel.json                    # SPA rewrite rules for Vercel deployment
└── docs/plans/                        # Design docs and implementation plans
```

## Deployment

Supports multiple deployment modes via dual auth (cookie + Bearer token):

| Mode | Auth Method | Setup |
|------|-------------|-------|
| **Dev** | Cookie via Vite proxy | Default — no config needed |
| **Single container** | Cookie (same-origin) | `docker build -t ret .` then run with env vars |
| **Split deploy (same domain)** | Cookie (cross-subdomain) | Set `COOKIE_DOMAIN=.example.com` |
| **Split deploy (different domains)** | Bearer token | Set `VITE_API_BASE_URL`, `CORS_ORIGINS`, `APP_URL` |
| **Mobile app** | Bearer token | Use `Authorization: Bearer` header from OAuth `?token=` redirect |

### Single Container (Docker)

```bash
docker build -t ret .
docker run -p 8000:8000 --env-file backend/.env ret
```

The multi-stage Dockerfile builds the frontend (Node 20) and serves it alongside the backend (Python 3.11). The backend auto-serves the built frontend from `static/` when `static/index.html` exists. Requires `DATABASE_URL` pointing to a PostgreSQL instance.

### Split Deployment (e.g., Azure + Vercel)

For separate frontend (e.g., Vercel) and backend (e.g., Azure App Service):

1. Set `VITE_API_BASE_URL` in `frontend/.env.production` to the backend URL
2. Set `CORS_ORIGINS` on the backend to include the frontend URL
3. Set `APP_URL` on the backend to the frontend URL (for OAuth redirects)
4. Auth works via Bearer tokens — the OAuth callback redirects with `?token=` in the URL, which the frontend captures and stores in localStorage

## Testing

> **Note:** Tests require Docker running — they spin up a PostgreSQL container via testcontainers.

```bash
cd backend && source venv/bin/activate

# Run all tests (164 tests)
pytest -v

# Run specific test file
pytest tests/test_tsp.py -v

# Run with coverage
pytest --cov=app

# Frontend
cd frontend
npm run build     # TypeScript check + production build
npm run lint      # ESLint
```

## License

MIT
