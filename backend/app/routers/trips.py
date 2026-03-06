import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db.repository import TripRepository
from app.dependencies import (
    get_chat_service,
    get_day_plan_orchestrator,
    get_enricher,
    get_journey_orchestrator,
    get_tips_service,
    get_trip_repository,
    require_user,
)
from app.models.chat import ChatEditRequest, ChatEditResponse
from app.models.journey import JourneyPlan
from app.models.trip import TripRequest, TripResponse, TripSummary
from app.agents.enricher import EnricherAgent
from app.core.rate_limit import get_plan_limiter, get_day_plan_limiter, get_chat_limiter, get_tips_limiter
from app.services.llm.exceptions import LLMValidationError
from app.orchestrators.day_plan import DayPlanOrchestrator
from app.orchestrators.journey import JourneyOrchestrator
from app.services.chat import ChatService
from app.services.tips import TipsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trips", tags=["trips"])


def _compute_cost_breakdown(trip: TripResponse) -> dict[str, float] | None:
    """Compute cost breakdown from day plans, accommodation, and transport."""
    dining = activities_cost = 0.0
    # Detect dining by substring rather than exact match — catches all
    # regional cuisine types (french_restaurant, sushi_restaurant, etc.)
    _DINING_SUBSTRINGS = ("restaurant", "cafe", "food", "bakery", "bar",
                          "dining", "bistro", "brasserie", "tavern", "pub")

    if trip.day_plans:
        for dp in trip.day_plans:
            for a in dp.activities:
                if a.estimated_cost_usd:
                    cat = (a.place.category or "").lower()
                    if any(s in cat for s in _DINING_SUBSTRINGS):
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

    # Clamp negative values to 0
    dining = max(0.0, dining)
    activities_cost = max(0.0, activities_cost)
    accommodation = max(0.0, accommodation)
    transport = max(0.0, transport)

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


from app.models.day_plan import Activity


def _recalculate_times(activities: list[Activity]) -> list[Activity]:
    """Recalculate time_start and time_end for reordered activities.

    Preserves each activity's duration but assigns new sequential times
    based on the new order and any route_to_next travel times.
    """
    if not activities:
        return activities

    # Find the start time from the first activity
    current_time = datetime.strptime(activities[0].time_start, "%H:%M")

    for i, activity in enumerate(activities):
        # Set start time
        activity.time_start = current_time.strftime("%H:%M")
        # Set end time based on duration
        end_time = current_time + timedelta(minutes=activity.duration_minutes)
        activity.time_end = end_time.strftime("%H:%M")

        # Add travel time to next if route exists
        if i < len(activities) - 1 and activity.route_to_next:
            travel_minutes = max(1, activity.route_to_next.duration_seconds // 60)
            current_time = end_time + timedelta(minutes=travel_minutes)
        else:
            # Default 15 min gap between activities
            current_time = end_time + timedelta(minutes=15)

    return activities


def _merge_enriched_data(original: JourneyPlan, updated: JourneyPlan) -> JourneyPlan:
    """Preserve enriched data (accommodation, fares, locations) from original plan.

    When a chat edit returns a new JourneyPlan from the LLM, it typically lacks
    the Google-enriched fields (place_id, photo_url, fare_usd, polyline, etc.).
    This merges those fields back from the original plan so they are not lost.
    """
    # Build lookup of original cities by name
    original_cities = {c.name.lower(): c for c in original.cities}

    for city in updated.cities:
        orig = original_cities.get(city.name.lower())
        if orig:
            # Preserve Google-enriched accommodation fields that the LLM won't regenerate
            if orig.accommodation and city.accommodation:
                if not city.accommodation.place_id and orig.accommodation.place_id:
                    city.accommodation.place_id = orig.accommodation.place_id
                if not city.accommodation.photo_url and orig.accommodation.photo_url:
                    city.accommodation.photo_url = orig.accommodation.photo_url
                if not city.accommodation.location and orig.accommodation.location:
                    city.accommodation.location = orig.accommodation.location
                if not city.accommodation.rating and orig.accommodation.rating:
                    city.accommodation.rating = orig.accommodation.rating
                if not city.accommodation.price_level and orig.accommodation.price_level:
                    city.accommodation.price_level = orig.accommodation.price_level
                if not city.accommodation.address and orig.accommodation.address:
                    city.accommodation.address = orig.accommodation.address
            elif orig.accommodation and not city.accommodation:
                city.accommodation = orig.accommodation
            # Preserve location if not set
            if not city.location and orig.location:
                city.location = orig.location
                city.place_id = orig.place_id

    # Preserve enriched travel leg data
    original_legs = {(l.from_city.lower(), l.to_city.lower()): l for l in original.travel_legs}
    for leg in updated.travel_legs:
        orig_leg = original_legs.get((leg.from_city.lower(), leg.to_city.lower()))
        if orig_leg:
            if not leg.fare_usd and orig_leg.fare_usd:
                leg.fare_usd = orig_leg.fare_usd
            if not leg.fare and orig_leg.fare:
                leg.fare = orig_leg.fare
            if not leg.distance_km and orig_leg.distance_km:
                leg.distance_km = orig_leg.distance_km
            if not leg.polyline and orig_leg.polyline:
                leg.polyline = orig_leg.polyline

    # Preserve review score and totals
    if not updated.review_score and original.review_score:
        updated.review_score = original.review_score
    if not updated.total_distance_km and original.total_distance_km:
        updated.total_distance_km = original.total_distance_km
    if not updated.total_travel_hours and original.total_travel_hours:
        updated.total_travel_hours = original.total_travel_hours

    return updated


async def _check_trip_ownership(repo: TripRepository, trip_id: str, user_id: str):
    """Verify the user owns the trip. Warns on ownerless legacy trips."""
    owner = await repo.get_trip_user_id(trip_id)
    if owner is None:
        logger.warning("Ownerless trip %s accessed by user %s (legacy migration)", trip_id, user_id)
        return  # Allow access to ownerless legacy trips
    if owner != user_id:
        raise HTTPException(404, "Trip not found")


@router.post("/plan/stream")
async def plan_trip_stream(
    request: TripRequest,
    orchestrator: JourneyOrchestrator = Depends(get_journey_orchestrator),
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    """Stream journey planning via SSE."""
    get_plan_limiter().check(user["sub"])

    async def event_generator():
        try:
            async for event in orchestrator.plan_stream(request):
                if event.phase == "complete" and event.data:
                    # Save to DB
                    from app.models.journey import JourneyPlan

                    journey = JourneyPlan.model_validate(event.data)
                    trip_id = await repo.save_trip(request, journey, user_id=user["sub"])
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
    user: dict = Depends(require_user),
):
    """Stream day plan generation for a saved trip."""
    day_plan_limiter = get_day_plan_limiter()
    day_plan_limiter.check(user["sub"])
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
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
    enricher: EnricherAgent = Depends(get_enricher),
    orchestrator: DayPlanOrchestrator = Depends(get_day_plan_orchestrator),
    user: dict = Depends(require_user),
) -> ChatEditResponse:
    get_chat_limiter().check(user["sub"])
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    await _check_trip_ownership(repo, trip_id, user["sub"])

    try:
        if request.context == "day_plans":
            if not trip.day_plans:
                return ChatEditResponse(
                    reply="No day plans to edit yet. Generate day plans first, then you can edit them.",
                    changes_made=[],
                )
            response = await chat.edit_day_plans(request.message, trip.day_plans, trip.journey, trip.request)
            if response.updated_day_plans:
                # Recompute routes for edited day plans
                pace = trip.request.pace if trip.request else None
                for dp in response.updated_day_plans:
                    try:
                        dp.activities = await orchestrator._compute_routes_via_matrix(
                            dp.activities, pace=pace or "moderate",
                        )
                    except Exception as exc:
                        logger.warning("Route recomputation after chat edit failed for day %d: %s", dp.day_number, exc)
                await repo.update_day_plans(trip_id, response.updated_day_plans)
        else:
            response = await chat.edit_journey(request.message, trip.journey, trip.request)
            if response.updated_journey:
                response.updated_journey = _merge_enriched_data(trip.journey, response.updated_journey)
                # Re-enrich new/changed cities and legs with Google API data
                try:
                    budget_tier = trip.request.budget.value if hasattr(trip.request, 'budget') else "moderate"
                    response.updated_journey = await enricher.enrich_plan(
                        response.updated_journey, budget_tier=budget_tier
                    )
                except Exception as exc:
                    logger.warning("Re-enrichment after chat edit failed: %s", exc)
                await repo.update_journey(trip_id, response.updated_journey)
                # Clear stale day plans since journey structure changed
                await repo.update_day_plans(trip_id, [], quality_score=None)
                response.changes_made = response.changes_made or []
                response.changes_made.append("Day plans cleared — regenerate to reflect changes")
    except LLMValidationError as exc:
        logger.warning("Chat edit LLM validation failed: %s", exc)
        raise HTTPException(502, f"AI failed to produce a valid response. Please try again.")
    except Exception as exc:
        logger.exception("Chat edit failed for trip %s", trip_id)
        raise HTTPException(502, "Chat edit failed due to an AI service error. Please try again.")

    return response


@router.get("")
async def list_trips(
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TripSummary]:
    return await repo.list_trips(user_id=user["sub"], limit=limit, offset=offset)


@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
) -> TripResponse:
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    await _check_trip_ownership(repo, trip_id, user["sub"])
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


@router.put("/{trip_id}/quick-edit")
async def quick_edit_activity(
    trip_id: str,
    edit: dict,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    """Quick edit a day plan activity (remove or adjust duration).

    Body: { "action": "remove"|"adjust_duration", "day_number": int,
            "activity_id": str, "duration_change": int (minutes, for adjust) }
    """
    await _check_trip_ownership(repo, trip_id, user["sub"])
    trip = await repo.get_trip(trip_id)
    if not trip or not trip.day_plans:
        raise HTTPException(404, "Trip or day plans not found")

    action = edit.get("action")
    day_number = edit.get("day_number")
    activity_id = edit.get("activity_id")

    if not action or not day_number or not activity_id:
        raise HTTPException(400, "Missing action, day_number, or activity_id")

    # Find the day plan
    day_plan = next((dp for dp in trip.day_plans if dp.day_number == day_number), None)
    if not day_plan:
        raise HTTPException(404, f"Day {day_number} not found")

    if action == "remove":
        day_plan.activities = [a for a in day_plan.activities if a.id != activity_id]
        # Recalculate times for remaining activities
        day_plan.activities = _recalculate_times(day_plan.activities)
        # Recalculate daily cost
        day_plan.daily_cost_usd = sum(
            a.estimated_cost_usd or 0 for a in day_plan.activities
        )
    elif action == "adjust_duration":
        duration_change = edit.get("duration_change", 0)
        for a in day_plan.activities:
            if a.id == activity_id:
                a.duration_minutes = max(15, a.duration_minutes + duration_change)
                break
        else:
            raise HTTPException(404, "Activity not found")
        # Recalculate all times (duration change cascades to subsequent activities)
        day_plan.activities = _recalculate_times(day_plan.activities)
    else:
        raise HTTPException(400, f"Unknown action: {action}")

    await repo.update_day_plans(trip_id, trip.day_plans)
    return {"status": "ok", "day_plans": [dp.model_dump() for dp in trip.day_plans]}


@router.put("/{trip_id}/reorder")
async def reorder_activities(
    trip_id: str,
    body: dict,
    repo: TripRepository = Depends(get_trip_repository),
    orchestrator: DayPlanOrchestrator = Depends(get_day_plan_orchestrator),
    user: dict = Depends(require_user),
):
    """Reorder activities within a day plan.

    Recalculates time slots and routes after reordering.

    Body: { "day_number": int, "activity_ids": ["id1", "id2", ...] }
    """
    await _check_trip_ownership(repo, trip_id, user["sub"])
    trip = await repo.get_trip(trip_id)
    if not trip or not trip.day_plans:
        raise HTTPException(404, "Trip or day plans not found")

    day_number = body.get("day_number")
    activity_ids = body.get("activity_ids", [])

    if not day_number or not activity_ids:
        raise HTTPException(400, "Missing day_number or activity_ids")

    day_plan = next((dp for dp in trip.day_plans if dp.day_number == day_number), None)
    if not day_plan:
        raise HTTPException(404, f"Day {day_number} not found")

    # Reorder activities based on the provided ID order
    id_to_activity = {a.id: a for a in day_plan.activities}
    reordered = []
    for aid in activity_ids:
        if aid in id_to_activity:
            reordered.append(id_to_activity[aid])
    # Append any activities not in the reorder list
    for a in day_plan.activities:
        if a.id not in {r.id for r in reordered}:
            reordered.append(a)

    # Recalculate time slots for the new order
    reordered = _recalculate_times(reordered)

    # Recompute routes between consecutive activities
    pace = trip.request.pace if trip.request else None
    try:
        reordered = await orchestrator._compute_routes_via_matrix(
            reordered, pace=pace or "moderate",
        )
    except Exception as exc:
        logger.warning("Route recomputation failed after reorder: %s", exc)

    day_plan.activities = reordered

    await repo.update_day_plans(trip_id, trip.day_plans)
    return {"status": "ok", "day_plans": [dp.model_dump() for dp in trip.day_plans]}


@router.post("/{trip_id}/tips")
async def generate_tips(
    trip_id: str,
    activities: list[dict],
    tips_service: TipsService = Depends(get_tips_service),
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    await _check_trip_ownership(repo, trip_id, user["sub"])
    get_tips_limiter().check(user["sub"])
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
