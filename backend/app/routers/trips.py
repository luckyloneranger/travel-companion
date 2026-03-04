import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.db.repository import TripRepository
from app.dependencies import (
    get_chat_service,
    get_current_user,
    get_day_plan_orchestrator,
    get_journey_orchestrator,
    get_tips_service,
    get_trip_repository,
    require_user,
)
from app.models.chat import ChatEditRequest, ChatEditResponse
from app.models.trip import TripRequest, TripResponse, TripSummary
from app.orchestrators.day_plan import DayPlanOrchestrator
from app.orchestrators.journey import JourneyOrchestrator
from app.services.chat import ChatService
from app.services.tips import TipsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trips", tags=["trips"])


def _compute_cost_breakdown(trip: TripResponse) -> dict[str, float] | None:
    """Compute cost breakdown from day plans, accommodation, and transport."""
    dining = activities_cost = 0.0
    dining_categories = {"restaurant", "cafe", "bakery", "food", "dining", "bar",
                         "french_restaurant", "italian_restaurant", "sushi_restaurant",
                         "tea_house", "bistro", "falafel_restaurant"}

    if trip.day_plans:
        for dp in trip.day_plans:
            for a in dp.activities:
                if a.estimated_cost_usd:
                    cat = (a.place.category or "").lower()
                    if cat in dining_categories or "restaurant" in cat or "cafe" in cat:
                        dining += a.estimated_cost_usd
                    else:
                        activities_cost += a.estimated_cost_usd

    # Accommodation costs
    accommodation = 0.0
    for city in trip.journey.cities:
        if city.accommodation and city.accommodation.estimated_nightly_usd:
            accommodation += city.accommodation.estimated_nightly_usd * city.days

    # Transport costs
    transport = 0.0
    for leg in trip.journey.travel_legs:
        if leg.fare_usd:
            transport += leg.fare_usd

    total = dining + activities_cost + accommodation + transport
    if total == 0:
        return None

    result = {
        "accommodation_usd": round(accommodation, 2),
        "transport_usd": round(transport, 2),
        "activities_usd": round(activities_cost, 2),
        "dining_usd": round(dining, 2),
        "total_usd": round(total, 2),
    }
    if trip.request.budget_usd:
        result["budget_usd"] = trip.request.budget_usd
        result["budget_remaining_usd"] = round(trip.request.budget_usd - total, 2)
    return result


async def _check_trip_ownership(repo: TripRepository, trip_id: str, user_id: str):
    """Verify the user owns the trip. Allows access to ownerless legacy trips."""
    owner = await repo.get_trip_user_id(trip_id)
    if owner is not None and owner != user_id:
        raise HTTPException(404, "Trip not found")


@router.post("/plan/stream")
async def plan_trip_stream(
    request: TripRequest,
    orchestrator: JourneyOrchestrator = Depends(get_journey_orchestrator),
    repo: TripRepository = Depends(get_trip_repository),
    user: dict | None = Depends(get_current_user),
):
    """Stream journey planning via SSE."""

    async def event_generator():
        try:
            async for event in orchestrator.plan_stream(request):
                if event.phase == "complete" and event.data:
                    # Save to DB
                    from app.models.journey import JourneyPlan

                    journey = JourneyPlan.model_validate(event.data)
                    user_id = user["sub"] if user else None
                    trip_id = await repo.save_trip(request, journey, user_id=user_id)
                    event.data["trip_id"] = trip_id
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Stream error")
            error_data = json.dumps({"phase": "error", "message": str(e), "progress": 0})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{trip_id}/days/stream")
async def generate_day_plans_stream(
    trip_id: str,
    orchestrator: DayPlanOrchestrator = Depends(get_day_plan_orchestrator),
    repo: TripRepository = Depends(get_trip_repository),
    user: dict | None = Depends(get_current_user),
):
    """Stream day plan generation for a saved trip."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    if user:
        await _check_trip_ownership(repo, trip_id, user["sub"])

    async def event_generator():
        try:
            async for event in orchestrator.generate_stream(trip.journey, trip.request):
                if event.phase == "complete" and event.data:
                    from app.models.day_plan import DayPlan

                    day_plans = [DayPlan.model_validate(dp) for dp in event.data.get("day_plans", [])]
                    await repo.update_day_plans(trip_id, day_plans)
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Day plan stream error")
            error_data = json.dumps({"phase": "error", "message": str(e), "progress": 0})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{trip_id}/chat")
async def chat_edit(
    trip_id: str,
    request: ChatEditRequest,
    chat: ChatService = Depends(get_chat_service),
    repo: TripRepository = Depends(get_trip_repository),
    user: dict | None = Depends(get_current_user),
) -> ChatEditResponse:
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    if user:
        await _check_trip_ownership(repo, trip_id, user["sub"])

    if request.context == "day_plans" and trip.day_plans:
        response = await chat.edit_day_plans(request.message, trip.day_plans, trip.journey, trip.request)
        if response.updated_day_plans:
            await repo.update_day_plans(trip_id, response.updated_day_plans)
    else:
        response = await chat.edit_journey(request.message, trip.journey, trip.request)
        if response.updated_journey:
            await repo.update_journey(trip_id, response.updated_journey)

    return response


@router.get("")
async def list_trips(
    repo: TripRepository = Depends(get_trip_repository),
    user: dict | None = Depends(get_current_user),
) -> list[TripSummary]:
    user_id = user["sub"] if user else None
    return await repo.list_trips(user_id=user_id)


@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict | None = Depends(get_current_user),
) -> TripResponse:
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    owner = await repo.get_trip_user_id(trip_id)
    # Allow if: no owner (legacy), user is owner, or trip is shared
    if owner is not None and (not user or owner != user.get("sub")):
        share_token = await repo.get_share_token(trip_id)
        if not share_token:
            raise HTTPException(404, "Trip not found")
    trip.cost_breakdown = _compute_cost_breakdown(trip)
    return trip


@router.delete("/{trip_id}")
async def delete_trip(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    await _check_trip_ownership(repo, trip_id, user["sub"])
    deleted = await repo.delete_trip(trip_id)
    if not deleted:
        raise HTTPException(404, "Trip not found")
    return {"status": "deleted"}


@router.post("/{trip_id}/tips")
async def generate_tips(
    trip_id: str,
    activities: list[dict],
    tips_service: TipsService = Depends(get_tips_service),
    repo: TripRepository = Depends(get_trip_repository),
    user: dict | None = Depends(get_current_user),
):
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    if user:
        await _check_trip_ownership(repo, trip_id, user["sub"])
    return await tips_service.generate_tips(activities, trip.request.destination)


@router.post("/{trip_id}/share")
async def share_trip(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    """Create a shareable link for a trip."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    await _check_trip_ownership(repo, trip_id, user["sub"])

    # Check if already shared
    existing = await repo.get_share_token(trip_id)
    if existing:
        return {"token": existing, "url": f"/shared/{existing}"}

    token = await repo.create_share(trip_id)
    return {"token": token, "url": f"/shared/{token}"}


@router.delete("/{trip_id}/share")
async def unshare_trip(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    """Revoke sharing for a trip."""
    await _check_trip_ownership(repo, trip_id, user["sub"])
    deleted = await repo.delete_share(trip_id)
    if not deleted:
        raise HTTPException(404, "No share found")
    return {"status": "unshared"}


# ── Shared trip access (no auth required) ─────────────────────────────

shared_router = APIRouter(tags=["shared"])


@shared_router.get("/api/shared/{token}")
async def get_shared_trip(
    token: str,
    repo: TripRepository = Depends(get_trip_repository),
):
    """Get a shared trip by its token. No auth required."""
    trip = await repo.get_trip_by_share_token(token)
    if not trip:
        raise HTTPException(404, "Shared trip not found")
    trip.cost_breakdown = _compute_cost_breakdown(trip)
    return trip
