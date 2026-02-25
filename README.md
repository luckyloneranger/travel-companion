# Travel Companion

AI-powered travel planning application with single-city itineraries and multi-city journey planning using Azure OpenAI and Google APIs.

## Features

- 🌍 **Multi-City Journey Planning**: Plan trips across multiple cities with intelligent city selection and travel routing (V6 architecture)
- 🗓️ **Single-City Day Plans**: Detailed daily itineraries with optimized routes and time slots
- 🤖 **AI-Powered Planning**: LLM-driven place selection, theming, and creative recommendations
- 🗺️ **Smart Routing**: TSP-based route optimization to minimize travel time
- ⏰ **Real-Time Data**: Live opening hours, ratings, and travel times from Google APIs
- 📊 **Quality Scoring**: 7-metric evaluation system for itinerary quality
- 🚀 **SSE Streaming**: Real-time progress updates during generation
- ⛴️ **Multi-Modal Transport**: Supports train, bus, and ferry routes with Google Directions API
- 🎯 **Smart Destination Types**: Respects destination types (e.g., "Thai Islands" only suggests islands)

## Architecture

**Hybrid AI + Deterministic approach**:
- **AI Layer (Azure OpenAI GPT-4o)**: Creative decisions - city selection, place selection, theming, tips
- **Deterministic Layer**: Route optimization, schedule building, time calculations, validation

**Two Generation Modes**:
| Mode | Use Case | Time | Description |
|------|----------|------|-------------|
| **FAST** | Single city | ~15-30s | Single-pass AI planning + route optimization |
| **JOURNEY (V6)** | Multi-city | ~2-5min | Scout → Enrich → Review → Planner iterative loop |

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI**: Azure OpenAI GPT-4o
- **APIs**: Google Places API (New), Google Routes API
- **Validation**: Pydantic v2
- **HTTP Client**: httpx (async)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Styling**: Tailwind CSS
- **State**: React hooks
- **Streaming**: Server-Sent Events (SSE)

## Prerequisites

- Python 3.11+
- Node.js 18+
- Azure OpenAI API access
- Google Cloud account with Places and Routes APIs enabled

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/luckyloneranger/travel-companion.git
cd travel-companion
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API keys
```

### 4. Run Development Servers

**Backend** (from `/backend`):
```bash
uvicorn app.main:app --reload --port 8000
```

**Frontend** (from `/frontend`):
```bash
npm run dev
```

Open http://localhost:5173 in your browser.

## Configuration

### Backend Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., "gpt-4") |
| `GOOGLE_PLACES_API_KEY` | Google Places API key |
| `GOOGLE_ROUTES_API_KEY` | Google Routes API key |

### Frontend Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API URL |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key |

## API Endpoints

### Single-City Itinerary
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/itinerary` | POST | Generate a single-city day itinerary |
| `/api/itinerary/stream` | POST | Generate with SSE progress updates |
| `/api/itinerary/tips` | POST | Generate activity tips for places |
| `/api/itinerary/quality` | POST | Evaluate itinerary quality score |

### Multi-City Journey (V6)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/journey/plan/stream` | POST | Generate multi-city journey plan with SSE |
| `/api/journey/days/stream` | POST | Generate detailed day plans for journey |

### Example: Journey Request
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

### Example: Single-City Request
```json
{
  "destination": "Paris, France",
  "start_date": "2026-03-15",
  "end_date": "2026-03-18",
  "interests": ["art", "food", "history"],
  "pace": "moderate"
}
```

### GET /health
Health check endpoint.

## Project Structure

```
travel-companion/
├── backend/
│   └── app/
│       ├── main.py                    # FastAPI application
│       ├── config/                    # Settings & tuning
│       │   ├── settings.py            # Environment config
│       │   ├── tuning.py              # Tunable parameters
│       │   ├── planning.py            # Pace configs
│       │   └── regional_transport.py  # Transport by region
│       ├── core/
│       │   ├── clients/               # HTTP & OpenAI clients
│       │   └── middleware/            # Request tracing
│       ├── prompts/                   # Centralized prompts (.md)
│       │   ├── journey/               # Scout, reviewer, planner
│       │   ├── day_plan/              # Planning, validation
│       │   └── tips/                  # Tips generation
│       ├── generators/
│       │   ├── journey_plan/v6/       # Multi-city planning
│       │   │   ├── orchestrator.py    # Main coordinator
│       │   │   ├── scout.py           # City selection
│       │   │   ├── enricher.py        # Google API grounding
│       │   │   ├── reviewer.py        # Quality evaluation
│       │   │   └── planner.py         # Issue resolution
│       │   ├── day_plan/
│       │   │   ├── fast/              # Single-pass generator
│       │   │   └── quality/           # 7-metric scorer
│       │   └── tips/                  # Activity tips
│       ├── models/                    # Pydantic models
│       ├── routers/                   # API endpoints
│       │   ├── itinerary.py           # Single-city
│       │   └── journey.py             # Multi-city
│       ├── services/
│       │   ├── external/              # Azure OpenAI, Google APIs
│       │   │   ├── azure_openai.py    # LLM service
│       │   │   ├── google_places.py   # Place discovery
│       │   │   ├── google_routes.py   # Driving/walking times
│       │   │   └── google_directions.py # Transit/ferry routes
│       │   └── internal/              # Optimizer, scheduler
│       └── utils/                     # Geo, JSON helpers
├── frontend/
│   └── src/
│       ├── App.tsx                    # Main app
│       ├── components/
│       │   ├── JourneyInputForm.tsx   # Trip input form
│       │   ├── V6JourneyPlanView/     # Journey visualization
│       │   ├── GenerationProgress.tsx # SSE progress display
│       │   └── Header.tsx             # App header
│       ├── services/api.ts            # API client with SSE
│       └── types/                     # TypeScript types
├── ARCHITECTURE.md                    # Design documentation
└── README.md
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest                    # Run all tests
pytest --cov              # With coverage
pytest -k "quality"       # Run specific tests
```

### Code Formatting

```bash
# Backend
cd backend
black .
isort .

# Frontend
cd frontend
npm run lint
npm run build
```

## Quality Evaluation

The itinerary scorer evaluates plans across 7 metrics:
- **Duration Balance**: Appropriate time at each place
- **Geographic Efficiency**: Minimized backtracking
- **Meal Timing**: Meals at appropriate times
- **Opening Hours**: Places visited when open
- **Theme Alignment**: Activities match interests
- **Travel Efficiency**: Reasonable transit times
- **Variety**: Mix of activity types

## License

MIT
