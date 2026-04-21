from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from app.dependencies import get_city_repo, get_job_repo, get_places_service, require_user
from app.db.repository import CityRepository, JobRepository

router = APIRouter(tags=["admin"])


# Public job polling (any authenticated user can check their job)
@router.get("/api/jobs/{job_id}")
async def get_job_status(
    job_id: UUID,
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Get job status by ID."""
    job = await job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": str(job.id),
        "status": job.status,
        "progress_pct": job.progress_pct,
        "result": job.result,
        "error": job.error,
    }


# Admin endpoints
@router.post("/api/admin/cities")
async def add_city(
    body: dict,
    user: dict = Depends(require_user),
    city_repo: CityRepository = Depends(get_city_repo),
    places_service=Depends(get_places_service),
):
    """Add a city to the catalog by geocoding it."""
    name = body.get("name", "")
    country = body.get("country", "")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    # Geocode to get location + metadata
    geo = await places_service.geocode(f"{name}, {country}" if country else name)
    if not geo:
        raise HTTPException(status_code=404, detail=f"Could not geocode '{name}'")

    city = await city_repo.create(
        name=geo.get("name", name),
        country=geo.get("country", country),
        country_code=geo.get("country_code", "XX")[:3],
        location={"lat": geo["lat"], "lng": geo["lng"]},
        timezone=geo.get("timezone", "UTC"),
        currency=body.get("currency", "USD"),
        population_tier=body.get("population_tier", "medium"),
        region=body.get("region"),
    )
    return {"id": str(city.id), "name": city.name, "country": city.country}


@router.post("/api/admin/cities/{city_id}/generate")
async def trigger_generation(
    city_id: UUID,
    body: dict,
    user: dict = Depends(require_user),
    city_repo: CityRepository = Depends(get_city_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Queue a batch generation job for a city."""
    city = await city_repo.get(city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    job = await job_repo.create(
        job_type="batch_generate",
        city_id=city_id,
        parameters={
            "city_name": city.name,
            "country": city.country,
            "pace": body.get("pace", "moderate"),
            "budget": body.get("budget", "moderate"),
            "day_count": body.get("day_count", 3),
        },
        priority=body.get("priority", 5),
    )
    return {"job_id": str(job.id), "status": "queued"}


@router.post("/api/admin/cities/{city_id}/refresh")
async def trigger_refresh(
    city_id: UUID,
    user: dict = Depends(require_user),
    city_repo: CityRepository = Depends(get_city_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Trigger a refresh job for a city."""
    city = await city_repo.get(city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    job = await job_repo.create(job_type="refresh", city_id=city_id, parameters={}, priority=3)
    return {"job_id": str(job.id)}


@router.get("/api/admin/stats")
async def get_stats(
    user: dict = Depends(require_user),
    city_repo: CityRepository = Depends(get_city_repo),
):
    """Get admin stats."""
    cities, total = await city_repo.list(limit=1, offset=0)
    return {"cities_count": total}
