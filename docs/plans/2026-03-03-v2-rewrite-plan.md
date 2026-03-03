# Travel Companion V2 — Full Rewrite Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the entire Travel Companion app from scratch with identical functionality, unified pipeline, multi-provider LLM support, SQLite persistence, Zustand state management, and shadcn/ui design system.

**Architecture:** Unified trip planning pipeline (single-city = 1-city journey). LLM provider abstraction (Azure OpenAI + Anthropic Claude via structured output). SQLite for trip persistence. React + Vite + Zustand + shadcn/ui frontend with fresh design.

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy async (SQLite) / httpx / Pydantic v2 | React 18 / TypeScript / Vite / Zustand / shadcn/ui / Tailwind / @vis.gl/react-google-maps

---

## Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pipeline | Unified (single-city = 1-city journey) | Eliminates FAST/JOURNEY duplication |
| Journey + Day Plans | Separate SSE streams | Avoids LLM overload, user controls flow |
| LLM | Multi-provider (Azure OpenAI + Claude) | Flexibility, structured output via function_calling/tool_use |
| Models | Pydantic v2 everywhere | No dataclass/Pydantic split |
| DI | FastAPI Depends() | Testable, swappable services |
| Persistence | SQLite via aiosqlite + SQLAlchemy async | Trips survive refresh, zero-ops |
| Auth | None | Keep it simple |
| Frontend state | Zustand | Clean separation from components |
| UI library | shadcn/ui + Tailwind | Consistent, professional |
| Design | Fresh modern design | Clean rebuild |
| Maps | @vis.gl/react-google-maps | Keep, works well |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │  Zustand    │  │  API Client  │  │  shadcn/ui +     │  │
│  │  Stores     │  │  (SSE/REST)  │  │  Components      │  │
│  └────────────┘  └─────────────┘  └──────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ SSE / REST
┌──────────────────────────┴──────────────────────────────┐
│                   Backend (FastAPI)                       │
│                                                          │
│  ┌──────────┐    ┌──────────────────┐                    │
│  │ Routers  │───▶│  Orchestrators   │                    │
│  │ (trips,  │    │  (Journey, Day)  │                    │
│  │  places) │    └────────┬─────────┘                    │
│  └──────────┘         ┌───┴───┐                          │
│                  ┌────┴────┐ ┌┴──────────┐               │
│                  │ Agents  │ │ Algorithms │               │
│                  │ Scout   │ │ TSP        │               │
│                  │ Enricher│ │ Scheduler  │               │
│                  │ Reviewer│ │ Quality    │               │
│                  │ Planner │ └────────────┘               │
│                  └────┬────┘                              │
│              ┌────────┴─────────┐                        │
│         ┌────┴─────┐    ┌──────┴──────┐                  │
│         │  LLM     │    │  Google     │                  │
│         │  Service  │    │  APIs       │                  │
│         │ (multi)  │    │ (Places,    │                  │
│         └──────────┘    │  Routes,    │                  │
│                         │  Directions)│                  │
│         ┌──────────┐    └─────────────┘                  │
│         │  SQLite  │                                     │
│         │  (trips) │                                     │
│         └──────────┘                                     │
└──────────────────────────────────────────────────────────┘
```

---

## Module Structure

### Backend

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, middleware
│   ├── dependencies.py            # All Depends() factories
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # Pydantic BaseSettings (env vars)
│   │   ├── planning.py            # Pace configs, duration-by-type, interest maps
│   │   └── regional_transport.py  # Region-specific transport guidance
│   │
│   ├── models/
│   │   ├── __init__.py            # Re-export all
│   │   ├── common.py              # Location, Destination, Pace, TravelMode, Budget
│   │   ├── trip.py                # TripRequest, TripResponse
│   │   ├── journey.py             # CityStop, TravelLeg, Accommodation, JourneyPlan
│   │   ├── day_plan.py            # Place, Activity, Route, DayPlan
│   │   ├── quality.py             # MetricResult, QualityReport
│   │   ├── chat.py                # ChatEditRequest/Response
│   │   └── progress.py            # ProgressEvent types
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── trips.py               # /api/trips/* — plan, stream, save, load, list
│   │   ├── places.py              # /api/places/* — search
│   │   └── health.py              # /health
│   │
│   ├── orchestrators/
│   │   ├── __init__.py
│   │   ├── journey.py             # JourneyOrchestrator (Scout→Enrich→Review→Planner)
│   │   └── day_plan.py            # DayPlanOrchestrator (Discover→AI Plan→Optimize→Schedule)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── scout.py               # Scout agent (LLM: suggest cities + transport + hotels)
│   │   ├── enricher.py            # Enricher (Google: geocode, directions, hotel lookup)
│   │   ├── reviewer.py            # Reviewer agent (LLM: evaluate plan feasibility)
│   │   ├── planner.py             # Planner agent (LLM: fix reviewer issues)
│   │   └── day_planner.py         # Day planner (LLM: select+group activities from candidates)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # LLMService ABC with structured output interface
│   │   │   ├── azure_openai.py    # Azure OpenAI implementation (function_calling)
│   │   │   ├── anthropic.py       # Anthropic Claude implementation (tool_use)
│   │   │   └── factory.py         # Create LLM service from config
│   │   ├── google/
│   │   │   ├── __init__.py
│   │   │   ├── places.py          # Google Places API (geocode, discover, search_lodging)
│   │   │   ├── routes.py          # Google Routes API (driving/walking routes)
│   │   │   └── directions.py      # Google Directions API (transit/ferry/train)
│   │   ├── chat.py                # ChatService (unified journey + day plan editing)
│   │   └── tips.py                # TipsService (generate activity tips)
│   │
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── tsp.py                 # Route optimizer (nearest neighbor + 2-opt)
│   │   ├── scheduler.py           # Schedule builder (time-slot assignment)
│   │   └── quality/
│   │       ├── __init__.py
│   │       ├── scorer.py          # ItineraryScorer (orchestrates 7 evaluators)
│   │       ├── evaluators.py      # All 7 evaluators in one file
│   │       └── models.py          # Quality-specific models
│   │
│   ├── prompts/
│   │   ├── loader.py              # PromptLoader class
│   │   ├── journey/
│   │   │   ├── scout_system.md
│   │   │   ├── scout_user.md
│   │   │   ├── reviewer_system.md
│   │   │   ├── reviewer_user.md
│   │   │   ├── planner_system.md
│   │   │   └── planner_user.md
│   │   ├── day_plan/
│   │   │   ├── planning_system.md
│   │   │   ├── planning_user.md
│   │   │   ├── validation_system.md
│   │   │   └── validation_user.md
│   │   ├── chat/
│   │   │   ├── journey_edit_system.md
│   │   │   ├── journey_edit_user.md
│   │   │   ├── day_plan_edit_system.md
│   │   │   └── day_plan_edit_user.md
│   │   └── tips/
│   │       ├── tips_system.md
│   │       └── tips_user.md
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py              # async SQLAlchemy engine + session factory
│   │   ├── models.py              # SQLAlchemy ORM models (Trip table)
│   │   └── repository.py          # TripRepository (CRUD operations)
│   │
│   └── core/
│       ├── __init__.py
│       ├── http.py                # Shared httpx.AsyncClient pool
│       └── middleware.py          # Request tracing, CORS setup
│
├── tests/
│   ├── conftest.py                # Fixtures, DI overrides, test DB
│   ├── test_models.py             # Pydantic model validation
│   ├── test_quality.py            # Quality scorer + evaluators
│   ├── test_scheduler.py          # Schedule builder tests
│   ├── test_tsp.py                # TSP optimizer tests
│   ├── test_api.py                # Router integration tests (mocked services)
│   └── test_llm_service.py        # LLM abstraction tests
│
├── requirements.txt
└── .env.example
```

### Frontend

```
frontend/
├── src/
│   ├── main.tsx                   # Entry point, ErrorBoundary
│   ├── App.tsx                    # Top-level layout + routing
│   │
│   ├── stores/
│   │   ├── tripStore.ts           # Journey + day plan state (Zustand)
│   │   └── uiStore.ts            # UI state (phase, modals, progress)
│   │
│   ├── services/
│   │   └── api.ts                 # API client (SSE streaming, REST calls)
│   │
│   ├── types/
│   │   └── index.ts               # ALL TypeScript types
│   │
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components (button, card, dialog, etc.)
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   └── PageContainer.tsx
│   │   ├── trip/
│   │   │   ├── InputForm.tsx      # Unified input form (1+ cities)
│   │   │   ├── PlanProgress.tsx   # Streaming progress display
│   │   │   ├── JourneyPreview.tsx # Journey overview (cities, legs, map)
│   │   │   ├── CityCard.tsx       # City in journey
│   │   │   ├── TravelLegCard.tsx  # Inter-city transport
│   │   │   ├── DayCard.tsx        # Day breakdown
│   │   │   ├── ActivityCard.tsx   # Single activity
│   │   │   └── ChatPanel.tsx      # Chat editing interface
│   │   └── maps/
│   │       ├── TripMap.tsx        # Journey-level map
│   │       ├── DayMap.tsx         # Day-level map
│   │       └── DayMapPolylines.tsx
│   │
│   ├── utils/
│   │   └── polyline.ts            # Encoded polyline decoder
│   │
│   ├── hooks/
│   │   └── useStreamingPlan.ts    # SSE consumption hook
│   │
│   └── styles/
│       └── globals.css            # Tailwind + custom CSS vars
│
├── components.json                # shadcn/ui config
├── tailwind.config.ts
├── tsconfig.json
├── vite.config.ts
├── package.json
└── .env.example
```

---

## Data Models (Pydantic v2 — Single Source of Truth)

### Common Models (`models/common.py`)

```python
class Location(BaseModel):
    lat: float
    lng: float

class Destination(BaseModel):
    name: str
    location: Location
    country: str = ""
    timezone: str = ""

class Pace(str, Enum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    PACKED = "packed"

class TravelMode(str, Enum):
    WALK = "WALK"
    DRIVE = "DRIVE"
    TRANSIT = "TRANSIT"

class TransportMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    DRIVE = "drive"
    FERRY = "ferry"
```

### Trip Models (`models/trip.py`)

```python
class TripRequest(BaseModel):
    """Unified input for both single-city and multi-city planning."""
    destination: str            # "Northern Italy" or "Kyoto"
    origin: str = ""            # Where traveler starts from
    total_days: int = Field(ge=1, le=21)
    start_date: date
    interests: list[str] = []
    pace: Pace = Pace.MODERATE
    travel_mode: TravelMode = TravelMode.WALK
    must_include: list[str] = []
    avoid: list[str] = []

class TripSummary(BaseModel):
    """Brief trip summary for listing."""
    id: str
    theme: str
    destination: str
    total_days: int
    cities_count: int
    created_at: datetime
    has_day_plans: bool

class TripResponse(BaseModel):
    """Complete saved trip."""
    id: str
    request: TripRequest
    journey: JourneyPlan
    day_plans: list[DayPlan] | None = None
    quality_score: float | None = None
    created_at: datetime
    updated_at: datetime
```

### Journey Models (`models/journey.py`)

```python
class Accommodation(BaseModel):
    name: str
    address: str = ""
    location: Location | None = None
    place_id: str | None = None
    rating: float | None = None
    photo_url: str | None = None
    price_level: int | None = None  # 0-4 from Google

class CityHighlight(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    suggested_duration_hours: float | None = None

class CityStop(BaseModel):
    name: str
    country: str
    days: int
    highlights: list[CityHighlight] = []
    why_visit: str = ""
    best_time_to_visit: str = ""
    location: Location | None = None
    place_id: str | None = None
    accommodation: Accommodation | None = None

class TravelLeg(BaseModel):
    from_city: str
    to_city: str
    mode: TransportMode
    duration_hours: float = 0
    distance_km: float | None = None
    notes: str = ""
    # Enriched fields
    fare: str | None = None
    operator: str | None = None
    booking_tip: str | None = None
    polyline: str | None = None

class JourneyPlan(BaseModel):
    theme: str
    summary: str
    origin: str = ""
    cities: list[CityStop]
    travel_legs: list[TravelLeg] = []
    total_days: int
    total_distance_km: float | None = None
    total_travel_hours: float | None = None
    review_score: float | None = None
    route: str | None = None    # "Tokyo → Kyoto → Osaka"
```

### Day Plan Models (`models/day_plan.py`)

```python
class Place(BaseModel):
    place_id: str
    name: str
    address: str = ""
    location: Location
    category: str = ""
    rating: float | None = None
    photo_url: str | None = None
    opening_hours: list[str] = []
    website: str | None = None

class Route(BaseModel):
    distance_meters: int = 0
    duration_seconds: int = 0
    duration_text: str = ""
    travel_mode: TravelMode = TravelMode.WALK
    polyline: str | None = None

class Activity(BaseModel):
    id: str
    time_start: str          # "09:00"
    time_end: str            # "10:30"
    duration_minutes: int
    place: Place
    notes: str = ""
    route_to_next: Route | None = None

class DayPlan(BaseModel):
    date: str                # "2026-03-15"
    day_number: int
    theme: str = ""
    activities: list[Activity] = []
    city_name: str = ""      # Which city this day belongs to
```

---

## LLM Service Abstraction (`services/llm/`)

### Base Interface (`base.py`)

```python
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class LLMService(ABC):
    """Abstract LLM service supporting structured output."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text response."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate structured JSON response matching schema."""

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
```

### Azure OpenAI (`azure_openai.py`)

Uses `response_format={"type": "json_schema", "json_schema": {...}}` (structured outputs) or `tools` (function_calling).

### Anthropic Claude (`anthropic.py`)

Uses `tool_use` with `tool_choice={"type": "tool", "name": "submit"}` for guaranteed structured output.

### Factory (`factory.py`)

```python
def create_llm_service(settings: Settings) -> LLMService:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMService(settings.anthropic_api_key, settings.anthropic_model)
    else:  # default: azure_openai
        return AzureOpenAILLMService(settings.azure_openai_endpoint, ...)
```

---

## Dependency Injection (`dependencies.py`)

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()

async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    # Managed by lifespan
    yield app_state.http_client

def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return create_llm_service(settings)

def get_places_service(settings = Depends(get_settings), http = Depends(get_http_client)) -> GooglePlacesService:
    return GooglePlacesService(settings.google_places_api_key, http)

def get_routes_service(settings = Depends(get_settings), http = Depends(get_http_client)) -> GoogleRoutesService:
    return GoogleRoutesService(settings.google_routes_api_key, http)

def get_journey_orchestrator(
    llm = Depends(get_llm_service),
    places = Depends(get_places_service),
    routes = Depends(get_routes_service),
    directions = Depends(get_directions_service),
) -> JourneyOrchestrator:
    return JourneyOrchestrator(llm, places, routes, directions)

def get_day_plan_orchestrator(
    llm = Depends(get_llm_service),
    places = Depends(get_places_service),
    routes = Depends(get_routes_service),
) -> DayPlanOrchestrator:
    return DayPlanOrchestrator(llm, places, routes)

async def get_trip_repository(db = Depends(get_db_session)) -> TripRepository:
    return TripRepository(db)
```

---

## API Endpoints

### Trips Router (`/api/trips`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/trips/plan/stream` | Stream journey planning (SSE) |
| POST | `/api/trips/{trip_id}/days/stream` | Stream day plan generation for saved trip (SSE) |
| POST | `/api/trips/{trip_id}/chat` | Edit trip via chat (journey or day plans) |
| GET | `/api/trips` | List saved trips |
| GET | `/api/trips/{trip_id}` | Get saved trip |
| DELETE | `/api/trips/{trip_id}` | Delete saved trip |
| POST | `/api/trips/{trip_id}/tips` | Generate tips for activities |

### Places Router (`/api/places`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/places/search` | Search places by query |

### Health

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |

---

## Data Flow

### Journey Planning Flow

```
TripRequest
  ↓
JourneyOrchestrator.plan_stream()
  ├─ 1. Scout (LLM) ─────────── generates cities[], travel_legs[], accommodations
  │     → yield ProgressEvent("scouting", 15%)
  │
  ├─ 2. Enricher (Google APIs) ─ geocode cities, validate hotels, get directions
  │     → yield ProgressEvent("enriching", 40%)
  │
  ├─ 3. Reviewer (LLM) ──────── score plan (0-100), list issues
  │     → yield ProgressEvent("reviewing", 60%)
  │
  ├─ 4. IF score < 70 AND iterations < 3:
  │     ├─ Planner (LLM) ────── fix issues
  │     │   → yield ProgressEvent("improving", 70%)
  │     └─ GOTO step 2
  │
  ├─ 5. Save to SQLite ──────── persist TripResponse
  │     → yield ProgressEvent("saving", 95%)
  │
  └─ 6. yield CompleteEvent(journey_plan)
```

### Day Plan Generation Flow (Separate Call)

```
trip_id + TripRequest context
  ↓
DayPlanOrchestrator.generate_stream(journey, request)
  ├─ FOR each city in journey.cities:
  │   ├─ 1. Discover (Google Places) ── find candidate places near city
  │   │     → yield CityStartEvent(city_name, progress)
  │   │
  │   ├─ 2. AI Plan (LLM) ──────────── select + group into themed days
  │   │
  │   ├─ 3. Validate (LLM, optional) ─ refine plan
  │   │
  │   ├─ 4. Optimize (TSP) ─────────── route optimization per day
  │   │
  │   ├─ 5. Schedule (deterministic) ── assign time slots
  │   │
  │   ├─ 6. Bookend (if hotel) ──────── add hotel departure/return activities
  │   │
  │   └─ yield CityCompleteEvent(city_name, day_plans[])
  │
  ├─ Update trip in SQLite with day_plans
  └─ yield CompleteEvent(all_day_plans)
```

---

## Zustand Stores

### tripStore.ts

```typescript
interface TripStore {
  // State
  journey: JourneyPlan | null;
  dayPlans: DayPlan[] | null;
  tripId: string | null;
  savedTrips: TripSummary[];

  // Actions
  setJourney: (journey: JourneyPlan) => void;
  setDayPlans: (plans: DayPlan[]) => void;
  updateJourney: (journey: JourneyPlan) => void;
  updateDayPlans: (plans: DayPlan[]) => void;
  reset: () => void;
  loadTrips: () => Promise<void>;
  loadTrip: (id: string) => Promise<void>;
  deleteTrip: (id: string) => Promise<void>;
}
```

### uiStore.ts

```typescript
interface UIStore {
  // State
  phase: 'input' | 'planning' | 'preview' | 'day-plans';
  progress: ProgressEvent | null;
  error: string | null;
  isPlanning: boolean;
  isGeneratingDays: boolean;
  showChat: boolean;
  showMap: boolean;

  // Actions
  setPhase: (phase: Phase) => void;
  setProgress: (event: ProgressEvent | null) => void;
  setError: (error: string | null) => void;
  startPlanning: () => void;
  finishPlanning: () => void;
  startDayGeneration: () => void;
  finishDayGeneration: () => void;
  toggleChat: () => void;
  toggleMap: () => void;
}
```

---

## Implementation Tasks

### Phase 1: Backend Foundation (Tasks 1-6)

#### Task 1: Project scaffolding + config

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/dependencies.py`
- Create: `backend/app/config/__init__.py`, `backend/app/config/settings.py`
- Create: `backend/app/core/__init__.py`, `backend/app/core/http.py`, `backend/app/core/middleware.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`

**Details:**
- FastAPI app with async lifespan (create httpx client on startup, close on shutdown)
- Pydantic BaseSettings loading from `.env`
- Settings fields: `llm_provider` (azure_openai | anthropic), Azure OpenAI keys, Anthropic API key, Google API keys, app_env, debug, cors_origins, log_level, database_url (default: `sqlite+aiosqlite:///./trips.db`)
- RequestTracingMiddleware (X-Request-ID + timing)
- CORS middleware
- Health endpoint
- Shared httpx.AsyncClient in app state

**Step 1:** Create directory structure
**Step 2:** Write `requirements.txt` with: fastapi, uvicorn, pydantic, pydantic-settings, httpx, aiosqlite, sqlalchemy[asyncio], openai, anthropic, python-dotenv
**Step 3:** Write `settings.py` with all env vars
**Step 4:** Write `main.py` with lifespan, middleware, health endpoint
**Step 5:** Write `dependencies.py` skeleton (settings, http_client)
**Step 6:** Write `core/http.py` and `core/middleware.py`
**Step 7:** Run: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000`
**Step 8:** Verify health endpoint returns 200
**Step 9:** Commit

---

#### Task 2: Pydantic models (all)

**Files:**
- Create: `backend/app/models/__init__.py`, `common.py`, `trip.py`, `journey.py`, `day_plan.py`, `quality.py`, `chat.py`, `progress.py`

**Details:**
Port ALL models from current app to Pydantic v2. No dataclasses. See "Data Models" section above for exact definitions.

Key differences from current:
- `CityStop.location: Location | None` instead of separate `latitude`/`longitude` fields
- All models in `/models/` directory (not scattered across generators)
- `TripRequest` replaces both `JourneyRequest` and `ItineraryRequest`
- `ProgressEvent` is a single type with `phase`, `message`, `progress`, `data` fields

**Step 1:** Write all model files with complete field definitions
**Step 2:** Write `__init__.py` re-exports
**Step 3:** Write basic tests in `tests/test_models.py`
**Step 4:** Run tests
**Step 5:** Commit

---

#### Task 3: LLM service abstraction

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/llm/__init__.py`
- Create: `backend/app/services/llm/base.py`, `azure_openai.py`, `anthropic.py`, `factory.py`

**Details:**
- `LLMService` ABC with `generate()` and `generate_structured()` methods
- `AzureOpenAILLMService`: Uses `openai.AsyncAzureOpenAI` with `response_format={"type": "json_object"}` for structured output (same as current, but cleaner)
- `AnthropicLLMService`: Uses `anthropic.AsyncAnthropic` with `tool_use` for structured output
- `create_llm_service(settings)` factory

For `generate_structured()`:
- Azure: Pass system+user prompt, set response_format to json_object, parse JSON from response
- Anthropic: Create tool with schema's JSON schema, force tool_choice, extract tool input

**Step 1:** Write `base.py` ABC
**Step 2:** Write `azure_openai.py` implementation
**Step 3:** Write `anthropic.py` implementation
**Step 4:** Write `factory.py`
**Step 5:** Write tests with mocked clients
**Step 6:** Run tests
**Step 7:** Commit

---

#### Task 4: Google API services

**Files:**
- Create: `backend/app/services/google/__init__.py`
- Create: `backend/app/services/google/places.py`, `routes.py`, `directions.py`

**Details:**
Port from current codebase with improvements:
- All services accept `httpx.AsyncClient` via constructor (DI, not global singleton)
- `GooglePlacesService`: geocode(), discover_places(), get_place_details(), search_lodging(), get_photo_url()
- `GoogleRoutesService`: compute_route(), compute_routes_batch()
- `GoogleDirectionsService`: get_directions() for transit/ferry

Key cleanup:
- Consistent error handling (log + return None, don't crash pipeline)
- Consistent Location model usage (no lat/lng dicts — always Location)
- Photo URL generation as method, not standalone function

**Step 1:** Write `places.py` (port all methods)
**Step 2:** Write `routes.py` (port all methods)
**Step 3:** Write `directions.py` (port all methods)
**Step 4:** Update `dependencies.py` with service factories
**Step 5:** Commit

---

#### Task 5: Algorithms (TSP + Scheduler + Quality)

**Files:**
- Create: `backend/app/algorithms/__init__.py`, `tsp.py`, `scheduler.py`
- Create: `backend/app/algorithms/quality/__init__.py`, `scorer.py`, `evaluators.py`, `models.py`

**Details:**
Port directly from current codebase — these are deterministic algorithms, no architectural changes needed.

- `RouteOptimizer`: nearest_neighbor + 2-opt, preserve_order option
- `ScheduleBuilder`: time-slot assignment with meal windows, pace multipliers, opening hours
- `ItineraryScorer` + 7 evaluators (meal_timing, geographic_clustering, travel_efficiency, variety, opening_hours, theme_alignment, duration_appropriateness)

**Step 1:** Write `tsp.py` (port RouteOptimizer)
**Step 2:** Write `scheduler.py` (port ScheduleBuilder)
**Step 3:** Write quality scorer + evaluators
**Step 4:** Write tests (test_tsp.py, test_scheduler.py, test_quality.py)
**Step 5:** Run tests
**Step 6:** Commit

---

#### Task 6: Prompt templates

**Files:**
- Create: `backend/app/prompts/loader.py`
- Create: all `.md` files under `backend/app/prompts/journey/`, `day_plan/`, `chat/`, `tips/`

**Details:**
Port ALL prompt templates from current codebase. The prompts are well-written — keep them identical. PromptLoader class with `load(name)` method that reads .md files and returns formatted strings.

Reorganize chat prompts into `prompts/chat/` (currently split between journey/ and day_plan/).

**Step 1:** Write `loader.py`
**Step 2:** Copy all prompt .md files (adjust paths)
**Step 3:** Verify loader works with a quick test
**Step 4:** Commit

---

### Phase 2: Backend Orchestrators + Agents (Tasks 7-10)

#### Task 7: Scout + Enricher agents

**Files:**
- Create: `backend/app/agents/__init__.py`, `scout.py`, `enricher.py`

**Details:**
- `Scout`: Takes TripRequest, calls LLM with scout prompts, returns JourneyPlan (parsed from structured output)
- `Enricher`: Takes JourneyPlan, geocodes cities, enriches accommodations via Places API, gets directions via Directions API, returns enriched JourneyPlan with real coordinates/travel data

Key improvement: Scout uses `llm.generate_structured()` instead of raw JSON parsing.

**Step 1:** Write `scout.py`
**Step 2:** Write `enricher.py`
**Step 3:** Commit

---

#### Task 8: Reviewer + Planner agents

**Files:**
- Create: `backend/app/agents/reviewer.py`, `planner.py`

**Details:**
- `Reviewer`: Takes enriched JourneyPlan, calls LLM with reviewer prompts, returns ReviewResult with score and issues
- `Planner`: Takes JourneyPlan + ReviewResult, calls LLM with planner prompts, returns fixed JourneyPlan

Both use `llm.generate_structured()`.

**Step 1:** Write `reviewer.py`
**Step 2:** Write `planner.py`
**Step 3:** Commit

---

#### Task 9: Journey orchestrator

**Files:**
- Create: `backend/app/orchestrators/__init__.py`, `journey.py`

**Details:**
`JourneyOrchestrator.plan_stream()` — async generator yielding ProgressEvents:
1. Scout → yield progress
2. Enrich → yield progress
3. Review → yield progress
4. IF score < 70 AND iterations < 3: Planner → Enrich → Review → loop
5. Yield CompleteEvent with JourneyPlan

**Step 1:** Write `journey.py`
**Step 2:** Commit

---

#### Task 10: Day plan orchestrator + day planner agent

**Files:**
- Create: `backend/app/agents/day_planner.py`
- Create: `backend/app/orchestrators/day_plan.py`

**Details:**
- `DayPlannerAgent`: LLM-based selection + grouping of discovered places into themed days
- `DayPlanOrchestrator.generate_stream()` — async generator:
  - For each city: discover → AI plan → (validate) → optimize → schedule → bookend
  - Yields CityStartEvent, CityCompleteEvent per city
  - Yields CompleteEvent at end

Port the `FastItineraryGenerator` pipeline but cleaner:
- Each step is a clear function call
- Hotel bookend logic integrated
- Progress events per city

**Step 1:** Write `day_planner.py` (LLM agent for place selection)
**Step 2:** Write `day_plan.py` orchestrator
**Step 3:** Commit

---

### Phase 3: Backend API Layer (Tasks 11-13)

#### Task 11: SQLite persistence

**Files:**
- Create: `backend/app/db/__init__.py`, `engine.py`, `models.py`, `repository.py`

**Details:**
- SQLAlchemy async with aiosqlite
- Single `trips` table: id (UUID), request (JSON), journey (JSON), day_plans (JSON nullable), quality_score (float nullable), created_at, updated_at
- `TripRepository`: save_trip(), get_trip(), list_trips(), update_trip(), delete_trip()
- Auto-create tables on startup via `create_all()`

**Step 1:** Write `engine.py` (create_engine, get_session)
**Step 2:** Write `models.py` (Trip ORM model)
**Step 3:** Write `repository.py` (CRUD)
**Step 4:** Update `dependencies.py` with get_db_session, get_trip_repository
**Step 5:** Update `main.py` lifespan to init DB
**Step 6:** Commit

---

#### Task 12: Trips router (SSE streaming + CRUD)

**Files:**
- Create: `backend/app/routers/__init__.py`, `trips.py`, `places.py`, `health.py`

**Details:**
- `POST /api/trips/plan/stream` — SSE streaming journey planning
  - Consumes JourneyOrchestrator.plan_stream()
  - Auto-saves trip on complete
  - Returns trip_id in complete event
- `POST /api/trips/{trip_id}/days/stream` — SSE streaming day plan generation
  - Loads trip from DB
  - Consumes DayPlanOrchestrator.generate_stream()
  - Updates trip with day_plans on complete
- `POST /api/trips/{trip_id}/chat` — Chat editing
- `GET /api/trips` — List saved trips
- `GET /api/trips/{trip_id}` — Get trip
- `DELETE /api/trips/{trip_id}` — Delete trip
- `POST /api/trips/{trip_id}/tips` — Generate tips

SSE format: `data: {json}\n\n` with event types: progress, city_start, city_complete, complete, error

**Step 1:** Write `trips.py` with all endpoints
**Step 2:** Write `places.py` (search endpoint)
**Step 3:** Write `health.py`
**Step 4:** Register routers in `main.py`
**Step 5:** Run full backend, test with curl
**Step 6:** Commit

---

#### Task 13: Chat service + tips service

**Files:**
- Create: `backend/app/services/chat.py`, `tips.py`

**Details:**
- `ChatService`: Unified service handling both journey and day plan edits
  - `edit_journey(message, journey, context)` — LLM-based journey editing
  - `edit_day_plans(message, day_plans, context)` — LLM-based day plan editing with Google Places grounding
  - Place search detection (keywords) + real place injection into prompt
- `TipsService`: Generate activity tips via LLM

Port from current `journey_chat.py` and `dayplan_chat.py`, unified into single service.

**Step 1:** Write `chat.py`
**Step 2:** Write `tips.py`
**Step 3:** Commit

---

### Phase 4: Frontend Foundation (Tasks 14-18)

#### Task 14: Frontend scaffolding

**Files:**
- Create: entire `frontend/` directory from scratch

**Details:**
- `npm create vite@latest frontend -- --template react-ts`
- Install: tailwindcss, @tailwindcss/vite, zustand, @vis.gl/react-google-maps, lucide-react
- Set up shadcn/ui: `npx shadcn@latest init`
- Add shadcn components: button, card, input, select, badge, dialog, sheet, skeleton, separator, tabs, tooltip, collapsible
- Configure path aliases (`@/*` → `src/*`)
- Set up Tailwind with fresh design tokens (new color palette)
- Create `.env.example` with `VITE_API_BASE_URL`, `VITE_GOOGLE_MAPS_API_KEY`

**Step 1:** Create Vite project
**Step 2:** Install dependencies
**Step 3:** Configure Tailwind with custom theme
**Step 4:** Init shadcn/ui + add components
**Step 5:** Set up path aliases
**Step 6:** Commit

---

#### Task 15: TypeScript types + API client

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/services/api.ts`

**Details:**
- Types mirror backend Pydantic models exactly
- API client with:
  - `planTripStream(request, signal)` → AsyncGenerator<ProgressEvent, JourneyPlan>
  - `generateDayPlansStream(tripId, signal)` → AsyncGenerator<ProgressEvent, DayPlan[]>
  - `editTrip(tripId, message, context)` → ChatResponse
  - `listTrips()` → TripSummary[]
  - `getTrip(id)` → TripResponse
  - `deleteTrip(id)` → void
  - `searchPlaces(query, destination)` → Place[]
  - `generateTips(tripId, activities)` → Tips
- SSE parsing with timeouts, AbortController, error handling

**Step 1:** Write types
**Step 2:** Write API client with SSE streaming
**Step 3:** Write polyline utility
**Step 4:** Commit

---

#### Task 16: Zustand stores

**Files:**
- Create: `frontend/src/stores/tripStore.ts`, `uiStore.ts`

**Details:**
See Zustand Stores section above. Clean separation:
- `tripStore`: Data state (journey, dayPlans, savedTrips)
- `uiStore`: UI state (phase, progress, loading, errors, toggles)

**Step 1:** Write `tripStore.ts`
**Step 2:** Write `uiStore.ts`
**Step 3:** Commit

---

#### Task 17: Layout + input form

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/components/layout/Header.tsx`, `PageContainer.tsx`
- Create: `frontend/src/components/trip/InputForm.tsx`

**Details:**
Fresh design. Key UX decisions:
- Single unified input form (no mode toggle)
- Clean, minimal header
- Input sections: destination, origin, dates, duration, interests (chips), pace
- "Plan My Trip" button
- Saved trips sidebar/dropdown (from SQLite)

Design language:
- Neutral/warm palette (not the current earth-tone — something fresh)
- shadcn/ui cards + buttons
- Clean typography
- Subtle animations

**Step 1:** Write `main.tsx` with ErrorBoundary + APIProvider
**Step 2:** Write `App.tsx` with routing logic (phase-based)
**Step 3:** Write layout components
**Step 4:** Write `InputForm.tsx` with all fields
**Step 5:** Run dev server, verify form renders
**Step 6:** Commit

---

#### Task 18: Planning progress UI

**Files:**
- Create: `frontend/src/components/trip/PlanProgress.tsx`
- Create: `frontend/src/hooks/useStreamingPlan.ts`

**Details:**
- `useStreamingPlan` hook: Manages SSE connection, AbortController, progress state
  - Returns: { startPlanning, cancelPlanning, isPlanning, progress }
  - Integrates with tripStore (sets journey on complete) and uiStore (sets progress/error)
- `PlanProgress`: Displays streaming progress
  - Phase indicator (scouting → enriching → reviewing → improving)
  - Progress bar
  - Current step message
  - Iteration counter (if review loop)
  - Cancel button

**Step 1:** Write `useStreamingPlan.ts`
**Step 2:** Write `PlanProgress.tsx`
**Step 3:** Integrate with App.tsx
**Step 4:** Test end-to-end: form → planning → progress display → journey result
**Step 5:** Commit

---

### Phase 5: Frontend Views (Tasks 19-23)

#### Task 19: Journey preview view

**Files:**
- Create: `frontend/src/components/trip/JourneyPreview.tsx`
- Create: `frontend/src/components/trip/CityCard.tsx`
- Create: `frontend/src/components/trip/TravelLegCard.tsx`

**Details:**
- Journey header (theme, summary, stats)
- Route visualization (origin → city1 → city2 → ...)
- City cards with highlights, accommodation, days
- Travel leg cards with transport info
- "Generate Day Plans" button
- "Show Map" toggle
- "Chat" button to edit journey

**Step 1:** Write `JourneyPreview.tsx`
**Step 2:** Write `CityCard.tsx`
**Step 3:** Write `TravelLegCard.tsx`
**Step 4:** Commit

---

#### Task 20: Day plans view

**Files:**
- Create: `frontend/src/components/trip/DayCard.tsx`
- Create: `frontend/src/components/trip/ActivityCard.tsx`

**Details:**
- Day cards grouped by city
- Activity cards with time, place, rating, photo, notes
- Accommodation activities styled differently (hotel icon)
- Route info between activities (distance, duration)
- "Show Map" toggle per day

**Step 1:** Write `DayCard.tsx`
**Step 2:** Write `ActivityCard.tsx`
**Step 3:** Integrate day plans into JourneyPreview (conditional render)
**Step 4:** Commit

---

#### Task 21: Map components

**Files:**
- Create: `frontend/src/components/maps/TripMap.tsx`
- Create: `frontend/src/components/maps/DayMap.tsx`
- Create: `frontend/src/components/maps/DayMapPolylines.tsx`
- Create: `frontend/src/utils/polyline.ts`

**Details:**
Port from current implementation — these work well.
- `TripMap`: Journey-level map with city + hotel markers
- `DayMap`: Day-level with numbered activity markers + route polylines
- Lazy-loaded with React.lazy + Suspense

**Step 1:** Write `polyline.ts`
**Step 2:** Write `TripMap.tsx`
**Step 3:** Write `DayMap.tsx` + `DayMapPolylines.tsx`
**Step 4:** Integrate with toggle buttons in views
**Step 5:** Commit

---

#### Task 22: Chat panel

**Files:**
- Create: `frontend/src/components/trip/ChatPanel.tsx`

**Details:**
- Slide-in sheet (shadcn Sheet component)
- Chat message list (user + assistant)
- Text input with send button
- Supports both journey editing and day plan editing
- On successful edit: updates tripStore, refreshes view

**Step 1:** Write `ChatPanel.tsx`
**Step 2:** Integrate with JourneyPreview
**Step 3:** Commit

---

#### Task 23: Saved trips view

**Files:**
- Modify: `frontend/src/components/trip/InputForm.tsx` (add saved trips section)

**Details:**
- Below the input form or in a sidebar
- List of saved trips with theme, date, city count
- Click to load trip
- Delete button
- Fetches from `GET /api/trips`

**Step 1:** Add saved trips section to input form
**Step 2:** Wire up load/delete actions
**Step 3:** Commit

---

### Phase 6: Integration + Polish (Tasks 24-26)

#### Task 24: End-to-end testing

**Details:**
- Backend: Full pipeline test with mocked LLM + Google APIs
- Frontend: Build check (tsc + vite build)
- Manual test: form → plan → preview → day plans → maps → chat edit
- Fix any integration issues

**Step 1:** Write `tests/test_api.py` with httpx.AsyncClient
**Step 2:** Run all backend tests
**Step 3:** Run frontend build
**Step 4:** Manual smoke test
**Step 5:** Fix issues
**Step 6:** Commit

---

#### Task 25: Planning config + regional transport

**Files:**
- Create: `backend/app/config/planning.py`, `regional_transport.py`

**Details:**
Port from current:
- Pace configs (relaxed/moderate/packed with activity counts, duration multipliers)
- Duration by type (180 entries mapping place types to minutes)
- Interest-to-type mapping
- Regional transport guidance

**Step 1:** Port `planning.py`
**Step 2:** Port `regional_transport.py`
**Step 3:** Commit

---

#### Task 26: Final cleanup + verification

**Details:**
- Remove all dead code
- Verify all TypeScript types match backend models
- Run full test suite
- Run frontend production build
- Update CLAUDE.md for v2 architecture
- Create .env.example files

**Step 1:** Cleanup
**Step 2:** Full verification
**Step 3:** Update docs
**Step 4:** Final commit

---

## Estimated Effort by Phase

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1 | 1-6 | Backend foundation (config, models, LLM, Google, algorithms, prompts) |
| Phase 2 | 7-10 | Backend orchestrators + agents |
| Phase 3 | 11-13 | Backend API layer (DB, routers, chat/tips) |
| Phase 4 | 14-18 | Frontend foundation (scaffolding, types, stores, form, progress) |
| Phase 5 | 19-23 | Frontend views (journey, days, maps, chat, saved trips) |
| Phase 6 | 24-26 | Integration + polish |

---

## What Changes vs What Stays

| Stays (port directly) | Changes (rewrite) |
|----------------------|-------------------|
| All 16 prompt templates | Model layer → Pydantic v2 only |
| TSP algorithm (nearest neighbor + 2-opt) | DI → FastAPI Depends() |
| Schedule builder (meal timing, pace) | LLM calls → structured output |
| Quality scorer (7 evaluators) | State mgmt → Zustand |
| Google API integrations | UI framework → shadcn/ui |
| Polyline decoder | Pipeline → unified (no FAST/JOURNEY split) |
| SSE streaming pattern | Persistence → SQLite |
| Scout→Enrich→Review→Planner loop | Service singletons → DI factories |
| Regional transport config | Frontend design → fresh |
| Place discovery + filtering | API endpoints → simplified |
