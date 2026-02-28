"""Itinerary API router for single-city day planning.

Uses FastItineraryGenerator for quick, high-quality itinerary generation.
"""

import asyncio
import json
import logging
from datetime import date
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models import ItineraryRequest, ItineraryResponse, TipsRequest, TipsResponse, QualityScoreResponse
from app.generators.day_plan.fast import FastItineraryGenerator
from app.generators.day_plan.quality import ItineraryScorer

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared quality scorer instance
_quality_scorer = ItineraryScorer()


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ ITINERARY GENERATION                                                       │
# └───────────────────────────────────────────────────────────────────────────┘

@router.post(
    "/itinerary",
    response_model=ItineraryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a travel itinerary",
    description="""
    Generate an AI-powered travel itinerary based on user preferences.
    
    The generation process:
    1. Geocodes the destination
    2. Discovers relevant places based on interests
    3. AI selects and groups places into themed days
    4. Optimizes routes between places
    5. Builds time-slotted schedules
    
    Note: Tips are generated on-demand via the /tips endpoint.
    """,
)
async def generate_itinerary(request: ItineraryRequest) -> ItineraryResponse:
    """Generate a complete travel itinerary."""
    logger.info(f"Itinerary request for {request.destination}")

    # Validate dates
    _validate_request(request)

    try:
        async with FastItineraryGenerator() as generator:
            itinerary = await generator.generate(request)
            logger.info(f"Generated itinerary with {len(itinerary.days)} days")
        
        # Apply quality evaluation
        _apply_quality_score(itinerary)
        
        return itinerary

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate itinerary. Please try again.",
        )


@router.post(
    "/itinerary/stream",
    summary="Generate itinerary with streaming progress",
    description="""
    Generate an AI-powered travel itinerary with real-time progress updates via SSE.
    
    Returns Server-Sent Events with progress updates during generation,
    followed by the final itinerary result.
    """,
)
async def generate_itinerary_stream(request: ItineraryRequest):
    """Generate itinerary with streaming progress updates."""
    logger.info(f"Streaming itinerary request for {request.destination}")

    # Validate dates
    _validate_request(request)

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for progress updates."""
        progress_queue: asyncio.Queue[dict] = asyncio.Queue()

        async def progress_callback(phase: str, message: str, progress: int, data: dict | None = None):
            """Callback to report progress."""
            await progress_queue.put({
                "type": "progress",
                "phase": phase,
                "message": message,
                "progress": progress,
                "data": data,
            })

        async def generate_in_background():
            """Run generation and put result in queue."""
            try:
                async with FastItineraryGenerator() as generator:
                    result = await generator.generate(request, progress_callback=progress_callback)
                    await progress_queue.put({"type": "complete", "result": result})
            except Exception as e:
                logger.error(f"Generation failed: {e}", exc_info=True)
                await progress_queue.put({"type": "error", "message": str(e)})

        # Start generation in background
        task = asyncio.create_task(generate_in_background())

        try:
            while True:
                event = await progress_queue.get()
                
                if event["type"] == "progress":
                    yield f"data: {json.dumps(event)}\n\n"
                
                elif event["type"] == "complete":
                    result = event["result"]
                    
                    # Apply quality evaluation
                    _apply_quality_score(result)
                    
                    # Convert Pydantic model to JSON-serializable dict
                    result_dict = result.model_dump(mode="json")
                    yield f"data: {json.dumps({'type': 'complete', 'result': result_dict})}\n\n"
                    break
                
                elif event["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'error': event['message']})}\n\n"
                    break

        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ PLACES SEARCH                                                              │
# └───────────────────────────────────────────────────────────────────────────┘

@router.get(
    "/places/search",
    summary="Search for places",
    description="Search for places in a destination based on a text query.",
)
async def search_places(
    query: str,
    destination: str,
    limit: int = 10,
):
    """Search for places in a destination."""
    from app.services.external import GooglePlacesService

    try:
        places_service = GooglePlacesService()

        # First geocode the destination
        dest = await places_service.geocode(destination)

        # Search for places
        candidates = await places_service.discover_places(
            location=dest.location,
            interests=[query.lower()],
            radius_km=10,
        )

        return {
            "destination": dest.name,
            "places": [
                {
                    "place_id": p.place_id,
                    "name": p.name,
                    "address": p.address,
                    "rating": p.rating,
                    "types": p.types[:3],
                }
                for p in candidates[:limit]
            ],
        }

    except Exception as e:
        logger.error(f"Place search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search places",
        )


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ TIPS GENERATION                                                            │
# └───────────────────────────────────────────────────────────────────────────┘

@router.post(
    "/tips",
    response_model=TipsResponse,
    summary="Generate tips for activities (on-demand)",
    description="""
    Generate AI-powered tips for activities in an itinerary.
    
    This endpoint is called on-demand when the user views activity details,
    rather than generating all tips upfront. This reduces initial load time.
    
    Send a batch of activities (typically all activities for a day) to get
    tips efficiently in a single LLM call.
    """,
)
async def generate_tips(request: TipsRequest) -> TipsResponse:
    """Generate tips for activities on-demand."""
    logger.info(f"Generating tips for {len(request.activities)} activities")
    
    if not request.activities:
        return TipsResponse(tips={})
    
    # Build schedule format expected by the tips generator
    schedule = []
    for activity in request.activities:
        schedule.append({
            "place_id": activity.get("place_id", ""),
            "name": activity.get("name", ""),
            "category": activity.get("category", "attraction"),
            "time_start": activity.get("time_start", "09:00"),
            "duration_minutes": activity.get("duration_minutes", 60),
        })
    
    try:
        from app.generators.tips import TipsGenerator
        
        generator = TipsGenerator()
        tips = await generator.generate(
            schedule,
            destination=request.destination,
        )
        return TipsResponse(tips=tips)
            
    except Exception as e:
        logger.error(f"Tips generation failed: {e}")
        # Return empty tips rather than failing - tips are non-critical
        return TipsResponse(tips={})


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ QUALITY EVALUATION                                                         │
# └───────────────────────────────────────────────────────────────────────────┘

@router.post(
    "/quality/evaluate",
    summary="Evaluate itinerary quality",
    description="""
    Evaluate the quality of an existing itinerary.
    
    Quality metrics include:
    - meal_timing: Meals at proper times and positions
    - geographic_clustering: Places grouped by proximity
    - travel_efficiency: Reasonable travel times
    - variety: Mix of activity types
    - opening_hours: Places open when scheduled
    - theme_alignment: Activities match day themes
    - duration_appropriateness: Time allocated appropriately
    """,
)
async def evaluate_quality(itinerary: ItineraryResponse):
    """Evaluate quality of an existing itinerary."""
    try:
        report = _quality_scorer.evaluate(itinerary)
        return {
            "overall_score": round(report.overall_score, 1),
            "overall_grade": report.overall_grade.value,
            "scores": report.scores.to_dict(),
            "metrics": [m.to_dict() for m in report.metrics],
            "total_issues": report.total_issues,
            "critical_issues": report.critical_issues,
            "recommendations": report.recommendations,
            "metadata": {
                "destination": report.destination,
                "num_days": report.num_days,
                "total_activities": report.total_activities,
            },
        }
    except Exception as e:
        logger.error(f"Quality evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality evaluation failed: {str(e)}",
        )


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ HELPER FUNCTIONS                                                           │
# └───────────────────────────────────────────────────────────────────────────┘

def _validate_request(request: ItineraryRequest):
    """Validate itinerary request parameters."""
    if request.start_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be in the past",
        )

    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    duration = (request.end_date - request.start_date).days + 1
    if duration > 14:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trip duration cannot exceed 14 days",
        )


def _apply_quality_score(itinerary: ItineraryResponse):
    """Apply quality evaluation to an itinerary."""
    try:
        quality_report = _quality_scorer.evaluate(itinerary)
        itinerary.quality_score = QualityScoreResponse(
            meal_timing=quality_report.scores.meal_timing,
            geographic_clustering=quality_report.scores.geographic_clustering,
            travel_efficiency=quality_report.scores.travel_efficiency,
            variety=quality_report.scores.variety,
            opening_hours=quality_report.scores.opening_hours,
            theme_alignment=quality_report.scores.theme_alignment,
            duration_appropriateness=quality_report.scores.duration_appropriateness,
            overall=quality_report.overall_score,
            grade=quality_report.overall_grade.value,
        )
        logger.info(f"Quality: {quality_report.overall_grade.value} ({quality_report.overall_score:.1f}/100)")
    except Exception as e:
        logger.warning(f"Quality evaluation failed: {e}")
