"""API router for multi-city journey generation.

V6 Architecture: LLM-First with Iterative Refinement
- Scout: LLM generates initial journey (cities + highlights + travel)
- Enricher: Ground with Google APIs (directions, geocoding)
- Reviewer: Evaluate if humanly feasible
- Planner: Fix issues based on review
- Loop until quality is acceptable
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.generators.journey_plan.request import JourneyRequest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/journey", tags=["journey"])


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ REQUEST MODELS                                                             │
# └───────────────────────────────────────────────────────────────────────────┘

class JourneyPlanRequest(BaseModel):
    """Request to generate a multi-city journey plan."""
    origin: str = Field(..., description="Starting city (e.g., 'Bangalore, India')")
    region: str = Field(..., description="Region to explore (e.g., 'Vietnam', 'South India')")
    destinations: list[str] = Field(default_factory=list, description="Specific cities to visit (optional)")
    total_days: int = Field(..., ge=3, le=30, description="Total trip duration in days")
    start_date: str = Field(..., description="Trip start date (ISO format: YYYY-MM-DD)")
    interests: list[str] = Field(..., min_length=1, description="Travel interests (e.g., ['culture', 'food', 'nature'])")
    pace: str = Field(default="moderate", description="Trip pace: relaxed, moderate, or packed")
    return_to_origin: bool = Field(default=False, description="Whether to return to starting city")
    must_include: list[str] = Field(default_factory=list, description="Cities that must be included")
    avoid: list[str] = Field(default_factory=list, description="Places or types to avoid")
    
    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Bangalore, India",
                "region": "Vietnam",
                "total_days": 14,
                "start_date": "2026-03-01",
                "interests": ["culture", "food", "history", "nature"],
                "pace": "moderate",
                "return_to_origin": False
            }
        }


class DayPlansRequest(BaseModel):
    """Request to generate detailed day plans for an approved journey."""
    journey: dict = Field(..., description="Approved journey plan from /plan/stream")
    start_date: str = Field(..., description="Trip start date (ISO format)")
    interests: list[str] = Field(..., description="Travel interests for activity selection")
    pace: str = Field(default="moderate", description="Daily activity pace")
    travel_mode: str = Field(default="WALK", description="Preferred travel mode in cities: WALK, DRIVE, TRANSIT")
    
    class Config:
        json_schema_extra = {
            "example": {
                "journey": {
                    "theme": "Cultural Vietnam",
                    "total_days": 14,
                    "cities": [
                        {"name": "Hanoi", "country": "Vietnam", "days": 3},
                        {"name": "Ninh Binh", "country": "Vietnam", "days": 2}
                    ],
                    "travel_legs": [
                        {"from_city": "Hanoi", "to_city": "Ninh Binh", "mode": "bus", "duration_hours": 2}
                    ]
                },
                "start_date": "2026-03-01",
                "interests": ["culture", "food", "history"],
                "pace": "moderate"
            }
        }


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ RESPONSE MODELS                                                            │
# └───────────────────────────────────────────────────────────────────────────┘

class JourneyPlanResponse(BaseModel):
    """Response containing the generated journey plan."""
    journey: dict = Field(..., description="Complete journey plan with cities and travel legs")
    review_score: float = Field(..., description="Quality score from review (0-100)")
    iterations: int = Field(..., description="Number of refinement iterations")
    total_travel_hours: float = Field(..., description="Total travel time between cities")
    total_distance_km: float = Field(..., description="Total distance traveled")
    
    class Config:
        json_schema_extra = {
            "example": {
                "journey": {
                    "theme": "Cultural South India",
                    "route": "Bangalore → Mysore → Ooty → Coorg",
                    "total_days": 7,
                    "cities": [{"name": "Mysore", "days": 2}]
                },
                "review_score": 85.0,
                "iterations": 2,
                "total_travel_hours": 12.5,
                "total_distance_km": 450.0
            }
        }


# ┌───────────────────────────────────────────────────────────────────────────┐
# │ JOURNEY PLANNING ENDPOINTS                                                 │
# └───────────────────────────────────────────────────────────────────────────┘

@router.post("/plan", response_model=JourneyPlanResponse)
async def plan_journey(request: JourneyPlanRequest):
    """
    Generate a multi-city journey plan (non-streaming).
    
    For most use cases, prefer `/plan/stream` for real-time progress updates.
    """
    from app.generators.journey_plan import V6Orchestrator
    
    logger.info(f"Journey plan request: {request.origin} → {request.region}")
    
    try:
        # Convert to V6 request format
        orchestrator = V6Orchestrator()
        
        # Build request dict compatible with V6Orchestrator
        v6_request = _build_v6_request(request)
        enriched = await orchestrator.plan_journey(v6_request)
        
        return JourneyPlanResponse(
            journey=_format_journey_response(enriched),
            review_score=0,
            iterations=1,
            total_travel_hours=enriched.total_travel_hours,
            total_distance_km=enriched.total_distance_km,
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Journey planning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Journey planning failed")


@router.post("/plan/stream")
async def plan_journey_stream(request: JourneyPlanRequest, req: Request):
    """
    Stream journey planning progress (recommended).
    
    Events emitted:
    - `scout`: LLM generating initial journey plan
    - `enrich`: Grounding with Google APIs (directions, geocoding)
    - `review`: Evaluating plan feasibility
    - `planner`: Fixing issues based on review
    - `complete`: Final journey plan ready
    - `error`: Processing failed
    
    Each event includes:
    - phase: Current phase name
    - step: Substep (start/progress/complete)
    - message: Human-readable status
    - progress: Overall progress (0-100)
    - iteration: Current iteration number (for refinement loops)
    - data: Phase-specific data (route, cities, etc.)
    """
    from app.generators.journey_plan import V6Orchestrator
    
    logger.info(f"Journey plan stream: {request.origin} → {request.region}")
    
    async def event_generator():
        try:
            orchestrator = V6Orchestrator()
            v6_request = _build_v6_request(request)
            
            async for progress in orchestrator.plan_journey_stream(v6_request):
                event_data = {
                    "phase": progress.phase,
                    "step": progress.step,
                    "message": progress.message,
                    "progress": progress.progress,
                    "iteration": progress.iteration,
                }
                if progress.data:
                    event_data["data"] = progress.data
                
                yield f"event: {progress.phase}\ndata: {json.dumps(event_data)}\n\n"
                
                if progress.phase in ("complete", "error"):
                    break
                    
                if await req.is_disconnected():
                    logger.info("Client disconnected")
                    break
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
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
# │ DAY PLANS GENERATION ENDPOINTS                                            │
# └───────────────────────────────────────────────────────────────────────────┘

@router.post("/days/stream")
async def generate_day_plans_stream(request: DayPlansRequest, req: Request):
    """
    Generate detailed day-by-day itineraries for each city (streaming).
    
    Takes an approved journey plan and creates detailed itineraries
    for each city using the FastItineraryGenerator.
    
    Events emitted:
    - `city_start`: Beginning generation for a city
    - `city_complete`: Finished city with day plans
    - `city_error`: Error generating city plans (non-fatal)
    - `complete`: All cities done
    - `error`: Fatal error
    
    Each event includes city_name, city_index, total_cities,
    and progress percentages.
    """
    from app.generators.journey_plan import (
        V6DayPlanGenerator,
        JourneyPlan,
        CityStop,
        CityHighlight,
        TravelLeg,
        TransportMode,
    )
    from app.models import Pace, TravelMode as ITravelMode
    
    logger.info(f"Day plans stream for {len(request.journey.get('cities', []))} cities")
    
    async def event_generator():
        try:
            # Reconstruct JourneyPlan from dict
            journey = _parse_journey_dict(request.journey)
            
            # Parse parameters
            start_date = datetime.fromisoformat(request.start_date).date()
            pace = Pace(request.pace.lower())
            travel_mode = ITravelMode(request.travel_mode.upper())
            
            # Generate
            generator = V6DayPlanGenerator()
            
            async for progress in generator.generate_day_plans_stream(
                journey=journey,
                start_date=start_date,
                interests=request.interests,
                pace=pace,
                travel_mode=travel_mode,
            ):
                event_data = {
                    "phase": progress.phase,
                    "city_name": progress.city_name,
                    "city_index": progress.city_index,
                    "total_cities": progress.total_cities,
                    "message": progress.message,
                    "progress": progress.progress,
                    "city_progress": progress.city_progress,
                }
                if progress.data:
                    event_data["data"] = progress.data
                
                yield f"event: {progress.phase}\ndata: {json.dumps(event_data)}\n\n"
                
                if progress.phase in ("complete", "error"):
                    break
                
                if await req.is_disconnected():
                    logger.info("Day plans client disconnected")
                    break
                    
        except Exception as e:
            logger.error(f"Day plans error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
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
# │ HELPER FUNCTIONS                                                           │
# └───────────────────────────────────────────────────────────────────────────┘

def _build_v6_request(request: JourneyPlanRequest) -> JourneyRequest:
    """Convert JourneyPlanRequest to V6Orchestrator format."""
    return JourneyRequest(
        origin=request.origin,
        region=request.region,
        destinations=request.destinations,
        total_days=request.total_days,
        start_date=request.start_date,
        interests=request.interests,
        pace=request.pace,
        return_to_origin=request.return_to_origin,
        must_include=request.must_include,
        avoid=request.avoid,
    )


def _format_journey_response(enriched) -> dict:
    """Format EnrichedPlan to response dict."""
    return {
        "theme": enriched.plan.theme,
        "summary": enriched.plan.summary,
        "route": enriched.plan.route_string,
        "origin": enriched.plan.origin,
        "region": enriched.plan.region,
        "total_days": enriched.plan.total_days,
        "cities": [
            {
                "name": city.name,
                "country": city.country,
                "days": city.days,
                "why_visit": city.why_visit,
                "best_time_to_visit": city.best_time_to_visit,
                "highlights": [
                    {"name": h.name, "description": h.description, "category": h.category}
                    for h in city.highlights
                ],
                "latitude": city.latitude,
                "longitude": city.longitude,
            }
            for city in enriched.plan.cities
        ],
        "travel_legs": [
            {
                "from_city": leg.from_city,
                "to_city": leg.to_city,
                "mode": leg.mode.value,
                "duration_hours": leg.duration_hours,
                "distance_km": leg.distance_km,
                "notes": leg.notes,
                "estimated_cost": leg.estimated_cost,
                "booking_tip": leg.booking_tip,
            }
            for leg in enriched.plan.travel_legs
        ],
    }


def _parse_journey_dict(journey_dict: dict):
    """Parse journey dict back to JourneyPlan object."""
    from app.generators.journey_plan import (
        JourneyPlan,
        CityStop,
        CityHighlight,
        TravelLeg,
        TransportMode,
    )
    
    cities = []
    for c in journey_dict.get("cities", []):
        highlights = []
        for h in c.get("highlights", []):
            if isinstance(h, dict):
                highlights.append(CityHighlight(
                    name=h.get("name", ""),
                    description=h.get("description", ""),
                    category=h.get("category", ""),
                    suggested_duration_hours=h.get("suggested_duration_hours", 2.0),
                ))
            elif isinstance(h, str):
                highlights.append(CityHighlight(name=h, description="", category=""))
        
        cities.append(CityStop(
            name=c.get("name", ""),
            country=c.get("country", ""),
            days=c.get("days", 1),
            highlights=highlights,
            why_visit=c.get("why_visit", ""),
            latitude=c.get("latitude"),
            longitude=c.get("longitude"),
        ))
    
    travel_legs = []
    for leg in journey_dict.get("travel_legs", []):
        mode_str = leg.get("mode", "drive").lower()
        try:
            mode = TransportMode(mode_str)
        except ValueError:
            mode = TransportMode.DRIVE
        
        travel_legs.append(TravelLeg(
            from_city=leg.get("from_city", ""),
            to_city=leg.get("to_city", ""),
            mode=mode,
            duration_hours=leg.get("duration_hours", 0),
            distance_km=leg.get("distance_km"),
            notes=leg.get("notes", ""),
            booking_tip=leg.get("booking_tip"),
        ))
    
    return JourneyPlan(
        theme=journey_dict.get("theme", "Your Journey"),
        summary=journey_dict.get("summary", ""),
        cities=cities,
        travel_legs=travel_legs,
        total_days=journey_dict.get("total_days", sum(c.days for c in cities)),
        origin=journey_dict.get("origin", ""),
        region=journey_dict.get("region", ""),
    )


# Legacy endpoint aliases for backward compatibility
@router.post("/v6/plan", response_model=JourneyPlanResponse, include_in_schema=False)
async def plan_journey_v6_alias(request: JourneyPlanRequest):
    """Alias for /plan (V6 is now the default)."""
    return await plan_journey(request)


@router.post("/v6/plan/stream", include_in_schema=False)
async def plan_journey_v6_stream_alias(request: JourneyPlanRequest, req: Request):
    """Alias for /plan/stream (V6 is now the default)."""
    return await plan_journey_stream(request, req)


@router.post("/v6/days/stream", include_in_schema=False)
async def generate_v6_days_stream_alias(request: DayPlansRequest, req: Request):
    """Alias for /days/stream (V6 is now the default)."""
    return await generate_day_plans_stream(request, req)
