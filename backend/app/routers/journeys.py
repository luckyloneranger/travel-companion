from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.dependencies import get_journey_repo, get_job_repo, require_user
from app.db.repository import JourneyRepository, JobRepository
from app.models.journey import JourneyRequest

router = APIRouter(prefix="/api/journeys", tags=["journeys"])


@router.post("")
async def create_journey(
    request: JourneyRequest,
    user: dict = Depends(require_user),
    journey_repo: JourneyRepository = Depends(get_journey_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Create a new journey by assembling pre-generated city plans.

    For MVP, create a simple journey record. The full assembler integration
    requires wiring up the LLM allocator + variant lookup which will be
    done when the assembler dependency is added.
    """
    journey = await journey_repo.create(
        user_id=user.get("sub", ""),
        destination=request.destination,
        start_date=request.start_date,
        total_days=request.total_days,
        pace=request.pace.value if hasattr(request.pace, "value") else request.pace,
        budget=request.budget.value if hasattr(request.budget, "value") else request.budget,
        city_sequence=[],  # Will be populated by assembler
        origin=request.origin,
        travelers=request.travelers,
        status="generating",
    )

    # Queue assembly job
    job = await job_repo.create(
        job_type="assemble",
        parameters={
            "journey_id": str(journey.id),
            "destination": request.destination,
            "total_days": request.total_days,
            "pace": request.pace.value if hasattr(request.pace, "value") else request.pace,
            "budget": request.budget.value if hasattr(request.budget, "value") else request.budget,
        },
        priority=10,
    )

    return {
        "id": str(journey.id),
        "status": "generating",
        "job_id": str(job.id),
    }


@router.get("")
async def list_journeys(
    user: dict = Depends(require_user),
    journey_repo: JourneyRepository = Depends(get_journey_repo),
    limit: int = 50,
    offset: int = 0,
):
    journeys, total = await journey_repo.list_by_user(
        user_id=user.get("sub", ""),
        limit=limit,
        offset=offset,
    )
    return {
        "journeys": [
            {
                "id": str(j.id),
                "destination": j.destination,
                "start_date": j.start_date.isoformat() if j.start_date else None,
                "total_days": j.total_days,
                "city_count": len(j.city_sequence) if j.city_sequence else 0,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in journeys
        ],
        "total": total,
    }


@router.get("/{journey_id}")
async def get_journey(
    journey_id: UUID,
    user: dict = Depends(require_user),
    journey_repo: JourneyRepository = Depends(get_journey_repo),
):
    journey = await journey_repo.get(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return {
        "id": str(journey.id),
        "destination": journey.destination,
        "origin": journey.origin,
        "start_date": journey.start_date.isoformat() if journey.start_date else None,
        "total_days": journey.total_days,
        "pace": journey.pace,
        "budget": journey.budget,
        "travelers": journey.travelers,
        "status": journey.status,
        "city_sequence": journey.city_sequence,
        "transport_legs": journey.transport_legs,
        "weather_forecasts": journey.weather_forecasts,
        "cost_breakdown": journey.cost_breakdown,
        "created_at": journey.created_at.isoformat() if journey.created_at else None,
    }


@router.delete("/{journey_id}")
async def delete_journey(
    journey_id: UUID,
    user: dict = Depends(require_user),
    journey_repo: JourneyRepository = Depends(get_journey_repo),
):
    deleted = await journey_repo.delete(journey_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journey not found")
    return {"deleted": True}
