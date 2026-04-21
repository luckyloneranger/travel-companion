"""FastAPI dependency injection wiring for content library platform."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.auth import decode_access_token
from app.core.http import get_http_client
from app.db.engine import get_session
from app.db.repository import (
    CityRepository,
    DayPlanRepository,
    JobRepository,
    JourneyRepository,
    JourneyShareRepository,
    PlaceRepository,
    UserRepository,
    VariantRepository,
)
from app.services.google.directions import GoogleDirectionsService
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.google.weather import GoogleWeatherService
from app.services.llm.base import LLMService
from app.services.llm.factory import create_llm_service


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

async def get_db(settings: Settings = Depends(get_settings)):
    """Yield an async DB session."""
    async for session in get_session(settings):
        yield session


# ---------------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------------

def get_city_repo(db: AsyncSession = Depends(get_db)) -> CityRepository:
    return CityRepository(db)


def get_place_repo(db: AsyncSession = Depends(get_db)) -> PlaceRepository:
    return PlaceRepository(db)


def get_variant_repo(db: AsyncSession = Depends(get_db)) -> VariantRepository:
    return VariantRepository(db)


def get_day_plan_repo(db: AsyncSession = Depends(get_db)) -> DayPlanRepository:
    return DayPlanRepository(db)


def get_journey_repo(db: AsyncSession = Depends(get_db)) -> JourneyRepository:
    return JourneyRepository(db)


def get_job_repo(db: AsyncSession = Depends(get_db)) -> JobRepository:
    return JobRepository(db)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_share_repo(db: AsyncSession = Depends(get_db)) -> JourneyShareRepository:
    return JourneyShareRepository(db)


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

async def _get_http():
    """Resolve the shared HTTP client."""
    return await get_http_client()


def get_llm_service() -> LLMService:
    """Create an LLM service from current settings."""
    settings = get_settings()
    return create_llm_service(settings)


def get_places_service(
    settings: Settings = Depends(get_settings),
    http=Depends(_get_http),
) -> GooglePlacesService:
    return GooglePlacesService(settings.google_places_api_key, http)


def get_routes_service(
    settings: Settings = Depends(get_settings),
    http=Depends(_get_http),
) -> GoogleRoutesService:
    return GoogleRoutesService(settings.google_routes_api_key, http)


def get_directions_service(
    settings: Settings = Depends(get_settings),
    http=Depends(_get_http),
) -> GoogleDirectionsService:
    return GoogleDirectionsService(settings.google_places_api_key, http)


def get_weather_service(
    settings: Settings = Depends(get_settings),
    http=Depends(_get_http),
) -> GoogleWeatherService:
    return GoogleWeatherService(settings.google_weather_api_key, http)


# ---------------------------------------------------------------------------
# Authentication (dual: Bearer header first, cookie fallback)
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> dict | None:
    """Extract current user from Bearer header or JWT cookie.

    Checks Authorization header first (for cross-origin / mobile clients),
    then falls back to httpOnly cookie (for same-origin web).
    """
    # Check Bearer header first (mobile / cross-origin)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return decode_access_token(token)

    # Fall back to cookie (web / same-origin)
    token = request.cookies.get("access_token")
    if not token:
        return None
    return decode_access_token(token)


async def require_user(user: dict | None = Depends(get_current_user)) -> dict:
    """Require authentication. Raises 401 if not logged in."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
