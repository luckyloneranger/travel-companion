# Content-First Platform Rewrite — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite travel-companion from per-request LLM generation to a pre-generated content library platform with journey assembly.

**Architecture:** PostgreSQL content library (cities, places, plan_variants, day_plans, activities, routes) populated by an offline batch pipeline (Discover → Curate → Route → Schedule → Review → Store). Users browse a city catalog or input trips; a journey assembler stitches pre-made city plans with live transport + weather. On-demand drafts handle cache misses. A PostgreSQL-based job queue coordinates all background work.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Alembic, multi-provider LLM (Azure/Anthropic/Gemini), Google APIs (Places, Routes, Directions, Weather), React 19, Vite, Zustand 5, Tailwind v4, shadcn/ui.

**Design doc:** `docs/plans/2026-04-21-content-first-rewrite-design.md`

---

## Phase 1: Backend Foundation (DB + Models + Config)

### Task 1: Fresh Database Schema

**Files:**
- Create: `backend/alembic/versions/001_content_library_schema.py`
- Create: `backend/app/db/models.py` (replace existing)
- Modify: `backend/app/db/engine.py` (no changes expected, verify it works)

**Step 1: Write the migration**

```python
"""001 content library schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # cities
    op.create_table(
        "cities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(3), nullable=False),
        sa.Column("location", JSONB, nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("population_tier", sa.String(20), nullable=False),
        sa.Column("region", sa.String(100)),
        sa.Column("data_hash", sa.String(64)),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("name", "country_code", name="uq_city_name_country"),
    )

    # places
    op.create_table(
        "places",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("city_id", UUID(as_uuid=True), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("google_place_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("address", sa.String(1000)),
        sa.Column("location", JSONB, nullable=False),
        sa.Column("types", sa.ARRAY(sa.String(100)), nullable=False),
        sa.Column("rating", sa.Float),
        sa.Column("user_rating_count", sa.Integer),
        sa.Column("price_level", sa.SmallInteger),
        sa.Column("opening_hours", JSONB),
        sa.Column("photo_references", sa.ARRAY(sa.String(500))),
        sa.Column("editorial_summary", sa.Text),
        sa.Column("website_url", sa.String(1000)),
        sa.Column("is_lodging", sa.Boolean, server_default=sa.text("false")),
        sa.Column("business_status", sa.String(50), server_default=sa.text("'OPERATIONAL'")),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_places_city", "places", ["city_id"])
    op.create_index("idx_places_lodging", "places", ["city_id", "is_lodging"], postgresql_where=sa.text("is_lodging = true"))

    # plan_variants
    op.create_table(
        "plan_variants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("city_id", UUID(as_uuid=True), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pace", sa.String(20), nullable=False),
        sa.Column("budget", sa.String(20), nullable=False),
        sa.Column("day_count", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'generating'")),
        sa.Column("quality_score", sa.SmallInteger),
        sa.Column("accommodation_id", UUID(as_uuid=True), sa.ForeignKey("places.id")),
        sa.Column("accommodation_alternatives", JSONB),
        sa.Column("booking_hint", sa.Text),
        sa.Column("cost_breakdown", JSONB),
        sa.Column("generation_metadata", JSONB),
        sa.Column("data_hash", sa.String(64)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_variants_lookup", "plan_variants", ["city_id", "pace", "budget", "day_count", "status"])

    # day_plans
    op.create_table(
        "day_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("plan_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_number", sa.SmallInteger, nullable=False),
        sa.Column("theme", sa.String(255), nullable=False),
        sa.Column("theme_description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("variant_id", "day_number", name="uq_variant_day"),
    )

    # activities
    op.create_table(
        "activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("day_plan_id", UUID(as_uuid=True), sa.ForeignKey("day_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("place_id", UUID(as_uuid=True), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("sequence", sa.SmallInteger, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_meal", sa.Boolean, server_default=sa.text("false")),
        sa.Column("meal_type", sa.String(20)),
        sa.Column("estimated_cost_usd", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("day_plan_id", "sequence", name="uq_day_activity_seq"),
    )
    op.create_index("idx_activities_day", "activities", ["day_plan_id"])

    # routes
    op.create_table(
        "routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("day_plan_id", UUID(as_uuid=True), sa.ForeignKey("day_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_activity_id", UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("to_activity_id", UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("travel_mode", sa.String(20), nullable=False),
        sa.Column("distance_meters", sa.Integer, nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column("polyline", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_routes_day", "routes", ["day_plan_id"])

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("name", sa.String(255)),
        sa.Column("avatar_url", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_id", name="uq_user_provider"),
    )

    # journeys
    op.create_table(
        "journeys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.String(500), nullable=False),
        sa.Column("origin", sa.String(500)),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("total_days", sa.SmallInteger, nullable=False),
        sa.Column("pace", sa.String(20), nullable=False),
        sa.Column("budget", sa.String(20), nullable=False),
        sa.Column("travelers", JSONB),
        sa.Column("city_sequence", JSONB, nullable=False),
        sa.Column("transport_legs", JSONB),
        sa.Column("weather_forecasts", JSONB),
        sa.Column("cost_breakdown", JSONB),
        sa.Column("status", sa.String(20), server_default=sa.text("'complete'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_journeys_user", "journeys", ["user_id"])

    # journey_shares
    op.create_table(
        "journey_shares",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("journey_id", UUID(as_uuid=True), sa.ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # generation_jobs
    op.create_table(
        "generation_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("city_id", UUID(as_uuid=True), sa.ForeignKey("cities.id")),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("priority", sa.SmallInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("progress_pct", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("result", JSONB),
        sa.Column("error", sa.Text),
        sa.Column("locked_by", sa.String(100)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_jobs_queue", "generation_jobs", ["status", "priority", "created_at"],
                     postgresql_where=sa.text("status = 'queued'"))
    op.create_index("idx_jobs_city", "generation_jobs", ["city_id", "job_type"])


def downgrade() -> None:
    for table in ["generation_jobs", "journey_shares", "journeys", "users",
                   "routes", "activities", "day_plans", "plan_variants", "places", "cities"]:
        op.drop_table(table)
```

**Step 2: Write SQLAlchemy ORM models**

Replace `backend/app/db/models.py` with ORM table classes matching the migration above. Each table gets a SQLAlchemy `Mapped` class with `mapped_column()`. Relationships:
- `City.places` → `list[Place]`
- `City.variants` → `list[PlanVariant]`
- `PlanVariant.day_plans` → `list[DayPlan]`
- `DayPlan.activities` → `list[Activity]` (ordered by `sequence`)
- `DayPlan.routes` → `list[Route]`
- `Activity.place` → `Place`
- `Journey.user` → `User`

**Step 3: Run migration**

```bash
cd backend && source venv/bin/activate
alembic downgrade base  # clear old schema
alembic upgrade head
```
Expected: all 10 tables created.

**Step 4: Commit**

```bash
git add backend/alembic/ backend/app/db/models.py
git commit -m "feat: content library database schema + ORM models"
```

---

### Task 2: Pydantic Models

**Files:**
- Create: `backend/app/models/city.py`
- Create: `backend/app/models/variant.py`
- Create: `backend/app/models/journey.py`
- Create: `backend/app/models/job.py`
- Modify: `backend/app/models/common.py` (keep existing enums, add PopulationTier + VariantStatus)

**Step 1: Write models**

`city.py`:
```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.common import Location

class CityBase(BaseModel):
    name: str
    country: str
    country_code: str = Field(max_length=3)
    location: Location
    timezone: str
    currency: str = Field(max_length=10)
    population_tier: str  # mega / large / medium / small
    region: str | None = None

class CityCreate(BaseModel):
    name: str
    country: str

class CityResponse(CityBase):
    id: UUID
    variant_count: int = 0
    photo_url: str | None = None
    created_at: datetime

class CityDetailResponse(CityResponse):
    landmarks: list[dict] = []
    available_variants: list[dict] = []
```

`variant.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, time

class ActivityResponse(BaseModel):
    id: UUID
    place_id: UUID
    place_name: str
    place_address: str | None
    place_location: dict  # {lat, lng}
    place_rating: float | None
    place_photo_url: str | None
    place_types: list[str]
    place_opening_hours: list[dict] | None
    sequence: int
    start_time: time
    end_time: time
    duration_minutes: int
    category: str
    description: str | None
    is_meal: bool
    meal_type: str | None
    estimated_cost_usd: float | None

class RouteResponse(BaseModel):
    from_activity_sequence: int
    to_activity_sequence: int
    travel_mode: str
    distance_meters: int
    duration_seconds: int
    polyline: str | None

class DayPlanResponse(BaseModel):
    day_number: int
    theme: str
    theme_description: str | None
    activities: list[ActivityResponse]
    routes: list[RouteResponse]

class VariantSummary(BaseModel):
    id: UUID
    pace: str
    budget: str
    day_count: int
    quality_score: int | None
    cost_total: float | None
    status: str

class VariantDetailResponse(BaseModel):
    id: UUID
    city_id: UUID
    city_name: str
    pace: str
    budget: str
    day_count: int
    quality_score: int | None
    status: str
    accommodation: dict | None  # place details
    accommodation_alternatives: list[dict]
    booking_hint: str | None
    cost_breakdown: dict | None
    day_plans: list[DayPlanResponse]
```

`journey.py` (new, replaces old trip models):
```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from app.models.common import Pace, Budget

class JourneyRequest(BaseModel):
    destination: str = Field(min_length=1)
    origin: str | None = None
    start_date: date
    total_days: int = Field(ge=1, le=30)
    pace: Pace = Pace.MODERATE
    budget: Budget = Budget.MODERATE
    travelers: dict = Field(default_factory=lambda: {"adults": 2})

class CityAllocation(BaseModel):
    city_name: str
    country: str | None = None
    day_count: int
    order: int

class JourneyResponse(BaseModel):
    id: UUID
    destination: str
    origin: str | None
    start_date: date
    total_days: int
    pace: str
    budget: str
    travelers: dict
    status: str  # complete / generating / partial
    city_sequence: list[dict]
    transport_legs: list[dict] | None
    weather_forecasts: list[dict] | None
    cost_breakdown: dict | None
    created_at: datetime

class JourneySummary(BaseModel):
    id: UUID
    destination: str
    start_date: date
    total_days: int
    city_count: int
    status: str
    created_at: datetime
```

`job.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class JobStatus(BaseModel):
    id: UUID
    status: str  # queued / running / completed / failed
    progress_pct: int
    estimated_seconds_remaining: int | None = None
    result: dict | None = None
    error: str | None = None
```

`common.py` additions:
```python
class PopulationTier(str, Enum):
    MEGA = "mega"
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"

class VariantStatus(str, Enum):
    GENERATING = "generating"
    DRAFT = "draft"
    PUBLISHED = "published"
    STALE = "stale"
    ARCHIVED = "archived"
```

**Step 2: Commit**

```bash
git add backend/app/models/
git commit -m "feat: pydantic models for content library, journeys, jobs"
```

---

### Task 3: Repository Layer

**Files:**
- Create: `backend/app/db/repository.py` (replace existing)

**Step 1: Write failing tests**

Create `backend/tests/test_repository.py`:
```python
import pytest
from uuid import uuid4
from app.db.repository import CityRepository, VariantRepository, JourneyRepository, JobRepository

# Test CityRepository
async def test_create_city(db_session):
    repo = CityRepository(db_session)
    city = await repo.create(name="Tokyo", country="Japan", country_code="JP",
                              location={"lat": 35.6762, "lng": 139.6503},
                              timezone="Asia/Tokyo", currency="JPY",
                              population_tier="mega", region="East Asia")
    assert city.name == "Tokyo"
    assert city.id is not None

async def test_get_city_by_name(db_session):
    repo = CityRepository(db_session)
    await repo.create(name="Tokyo", country="Japan", country_code="JP",
                       location={"lat": 35.6762, "lng": 139.6503},
                       timezone="Asia/Tokyo", currency="JPY",
                       population_tier="mega", region="East Asia")
    city = await repo.get_by_name("Tokyo", "JP")
    assert city is not None
    assert city.name == "Tokyo"

async def test_list_cities(db_session):
    repo = CityRepository(db_session)
    await repo.create(name="Tokyo", country="Japan", country_code="JP",
                       location={"lat": 35.6762, "lng": 139.6503},
                       timezone="Asia/Tokyo", currency="JPY",
                       population_tier="mega", region="East Asia")
    cities, total = await repo.list(limit=10, offset=0)
    assert total == 1
    assert len(cities) == 1

# Test VariantRepository
async def test_lookup_variant(db_session):
    repo = VariantRepository(db_session)
    variant = await repo.lookup(city_id=uuid4(), pace="relaxed", budget="moderate", day_count=3)
    assert variant is None  # no variants yet

# Test JobRepository
async def test_create_and_pick_job(db_session):
    repo = JobRepository(db_session)
    job = await repo.create(job_type="batch_generate", city_id=None,
                             parameters={"pace": "relaxed"}, priority=5)
    assert job.status == "queued"
    picked = await repo.pick_next(worker_id="worker-1")
    assert picked is not None
    assert picked.id == job.id
    assert picked.status == "running"
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_repository.py -v
```
Expected: ImportError (repository module doesn't exist yet)

**Step 3: Implement repository**

Write `backend/app/db/repository.py` with these classes:
- `CityRepository` — CRUD, `get_by_name()`, `list()` with pagination/filtering
- `PlaceRepository` — `upsert_from_google()` (upsert by google_place_id), `get_by_city()`
- `VariantRepository` — `create()`, `lookup()` (by city+pace+budget+days+status=published), `update_status()`, `get_detail()` (with joined day_plans→activities→places, routes)
- `JourneyRepository` — CRUD, `list_by_user()`
- `JobRepository` — `create()`, `pick_next()` (SELECT FOR UPDATE SKIP LOCKED), `complete()`, `fail()`, `recover_stale()`

**Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_repository.py -v
```

**Step 5: Commit**

```bash
git add backend/app/db/repository.py backend/tests/test_repository.py
git commit -m "feat: repository layer with city, variant, journey, job CRUD"
```

---

### Task 4: Config Updates

**Files:**
- Modify: `backend/app/config/planning.py` — add batch pipeline constants
- Modify: `backend/app/config/settings.py` — no changes expected (reuse existing)

**Step 1: Add batch pipeline config**

Add to `planning.py`:
```python
# Batch pipeline
BATCH_MAX_ITERATIONS: int = 5
BATCH_MIN_SCORE: int = 80
BATCH_DISCOVERY_CANDIDATES: int = 150  # max candidates per city
DRAFT_DISCOVERY_CANDIDATES: int = 60

# Job queue
JOB_STALE_TIMEOUT_MINUTES: int = 15
JOB_POLL_INTERVAL_SECONDS: int = 5
WORKER_CONCURRENCY: int = 1  # jobs processed at a time

# Refresh
REFRESH_RATING_CHANGE_THRESHOLD: float = 0.3
REFRESH_REVIEW_CHANGE_THRESHOLD: int = 50
REFRESH_CANDIDATE_TURNOVER_THRESHOLD: float = 0.2  # 20%
```

**Step 2: Commit**

```bash
git add backend/app/config/planning.py
git commit -m "feat: batch pipeline and job queue config constants"
```

---

### Task 5: Dependencies Wiring

**Files:**
- Create: `backend/app/dependencies.py` (replace existing)

**Step 1: Write new dependency injection**

Wire up all services and repositories using FastAPI `Depends()`:

```python
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import Settings, get_settings
from app.db.engine import get_session
from app.db.repository import (
    CityRepository, PlaceRepository, VariantRepository,
    JourneyRepository, JobRepository,
)
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.google.directions import GoogleDirectionsService
from app.services.google.weather import GoogleWeatherService
from app.services.llm.factory import create_llm_service
from app.services.llm.base import LLMService
from app.core.http import get_http_client

async def get_db(settings: Settings = Depends(get_settings)) -> AsyncSession:
    async for session in get_session(settings):
        yield session

def get_city_repo(db: AsyncSession = Depends(get_db)) -> CityRepository:
    return CityRepository(db)

def get_place_repo(db: AsyncSession = Depends(get_db)) -> PlaceRepository:
    return PlaceRepository(db)

def get_variant_repo(db: AsyncSession = Depends(get_db)) -> VariantRepository:
    return VariantRepository(db)

def get_journey_repo(db: AsyncSession = Depends(get_db)) -> JourneyRepository:
    return JourneyRepository(db)

def get_job_repo(db: AsyncSession = Depends(get_db)) -> JobRepository:
    return JobRepository(db)

@lru_cache
def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return create_llm_service(settings)

# Google services — reuse existing pattern
def get_places_service(settings: Settings = Depends(get_settings)) -> GooglePlacesService:
    client = get_http_client()
    return GooglePlacesService(settings.google_places_api_key, client)

def get_routes_service(settings: Settings = Depends(get_settings)) -> GoogleRoutesService:
    client = get_http_client()
    return GoogleRoutesService(settings.google_routes_api_key, client)

def get_directions_service(settings: Settings = Depends(get_settings)) -> GoogleDirectionsService:
    client = get_http_client()
    return GoogleDirectionsService(settings.google_places_api_key, client)

def get_weather_service(settings: Settings = Depends(get_settings)) -> GoogleWeatherService:
    client = get_http_client()
    return GoogleWeatherService(settings.google_weather_api_key, client)

# Auth — reuse existing
from app.core.auth import decode_access_token
from app.db.repository import UserRepository

async def get_current_user(...):
    # same dual-auth pattern (Bearer header first, cookie fallback)
    ...

async def require_user(...):
    # raises 401 if no user
    ...
```

**Step 2: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "feat: dependency injection for content library services"
```

---

## Phase 2: Batch Generation Pipeline

### Task 6: Discovery Pipeline Step

**Files:**
- Create: `backend/app/pipelines/discovery.py`
- Create: `backend/tests/test_pipeline_discovery.py`

**Step 1: Write failing test**

```python
import pytest
from unittest.mock import AsyncMock
from app.pipelines.discovery import DiscoveryPipeline

async def test_discover_city_returns_candidates():
    places_service = AsyncMock()
    places_service.geocode.return_value = {
        "name": "Tokyo", "place_id": "xxx", "lat": 35.6762, "lng": 139.6503,
        "country": "Japan", "timezone": "Asia/Tokyo", "utc_offset_minutes": 540,
    }
    places_service.discover_places.return_value = [_mock_candidate("place1"), _mock_candidate("place2")]
    places_service.text_search_places.return_value = [_mock_candidate("place3")]
    places_service.search_lodging.return_value = _mock_candidate("hotel1", lodging=True)

    pipeline = DiscoveryPipeline(places_service)
    result = await pipeline.discover("Tokyo", interests=["cultural", "food"])

    assert result.city_metadata is not None
    assert result.city_metadata["country"] == "Japan"
    assert len(result.candidates) >= 2
    assert len(result.lodging_candidates) >= 1
    places_service.geocode.assert_called_once_with("Tokyo")
```

**Step 2: Run to verify failure**

```bash
cd backend && pytest tests/test_pipeline_discovery.py -v
```

**Step 3: Implement**

`discovery.py` wraps `GooglePlacesService` methods:
- `discover(city_name, interests)` → geocode + parallel searchNearby (per interest) + parallel searchText (4 queries) + lodging search
- Deduplicates by `google_place_id`
- Applies adaptive quality filters
- Separates lodging from activity candidates
- Returns `DiscoveryResult(city_metadata, candidates, lodging_candidates)`

Reuses: `GooglePlacesService.geocode`, `.discover_places`, `.text_search_places`, `.search_lodging`, `get_adaptive_place_filters()`

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add backend/app/pipelines/discovery.py backend/tests/test_pipeline_discovery.py
git commit -m "feat: discovery pipeline step — Google Places grounding"
```

---

### Task 7: Curation Pipeline Step (LLM)

**Files:**
- Create: `backend/app/pipelines/curation.py`
- Create: `backend/app/prompts/curation/curator_system.md`
- Create: `backend/app/prompts/curation/curator_user.md`
- Create: `backend/tests/test_pipeline_curation.py`

**Step 1: Write curation prompts**

`curator_system.md`:
```markdown
You are a travel curator. Given a list of Google-verified places for a city, create a multi-day travel plan.

RULES:
1. You may ONLY select activities from the provided candidate list. Reference each by its google_place_id.
2. Each day must have a theme (e.g., "Ancient Temples & Zen Gardens").
3. Place meals at culturally appropriate times for the destination country.
4. Activity count per day: relaxed=4-5, moderate=5-7, packed=7-9.
5. Include breakfast, lunch, and dinner each day from dining candidates.
6. Select 1 primary accommodation + 2 alternatives from lodging candidates.
7. Write a 1-2 sentence description for each activity, contextual to the day theme.
8. Estimate nightly accommodation cost in USD, calibrated to this city and budget tier.
9. Never include duplicate places across days.
10. Never include lodging-type places as activities.
```

`curator_user.md`:
```markdown
## City: {city_name}, {country}
## Trip: {day_count} days, {pace} pace, {budget} budget

{meal_time_guidance}

## Activity Candidates ({candidate_count} places):
{candidates_json}

## Lodging Candidates ({lodging_count} hotels):
{lodging_json}

Create a {day_count}-day plan selecting from the candidates above.
```

**Step 2: Write failing test**

```python
async def test_curate_returns_valid_plan():
    llm = MockLLMService()
    pipeline = CurationPipeline(llm)
    result = await pipeline.curate(
        city_name="Tokyo", country="Japan",
        candidates=[...], lodging_candidates=[...],
        pace="moderate", budget="moderate", day_count=3,
    )
    assert len(result.days) == 3
    assert result.accommodation is not None
    # All activity place_ids must be from candidates
    for day in result.days:
        for activity in day.activities:
            assert activity.google_place_id in candidate_ids
```

**Step 3: Implement**

`curation.py`:
- Loads prompts via `PromptLoader("curation")`
- Formats candidate list as compact JSON (google_place_id, name, types, rating, opening_hours)
- Calls `llm.generate_structured()` with Pydantic schema for structured output
- Validates: every returned `google_place_id` exists in the provided candidate set
- Rejects and retries (max 2) if validation fails
- Returns `CurationResult(days, accommodation, alternatives, booking_hint, cost_estimates)`

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add backend/app/pipelines/curation.py backend/app/prompts/curation/ backend/tests/test_pipeline_curation.py
git commit -m "feat: curation pipeline step — LLM selects from grounded candidates"
```

---

### Task 8: Routing Pipeline Step

**Files:**
- Create: `backend/app/pipelines/routing.py`
- Create: `backend/tests/test_pipeline_routing.py`

**Step 1: Write failing test**

```python
async def test_route_day_activities():
    routes_service = AsyncMock()
    routes_service.compute_route.return_value = Route(
        distance_meters=500, duration_seconds=360, travel_mode="WALK", polyline="abc"
    )
    pipeline = RoutingPipeline(routes_service)
    activities = [_activity(lat=35.0, lng=139.0), _activity(lat=35.01, lng=139.01)]
    result = await pipeline.route_day(activities, pace="moderate")
    assert len(result.routes) == 1
    assert result.routes[0].travel_mode == "WALK"
```

**Step 2: Implement**

`routing.py`:
- Takes list of activities (with locations) for a day
- Runs TSP optimization (reuses `RouteOptimizer` from `app/algorithms/tsp.py`)
- Computes route between each consecutive pair via `GoogleRoutesService.compute_best_route()`
- Walk/drive threshold is pace-aware (relaxed=25min, moderate=20min, packed=15min)
- Returns `RoutingResult(ordered_activities, routes)`

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/pipelines/routing.py backend/tests/test_pipeline_routing.py
git commit -m "feat: routing pipeline step — TSP + Google Routes"
```

---

### Task 9: Scheduling Pipeline Step

**Files:**
- Create: `backend/app/pipelines/scheduling.py`
- Create: `backend/tests/test_pipeline_scheduling.py`

**Step 1: Write failing test**

```python
async def test_schedule_day():
    pipeline = SchedulingPipeline()
    activities = [
        _activity(duration=60, category="cultural"),
        _activity(duration=45, category="dining", is_meal=True, meal_type="lunch"),
        _activity(duration=90, category="nature"),
    ]
    routes = [_route(duration_s=600), _route(duration_s=300)]
    result = pipeline.schedule_day(
        activities=activities, routes=routes,
        country="Japan", pace="moderate",
    )
    assert result[0].start_time is not None
    # Lunch should be in lunch window
    lunch = [a for a in result if a.meal_type == "lunch"][0]
    assert lunch.start_time >= time(11, 30)
    assert lunch.start_time <= time(14, 0)
```

**Step 2: Implement**

`scheduling.py`:
- Wraps `ScheduleBuilder` from `app/algorithms/scheduler.py`
- Uses `ScheduleConfig.for_region(country)` for culture-aware meal windows
- Applies pace multipliers from `PACE_CONFIGS`
- Enforces opening hours as hard constraints
- Returns activities with `start_time` and `end_time` populated

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/pipelines/scheduling.py backend/tests/test_pipeline_scheduling.py
git commit -m "feat: scheduling pipeline step — culture-aware time slots"
```

---

### Task 10: Review Pipeline Step

**Files:**
- Create: `backend/app/pipelines/review.py`
- Create: `backend/app/prompts/review/reviewer_system.md`
- Create: `backend/app/prompts/review/reviewer_user.md`
- Create: `backend/app/prompts/review/fixer_system.md`
- Create: `backend/app/prompts/review/fixer_user.md`
- Create: `backend/tests/test_pipeline_review.py`

**Step 1: Write failing test**

```python
async def test_review_scores_plan():
    llm = MockLLMService()
    pipeline = ReviewPipeline(llm)
    plan = _mock_plan(days=3, activities_per_day=6)
    result = await pipeline.review(plan, city_name="Tokyo", candidates=[...])
    assert result.score >= 0
    assert result.score <= 100
    assert isinstance(result.issues, list)

async def test_review_fix_loop():
    llm = MockLLMService()
    pipeline = ReviewPipeline(llm)
    plan = _mock_plan(days=3, activities_per_day=3)  # too few for moderate
    result = await pipeline.review_and_fix(
        plan, city_name="Tokyo", candidates=[...],
        max_iterations=2, min_score=80,
    )
    # Should attempt fixes (mock will return same plan, but logic is tested)
    assert result.best_score is not None
    assert result.iterations_used >= 1
```

**Step 2: Implement**

`review.py`:
- `review()`: calls LLM with reviewer prompts for 7-dimension scoring
- Also runs deterministic quality evaluators from `app/algorithms/quality/`
- Final score = weighted average of LLM score + deterministic score
- `fix()`: calls LLM fixer with issues + candidate pool, returns patched plan
- `review_and_fix()`: loop up to `max_iterations`, track best plan across iterations
- Reuses: quality evaluators, prompt loader

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/pipelines/review.py backend/app/prompts/review/ backend/tests/test_pipeline_review.py
git commit -m "feat: review pipeline step — LLM + deterministic quality scoring"
```

---

### Task 11: Costing Pipeline Step

**Files:**
- Create: `backend/app/pipelines/costing.py`
- Create: `backend/tests/test_pipeline_costing.py`

**Step 1: Write failing test**

```python
async def test_compute_costs():
    pipeline = CostingPipeline()
    plan = _mock_plan_with_accommodation(nightly_usd=150.0, days=3)
    result = pipeline.compute(plan)
    assert result.accommodation == 450.0  # 150 * 3
    assert result.total > 0
    assert "accommodation" in result.breakdown
    assert "dining" in result.breakdown
```

**Step 2: Implement**

`costing.py`:
- Deterministic computation from plan data:
  - Accommodation: nightly rate × days
  - Dining: sum of meal `estimated_cost_usd`
  - Activities: sum of non-meal `estimated_cost_usd`
  - Transport: mode-based estimate from route durations (walk=free, drive=~$0.50/km, transit=~$2-5/trip)
- Returns `CostBreakdown(accommodation, transport, dining, activities, total, per_day)`

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/pipelines/costing.py backend/tests/test_pipeline_costing.py
git commit -m "feat: costing pipeline step — deterministic cost breakdown"
```

---

### Task 12: Batch Pipeline Orchestrator

**Files:**
- Create: `backend/app/pipelines/batch.py`
- Create: `backend/tests/test_pipeline_batch.py`

**Step 1: Write failing test**

```python
async def test_batch_pipeline_full_run():
    """Integration test: batch pipeline produces a published variant."""
    batch = BatchPipeline(
        discovery=mock_discovery,
        curation=mock_curation,
        routing=mock_routing,
        scheduling=mock_scheduling,
        review=mock_review,
        costing=mock_costing,
        place_repo=mock_place_repo,
        variant_repo=mock_variant_repo,
    )
    result = await batch.generate(
        city_id=uuid4(), city_name="Tokyo", country="Japan",
        pace="relaxed", budget="moderate", day_count=3,
    )
    assert result.status in ("published", "draft")
    assert result.variant_id is not None
    assert result.quality_score is not None
```

**Step 2: Implement**

`batch.py` — `BatchPipeline` class:
1. Calls `DiscoveryPipeline.discover()` → upserts all candidates to `places` table
2. Calls `CurationPipeline.curate()` → raw plan with candidate references
3. Resolves candidate references to place IDs from DB
4. Calls `RoutingPipeline.route_day()` per day
5. Calls `SchedulingPipeline.schedule_day()` per day
6. Calls `ReviewPipeline.review_and_fix()` (max 5 iterations, min score 80)
7. Calls `CostingPipeline.compute()`
8. Stores variant + day_plans + activities + routes via repositories
9. Sets status to `published` if score ≥ 80, else `draft`
10. Reports progress via callback (for job queue progress_pct updates)

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/pipelines/batch.py backend/tests/test_pipeline_batch.py
git commit -m "feat: batch pipeline orchestrator — discover through store"
```

---

### Task 13: On-Demand Draft Pipeline

**Files:**
- Create: `backend/app/pipelines/draft.py`
- Create: `backend/tests/test_pipeline_draft.py`

**Step 1: Write failing test**

```python
async def test_draft_pipeline_single_pass():
    draft = DraftPipeline(discovery=..., curation=..., routing=..., scheduling=..., costing=..., ...)
    result = await draft.generate(
        city_name="Dubrovnik", country="Croatia",
        pace="moderate", budget="moderate", day_count=3,
    )
    assert result.status == "draft"
    assert result.variant_id is not None
```

**Step 2: Implement**

`draft.py` — same as batch but:
- Reduced discovery (60 candidates instead of 150)
- Single curation pass (no review/fix loop)
- Stores as `status='draft'`
- Queues an `upgrade_draft` job for the batch pipeline to replace later

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/pipelines/draft.py backend/tests/test_pipeline_draft.py
git commit -m "feat: on-demand draft pipeline — fast single-pass generation"
```

---

### Task 14: Job Queue Worker

**Files:**
- Create: `backend/app/worker/queue.py`
- Create: `backend/app/worker/runner.py`
- Create: `backend/tests/test_worker.py`

**Step 1: Write failing test**

```python
async def test_worker_picks_and_executes_job():
    job_repo = AsyncMock()
    job_repo.pick_next.return_value = _mock_job(job_type="batch_generate", parameters={"pace": "relaxed", "budget": "moderate", "day_count": 3})
    batch_pipeline = AsyncMock()
    batch_pipeline.generate.return_value = _mock_result(variant_id=uuid4(), status="published")

    worker = Worker(job_repo=job_repo, batch_pipeline=batch_pipeline, draft_pipeline=AsyncMock())
    await worker.process_one()

    job_repo.pick_next.assert_called_once()
    batch_pipeline.generate.assert_called_once()
    job_repo.complete.assert_called_once()

async def test_worker_handles_failure():
    job_repo = AsyncMock()
    job_repo.pick_next.return_value = _mock_job(job_type="batch_generate")
    batch_pipeline = AsyncMock()
    batch_pipeline.generate.side_effect = Exception("LLM timeout")

    worker = Worker(job_repo=job_repo, batch_pipeline=batch_pipeline, draft_pipeline=AsyncMock())
    await worker.process_one()

    job_repo.fail.assert_called_once()
```

**Step 2: Implement**

`queue.py` — thin wrapper around `JobRepository` with convenience methods.

`runner.py` — `Worker` class:
- `process_one()`: pick job → dispatch to correct pipeline → complete/fail
- `run_loop()`: poll every `JOB_POLL_INTERVAL_SECONDS`, process one job per iteration
- Dispatches: `batch_generate` → `BatchPipeline`, `on_demand` → `DraftPipeline`, `upgrade_draft` → `BatchPipeline`, `refresh` → `RefreshPipeline` (Task 20)
- Stale job recovery on startup

**Step 3: Write CLI entrypoint**

Create `backend/cli.py`:
```python
import asyncio
import click

@click.group()
def cli():
    pass

@cli.command()
@click.option("--city", required=True)
@click.option("--pace", default="moderate")
@click.option("--budget", default="moderate")
@click.option("--days", default=3, type=int)
def generate(city, pace, budget, days):
    """Queue a batch generation job for a city."""
    asyncio.run(_queue_generate(city, pace, budget, days))

@cli.command()
def worker():
    """Start the job queue worker."""
    asyncio.run(_run_worker())

if __name__ == "__main__":
    cli()
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add backend/app/worker/ backend/cli.py backend/tests/test_worker.py
git commit -m "feat: job queue worker + CLI for batch generation"
```

---

## Phase 3: API Layer

### Task 15: Cities Router (Browse Catalog)

**Files:**
- Create: `backend/app/routers/cities.py`
- Create: `backend/tests/test_api_cities.py`

**Step 1: Write failing test**

```python
async def test_list_cities(client):
    # Seed a city via repo
    response = await client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    assert "cities" in data
    assert "total" in data

async def test_get_city_detail(client, seeded_city):
    response = await client.get(f"/api/cities/{seeded_city.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Tokyo"
    assert "available_variants" in data

async def test_get_variant_detail(client, seeded_variant):
    response = await client.get(f"/api/cities/{seeded_variant.city_id}/variants/{seeded_variant.id}")
    assert response.status_code == 200
    data = response.json()
    assert "day_plans" in data
    assert len(data["day_plans"]) > 0
```

**Step 2: Implement router**

```python
from fastapi import APIRouter, Depends, Query
from app.dependencies import get_city_repo, get_variant_repo

router = APIRouter(prefix="/api/cities", tags=["cities"])

@router.get("")
async def list_cities(
    region: str | None = None,
    sort: str = "name",
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    city_repo: CityRepository = Depends(get_city_repo),
): ...

@router.get("/{city_id}")
async def get_city(city_id: UUID, city_repo=Depends(get_city_repo)): ...

@router.get("/{city_id}/variants")
async def list_variants(city_id: UUID, pace: str | None = None, budget: str | None = None, variant_repo=Depends(get_variant_repo)): ...

@router.get("/{city_id}/variants/{variant_id}")
async def get_variant_detail(city_id: UUID, variant_id: UUID, variant_repo=Depends(get_variant_repo)): ...
```

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/routers/cities.py backend/tests/test_api_cities.py
git commit -m "feat: cities catalog API — list, detail, variants"
```

---

### Task 16: Journey Assembler

**Files:**
- Create: `backend/app/assembler/allocator.py`
- Create: `backend/app/assembler/lookup.py`
- Create: `backend/app/assembler/connector.py`
- Create: `backend/app/assembler/assembler.py`
- Create: `backend/app/prompts/allocator/allocator_system.md`
- Create: `backend/app/prompts/allocator/allocator_user.md`
- Create: `backend/tests/test_assembler.py`

**Step 1: Write failing tests**

```python
async def test_allocator_splits_days():
    llm = MockLLMService()
    allocator = CityAllocator(llm)
    result = await allocator.allocate(
        destination="Japan", total_days=10, pace="relaxed", budget="moderate",
    )
    assert len(result) >= 2
    assert sum(c.day_count for c in result) == 10

async def test_lookup_finds_variants():
    variant_repo = AsyncMock()
    variant_repo.lookup.return_value = _mock_variant()
    lookup = VariantLookup(variant_repo)
    result = await lookup.find(city_id=uuid4(), pace="relaxed", budget="moderate", day_count=3)
    assert result.variant is not None
    assert result.needs_generation is False

async def test_assembler_full_flow():
    assembler = JourneyAssembler(allocator=..., lookup=..., connector=..., weather=...)
    journey = await assembler.assemble(
        JourneyRequest(destination="Japan", start_date=date(2026, 5, 1), total_days=10, ...)
    )
    assert journey.status in ("complete", "generating")
    assert len(journey.city_sequence) >= 2
```

**Step 2: Implement**

`allocator.py`:
- LLM call with structured output → `list[CityAllocation]`
- Validates: sum of days = total_days, at least 2 days per city
- Prompt: destination, total_days, pace, interests

`lookup.py`:
- `find(city_id, pace, budget, day_count)` → check for exact published variant
- Close-match: if we have 3d but need 4d, return the 3d with a flag
- No match: return `needs_generation=True`

`connector.py`:
- For each city pair: `GoogleDirectionsService.get_all_transport_options()`
- Parallel calls via `asyncio.gather`
- Returns `TransportLeg[]`

`assembler.py`:
- Orchestrates: allocate → lookup (parallel) → connect (parallel) → weather (parallel) → assemble
- If any city needs generation: create on-demand job, return `status="generating"`
- If all cached: return `status="complete"` with full journey

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/assembler/ backend/app/prompts/allocator/ backend/tests/test_assembler.py
git commit -m "feat: journey assembler — allocator, lookup, connector"
```

---

### Task 17: Journeys Router

**Files:**
- Create: `backend/app/routers/journeys.py`
- Create: `backend/tests/test_api_journeys.py`

**Step 1: Write failing tests**

```python
async def test_create_journey(client, seeded_variants):
    response = await client.post("/api/journeys", json={
        "destination": "Japan", "start_date": "2026-05-01",
        "total_days": 10, "pace": "relaxed", "budget": "moderate",
    }, headers={"X-Test-User": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("complete", "generating")

async def test_list_journeys(client):
    response = await client.get("/api/journeys", headers={"X-Test-User": "test"})
    assert response.status_code == 200

async def test_get_journey(client, seeded_journey):
    response = await client.get(f"/api/journeys/{seeded_journey.id}", headers={"X-Test-User": "test"})
    assert response.status_code == 200

async def test_journey_requires_auth(client):
    response = await client.get("/api/journeys")
    assert response.status_code == 401
```

**Step 2: Implement router**

```python
router = APIRouter(prefix="/api/journeys", tags=["journeys"])

@router.post("")
async def create_journey(
    request: JourneyRequest,
    user = Depends(require_user),
    assembler = Depends(get_assembler),
    journey_repo = Depends(get_journey_repo),
): ...

@router.get("")
async def list_journeys(user=Depends(require_user), repo=Depends(get_journey_repo)): ...

@router.get("/{journey_id}")
async def get_journey(journey_id: UUID, user=Depends(require_user), repo=Depends(get_journey_repo)): ...

@router.delete("/{journey_id}")
async def delete_journey(journey_id: UUID, user=Depends(require_user), repo=Depends(get_journey_repo)): ...
```

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/routers/journeys.py backend/tests/test_api_journeys.py
git commit -m "feat: journeys API — create, list, get, delete"
```

---

### Task 18: Jobs Router + Admin Router

**Files:**
- Create: `backend/app/routers/admin.py`
- Create: `backend/tests/test_api_admin.py`

**Step 1: Write failing tests**

```python
async def test_poll_job_status(client, seeded_job):
    response = await client.get(f"/api/jobs/{seeded_job.id}", headers={"X-Test-User": "test"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "progress_pct" in data

async def test_admin_add_city(client):
    response = await client.post("/api/admin/cities", json={"name": "Paris", "country": "France"},
                                  headers={"X-Test-User": "admin"})
    assert response.status_code == 200

async def test_admin_trigger_generate(client, seeded_city):
    response = await client.post(f"/api/admin/cities/{seeded_city.id}/generate",
                                  json={"pace": "relaxed", "budget": "moderate", "day_count": 3},
                                  headers={"X-Test-User": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
```

**Step 2: Implement**

- `GET /api/jobs/:id` — public (any authenticated user can poll their job)
- `POST /api/admin/cities` — geocode + create city record
- `POST /api/admin/cities/:id/generate` — create batch_generate job
- `POST /api/admin/cities/:id/refresh` — create refresh job
- `GET /api/admin/jobs` — list all jobs
- `GET /api/admin/stats` — counts

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_api_admin.py
git commit -m "feat: admin API — city management, job queue, stats"
```

---

### Task 19: Sharing + Export (adapted)

**Files:**
- Create: `backend/app/routers/sharing.py`
- Modify: `backend/app/routers/export.py` — adapt to new journey schema

**Step 1: Implement sharing**

Same pattern as current system:
- `POST /api/journeys/:id/share` → generate token, store in `journey_shares`
- `DELETE /api/journeys/:id/share` → revoke
- `GET /api/shared/:token` → get journey without auth

**Step 2: Adapt export**

PDF + calendar export need to read from the new schema (journeys → city_sequence → variant day_plans). The weasyprint rendering template needs updating to the new model structure.

**Step 3: Write tests**

```python
async def test_share_journey(client, seeded_journey):
    response = await client.post(f"/api/journeys/{seeded_journey.id}/share",
                                  headers={"X-Test-User": "test"})
    assert response.status_code == 200
    token = response.json()["token"]
    # Verify public access
    shared = await client.get(f"/api/shared/{token}")
    assert shared.status_code == 200
```

**Step 4: Commit**

```bash
git add backend/app/routers/sharing.py backend/app/routers/export.py backend/tests/test_api_sharing.py
git commit -m "feat: sharing + export adapted to journey schema"
```

---

### Task 20: Smart Refresh Pipeline

**Files:**
- Create: `backend/app/worker/refresh.py`
- Create: `backend/tests/test_refresh.py`

**Step 1: Write failing test**

```python
async def test_refresh_no_changes(seeded_city_with_places):
    """When discovery returns same places, no regeneration needed."""
    discovery = AsyncMock()
    discovery.discover.return_value = _same_candidates_as_stored()
    refresh = RefreshPipeline(discovery=discovery, city_repo=..., job_repo=...)
    result = await refresh.check_city(seeded_city_with_places.id)
    assert result.changed is False
    assert result.jobs_queued == 0

async def test_refresh_major_change(seeded_city_with_places):
    """When >20% candidates change, queue regeneration jobs."""
    discovery = AsyncMock()
    discovery.discover.return_value = _different_candidates()
    refresh = RefreshPipeline(discovery=discovery, city_repo=..., job_repo=...)
    result = await refresh.check_city(seeded_city_with_places.id)
    assert result.changed is True
    assert result.jobs_queued > 0
```

**Step 2: Implement**

`refresh.py`:
- `check_city(city_id)`: re-run discovery, compute hash, compare to stored
- Minor change (hours/rating) → update places in-place
- Major change (>20% turnover, closed places) → mark variants stale, queue regeneration
- `refresh_all()`: iterate all cities, call `check_city()` per city

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add backend/app/worker/refresh.py backend/tests/test_refresh.py
git commit -m "feat: smart refresh pipeline — diff detection + selective regeneration"
```

---

### Task 21: FastAPI App Assembly

**Files:**
- Modify: `backend/app/main.py` — new app setup with new routers

**Step 1: Write new main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import get_settings
from app.core.middleware import RequestTracingMiddleware
from app.routers import cities, journeys, admin, places, auth, export, sharing

app = FastAPI(title="RET — Content Platform", version="3.0.0")

settings = get_settings()

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list,
                   allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"],
                   allow_credentials=True)

app.include_router(cities.router)
app.include_router(journeys.router)
app.include_router(admin.router)
app.include_router(places.router)
app.include_router(auth.router)
app.include_router(export.router)
app.include_router(sharing.router)

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0"}

# API catch-all for 404
@app.api_route("/api/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def api_404(path: str):
    return JSONResponse(status_code=404, content={"detail": f"Not found: /api/{path}"})
```

**Step 2: Run full backend test suite**

```bash
cd backend && pytest -v
```

**Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: FastAPI app assembly with all new routers"
```

---

## Phase 4: Frontend

### Task 22: Frontend Scaffolding + API Client

**Files:**
- Create: `frontend/src/lib/api.ts` (replace existing)
- Create: `frontend/src/stores/catalogStore.ts`
- Create: `frontend/src/stores/journeyStore.ts`
- Modify: `frontend/src/stores/uiStore.ts`
- Keep: `frontend/src/stores/authStore.ts` (unchanged)

**Step 1: Write new API client**

```typescript
// api.ts — new endpoints
const BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function listCities(params?: { region?: string; sort?: string; limit?: number; offset?: number }) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  const res = await fetch(`${BASE}/api/cities?${qs}`, { headers: getAuthHeaders() });
  return handle(res);
}

export async function getCity(cityId: string) { ... }
export async function getCityVariants(cityId: string, params?: { pace?: string; budget?: string }) { ... }
export async function getVariantDetail(cityId: string, variantId: string) { ... }

export async function createJourney(request: JourneyRequest) { ... }
export async function getJourney(journeyId: string) { ... }
export async function listJourneys() { ... }
export async function deleteJourney(journeyId: string) { ... }

export async function pollJob(jobId: string) { ... }

export async function shareJourney(journeyId: string) { ... }
export async function revokeShare(journeyId: string) { ... }
export async function getSharedJourney(token: string) { ... }

// Keep: photoUrl, getAuthHeaders, getMe, logout
```

**Step 2: Write stores**

`catalogStore.ts`:
```typescript
interface CatalogStore {
  cities: City[];
  selectedCity: CityDetail | null;
  selectedVariant: VariantDetail | null;
  loading: boolean;
  fetchCities: (params?) => Promise<void>;
  fetchCity: (id: string) => Promise<void>;
  fetchVariant: (cityId: string, variantId: string) => Promise<void>;
}
```

`journeyStore.ts`:
```typescript
interface JourneyStore {
  journeys: JourneySummary[];
  currentJourney: JourneyResponse | null;
  creating: boolean;
  jobId: string | null;
  createJourney: (request: JourneyRequest) => Promise<void>;
  pollUntilComplete: (jobId: string) => Promise<void>;
  fetchJourney: (id: string) => Promise<void>;
  fetchJourneys: () => Promise<void>;
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/stores/
git commit -m "feat: frontend API client + catalog/journey stores"
```

---

### Task 23: City Catalog Page

**Files:**
- Create: `frontend/src/pages/CityCatalog.tsx`
- Create: `frontend/src/components/CityGridCard.tsx`

**Step 1: Implement**

`CityCatalog.tsx`:
- Grid of city cards with search bar + region filter dropdown
- Fetches from `catalogStore.fetchCities()`
- Cards show: hero photo (from first landmark), city name, country, "X-day plans"
- Click → navigates to `/cities/:id`

`CityGridCard.tsx`:
- Reuse photo-first card design (hero banner with gradient overlay)
- City name, country, variant count badge
- Staggered entry animation (reuse existing CSS `.animate-stagger-in`)

**Step 2: Commit**

```bash
git add frontend/src/pages/CityCatalog.tsx frontend/src/components/CityGridCard.tsx
git commit -m "feat: city catalog page — grid with search and filter"
```

---

### Task 24: City Detail + Variant Picker

**Files:**
- Create: `frontend/src/pages/CityDetail.tsx`
- Create: `frontend/src/components/VariantPicker.tsx`

**Step 1: Implement**

`CityDetail.tsx`:
- Hero image header (reuse destination hero pattern)
- Map with landmark pins
- Landmark list
- Variant picker component
- "View Full Plan" button → navigates to plan view

`VariantPicker.tsx`:
- 3-column layout: relaxed / moderate / packed
- Each column shows: day count, activity count per day, total cost estimate
- Highlight available variants, gray out unavailable
- Click selects → loads variant preview

**Step 2: Commit**

```bash
git add frontend/src/pages/CityDetail.tsx frontend/src/components/VariantPicker.tsx
git commit -m "feat: city detail page with variant picker"
```

---

### Task 25: Plan View Page (shared between browse + journey)

**Files:**
- Create: `frontend/src/pages/PlanView.tsx`
- Reuse/adapt: `frontend/src/components/trip/DayTimeline.tsx`
- Create: `frontend/src/components/ActivityCard.tsx` (simplified from current)

**Step 1: Implement**

`PlanView.tsx`:
- Day tabs (same swipe navigation on mobile)
- Day timeline with activities (photo-first cards)
- Map with route polylines for selected day
- Cost breakdown panel
- Weather badge per day (if weather data available)

Reuse:
- Activity card layout (hero photo, gradient overlay, name, duration, category badge)
- Weather atmosphere gradients
- Budget breakdown bar chart
- Dark mode styles

**Step 2: Commit**

```bash
git add frontend/src/pages/PlanView.tsx frontend/src/components/ActivityCard.tsx
git commit -m "feat: plan view page — day timeline, activity cards, map"
```

---

### Task 26: Trip Wizard + Loading Screen

**Files:**
- Create: `frontend/src/pages/TripWizard.tsx` (simplified from current WizardForm)
- Create: `frontend/src/components/LoadingScreen.tsx`

**Step 1: Implement**

`TripWizard.tsx`:
- Fields: destination, origin, start date, total days, pace (3 buttons), budget (3 buttons), travelers
- Submit → `journeyStore.createJourney()`
- On success with `status="complete"` → navigate to `/journeys/:id`
- On `status="generating"` → show LoadingScreen

`LoadingScreen.tsx`:
- Simple centered spinner with text: "Preparing your trip..."
- Progress bar driven by `pollJob()` every 3 seconds
- On completion → navigate to journey dashboard

**Step 2: Commit**

```bash
git add frontend/src/pages/TripWizard.tsx frontend/src/components/LoadingScreen.tsx
git commit -m "feat: trip wizard + loading screen with job polling"
```

---

### Task 27: Journey Dashboard

**Files:**
- Create: `frontend/src/pages/JourneyDashboard.tsx`
- Create: `frontend/src/components/TransportLeg.tsx`

**Step 1: Implement**

`JourneyDashboard.tsx`:
- Vertical city sequence: city cards connected by transport leg indicators
- Each city card: name, days, accommodation, cost, hero photo
- Click city → expands to show day plans (reuses PlanView components)
- Total cost breakdown at bottom
- Weather forecasts per city
- Share + export buttons in header

`TransportLeg.tsx`:
- Between city cards: mode icon (train/bus/flight), duration, fare if available
- Compact inline design

**Step 2: Commit**

```bash
git add frontend/src/pages/JourneyDashboard.tsx frontend/src/components/TransportLeg.tsx
git commit -m "feat: journey dashboard — city sequence + transport legs"
```

---

### Task 28: App Router + Navigation

**Files:**
- Modify: `frontend/src/App.tsx` — new route structure
- Modify: `frontend/src/components/layout/Header.tsx` — new nav items

**Step 1: Implement new routes**

```typescript
<Routes>
  <Route path="/" element={<Home />} />
  <Route path="/cities" element={<CityCatalog />} />
  <Route path="/cities/:cityId" element={<CityDetail />} />
  <Route path="/cities/:cityId/plans/:variantId" element={<PlanView />} />
  <Route path="/plan" element={<TripWizard />} />
  <Route path="/journeys" element={<SavedJourneys />} />
  <Route path="/journeys/:journeyId" element={<JourneyDashboard />} />
  <Route path="/shared/:token" element={<SharedJourney />} />
  <Route path="/signin" element={<SignIn />} />
</Routes>
```

Header navigation:
- "Explore Cities" → `/cities`
- "Plan a Trip" → `/plan`
- "My Trips" → `/journeys` (auth required)

**Step 2: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/layout/Header.tsx
git commit -m "feat: app routing + navigation for content platform"
```

---

### Task 29: Saved Journeys + Shared Journey Pages

**Files:**
- Create: `frontend/src/pages/SavedJourneys.tsx`
- Create: `frontend/src/pages/SharedJourney.tsx`

**Step 1: Implement**

`SavedJourneys.tsx`:
- Grid of journey summary cards
- Each card: destination, dates, city count, total cost
- Click → navigate to `/journeys/:id`
- Delete button with confirmation

`SharedJourney.tsx`:
- Same as JourneyDashboard but read-only, no auth required
- Fetches via `getSharedJourney(token)`

**Step 2: Commit**

```bash
git add frontend/src/pages/SavedJourneys.tsx frontend/src/pages/SharedJourney.tsx
git commit -m "feat: saved journeys list + shared journey view"
```

---

## Phase 5: Content Generation + Polish

### Task 30: Generate Initial City Content

**Step 1: Start backend + worker**

```bash
# Terminal 1: API server
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2: Worker
cd backend && source venv/bin/activate && python cli.py worker
```

**Step 2: Add cities and queue generation**

```bash
# Add 20-30 cities
python cli.py generate --city "Tokyo" --pace relaxed --budget moderate --days 3
python cli.py generate --city "Tokyo" --pace moderate --budget moderate --days 3
python cli.py generate --city "Tokyo" --pace packed --budget moderate --days 3
python cli.py generate --city "Paris" --pace relaxed --budget moderate --days 3
# ... repeat for initial city set
```

Initial city list (20 cities):
Tokyo, Paris, Rome, Barcelona, London, New York, Bangkok, Istanbul, Dubai, Singapore,
Kyoto, Amsterdam, Prague, Lisbon, Seoul, Bali, Florence, Vienna, Marrakech, Sydney

**Step 3: Monitor generation**

```bash
curl http://localhost:8000/api/admin/stats | python3 -m json.tool
```

**Step 4: Verify quality**

```bash
# Check a generated variant
curl http://localhost:8000/api/cities | python3 -m json.tool
# Pick a city ID, check its variants
curl http://localhost:8000/api/cities/{id}/variants | python3 -m json.tool
```

**Step 5: Commit any prompt/config tweaks discovered during generation**

---

### Task 31: Frontend Polish

**Files:** Various frontend files

**Step 1: Dark mode**

Apply deep navy tones from existing CSS:
- Surface: `#0f1219`
- Reuse existing dark mode variables and patterns

**Step 2: Animations**

Reuse existing CSS from current app:
- `.animate-stagger-in .stagger-1..8` for city grid cards
- `.scroll-reveal` for scroll-triggered entrance
- Weather atmosphere gradients

**Step 3: Responsive design**

- Mobile-first layouts for all pages
- City catalog: 1 col → 2 col → 3 col grid
- Plan view: swipe navigation between days on mobile

**Step 4: Error states + empty states**

- Empty city catalog: "No cities available yet"
- Empty journeys: "Plan your first trip" with CTA
- Error boundary: reuse existing pattern

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: frontend polish — dark mode, animations, responsive, error states"
```

---

### Task 32: Frontend Build Check + Final Integration Test

**Step 1: Frontend build**

```bash
cd frontend && npm run build
```
Expected: clean build with no TypeScript errors.

**Step 2: Lint**

```bash
cd frontend && npm run lint
```

**Step 3: Full backend test suite**

```bash
cd backend && pytest -v
```

**Step 4: Manual smoke test**

1. Browse cities catalog → click a city → view variant → see day plans
2. Plan a trip → loading screen → journey dashboard with city plans
3. Share a journey → open shared link in incognito
4. Export PDF

**Step 5: Commit any fixes**

---

### Task 33: Update CLAUDE.md + Cleanup

**Files:**
- Modify: `CLAUDE.md` — document new architecture
- Delete: old orchestrator/agent files no longer used

**Step 1: Update CLAUDE.md**

Replace the architecture section to reflect:
- Content library model
- 4 pipelines (batch, draft, assembler, refresh)
- New project structure (pipelines/, assembler/, worker/)
- New API endpoints
- Dropped features (chat, tips, SSE)
- Worker CLI commands

**Step 2: Remove dead code**

Delete files that are fully replaced:
- `backend/app/orchestrators/` (replaced by `pipelines/` and `assembler/`)
- `backend/app/agents/` (replaced by `pipelines/curation.py` and `pipelines/review.py`)
- Old prompt files in `backend/app/prompts/journey/`, `day_plan/`, `chat/`, `tips/`
- `backend/app/services/chat.py`, `backend/app/services/tips.py`
- Old test files for replaced features

Keep the `app/services/google/` and `app/services/llm/` directories intact.

**Step 3: Commit**

```bash
git add -A
git commit -m "docs: update CLAUDE.md for content-first architecture + remove dead code"
```

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| 1: Backend Foundation | 1-5 | DB schema, models, repository, config, DI |
| 2: Batch Pipeline | 6-14 | Discovery → Curation → Routing → Scheduling → Review → Costing → Batch → Draft → Worker |
| 3: API Layer | 15-21 | Cities, Journeys, Admin, Sharing, Export, Refresh, App assembly |
| 4: Frontend | 22-29 | API client, stores, catalog, city detail, plan view, wizard, dashboard, routing |
| 5: Polish | 30-33 | Content generation, dark mode, animations, tests, CLAUDE.md |

**Total: 33 tasks across 5 phases.**

Each phase builds on the previous — Phase 1 is pure infrastructure, Phase 2 is the core pipeline (can be tested via CLI), Phase 3 exposes it via API, Phase 4 is the user-facing frontend, Phase 5 is content + polish.
