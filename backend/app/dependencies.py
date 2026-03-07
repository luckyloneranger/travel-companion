from fastapi import Depends, HTTPException, Request

from app.config import Settings
from app.config.settings import get_settings as _get_settings
from app.core.http import get_http_client
from app.db.engine import get_session as _get_db_session
from app.db.repository import TripRepository
from app.orchestrators.day_plan import DayPlanOrchestrator
from app.orchestrators.journey import JourneyOrchestrator
from app.services.chat import ChatService
from app.services.google.directions import GoogleDirectionsService
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.google.weather import GoogleWeatherService
from app.services.llm.base import LLMService
from app.services.llm.factory import create_llm_service
from app.services.tips import TipsService
from app.agents.day_fixer import DayFixerAgent
from app.agents.day_reviewer import DayReviewerAgent
from app.agents.day_scout import DayScoutAgent
from app.agents.enricher import EnricherAgent


def get_settings() -> Settings:
    return _get_settings()


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return create_llm_service(settings)


async def get_http():
    return await get_http_client()


def get_places_service(
    settings: Settings = Depends(get_settings), http=Depends(get_http)
) -> GooglePlacesService:
    return GooglePlacesService(settings.google_places_api_key, http)


def get_routes_service(
    settings: Settings = Depends(get_settings), http=Depends(get_http)
) -> GoogleRoutesService:
    return GoogleRoutesService(settings.google_routes_api_key, http)


def get_directions_service(
    settings: Settings = Depends(get_settings), http=Depends(get_http)
) -> GoogleDirectionsService:
    return GoogleDirectionsService(settings.google_places_api_key, http)


def get_weather_service(
    settings: Settings = Depends(get_settings), http=Depends(get_http)
) -> GoogleWeatherService:
    return GoogleWeatherService(settings.google_weather_api_key, http)


def get_journey_orchestrator(
    llm=Depends(get_llm_service),
    places=Depends(get_places_service),
    routes=Depends(get_routes_service),
    directions=Depends(get_directions_service),
) -> JourneyOrchestrator:
    return JourneyOrchestrator(llm, places, routes, directions)


def get_day_scout(llm: LLMService = Depends(get_llm_service)) -> DayScoutAgent:
    return DayScoutAgent(llm)


def get_day_reviewer(llm: LLMService = Depends(get_llm_service)) -> DayReviewerAgent:
    return DayReviewerAgent(llm)


def get_day_fixer(llm: LLMService = Depends(get_llm_service)) -> DayFixerAgent:
    return DayFixerAgent(llm)


def get_day_plan_orchestrator(
    llm=Depends(get_llm_service),
    places=Depends(get_places_service),
    routes=Depends(get_routes_service),
    directions=Depends(get_directions_service),
    weather=Depends(get_weather_service),
    day_scout: DayScoutAgent = Depends(get_day_scout),
    day_reviewer: DayReviewerAgent = Depends(get_day_reviewer),
    day_fixer: DayFixerAgent = Depends(get_day_fixer),
) -> DayPlanOrchestrator:
    return DayPlanOrchestrator(
        llm=llm, places=places, routes=routes,
        directions=directions, weather=weather,
        day_scout=day_scout, day_reviewer=day_reviewer, day_fixer=day_fixer,
    )


def get_chat_service(
    llm=Depends(get_llm_service),
    places=Depends(get_places_service),
) -> ChatService:
    return ChatService(llm, places)


def get_tips_service(llm=Depends(get_llm_service)) -> TipsService:
    return TipsService(llm)


def get_enricher(
    places=Depends(get_places_service),
    routes=Depends(get_routes_service),
    directions=Depends(get_directions_service),
) -> EnricherAgent:
    return EnricherAgent(places, routes, directions)


async def get_db_session(settings: Settings = Depends(_get_settings)):
    async for session in _get_db_session(settings):
        yield session


async def get_trip_repository(session=Depends(get_db_session)):
    yield TripRepository(session)


async def get_current_user(request: Request) -> dict | None:
    """Extract current user from Bearer header or JWT cookie.

    Checks Authorization header first (for cross-origin / mobile clients),
    then falls back to httpOnly cookie (for same-origin web).
    """
    from app.core.auth import decode_access_token

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


async def require_user(request: Request) -> dict:
    """Require authentication. Raises 401 if not logged in."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user
