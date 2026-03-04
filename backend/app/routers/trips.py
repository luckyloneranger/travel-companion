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
)
from app.models.chat import ChatEditRequest, ChatEditResponse
from app.models.trip import TripRequest, TripResponse, TripSummary
from app.orchestrators.day_plan import DayPlanOrchestrator
from app.orchestrators.journey import JourneyOrchestrator
from app.services.chat import ChatService
from app.services.tips import TipsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trips", tags=["trips"])


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
):
    """Stream day plan generation for a saved trip."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")

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
) -> ChatEditResponse:
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")

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
async def get_trip(trip_id: str, repo: TripRepository = Depends(get_trip_repository)) -> TripResponse:
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    return trip


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, repo: TripRepository = Depends(get_trip_repository)):
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
):
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    return await tips_service.generate_tips(activities, trip.request.destination)
