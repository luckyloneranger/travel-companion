from fastapi import APIRouter, Depends, Query, HTTPException
from uuid import UUID

from app.dependencies import get_city_repo, get_variant_repo, get_place_repo
from app.db.repository import CityRepository, VariantRepository, PlaceRepository

router = APIRouter(prefix="/api/cities", tags=["cities"])


@router.get("")
async def list_cities(
    region: str | None = None,
    sort: str = "name",
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    city_repo: CityRepository = Depends(get_city_repo),
):
    """List cities in the catalog."""
    cities, total = await city_repo.list(limit=limit, offset=offset, region=region, sort=sort)
    return {
        "cities": [_city_to_response(c) for c in cities],
        "total": total,
    }


@router.get("/{city_id}")
async def get_city(
    city_id: UUID,
    city_repo: CityRepository = Depends(get_city_repo),
    variant_repo: VariantRepository = Depends(get_variant_repo),
    place_repo: PlaceRepository = Depends(get_place_repo),
):
    """Get city detail with landmarks and available variants."""
    city = await city_repo.get(city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    variants = await variant_repo.list_by_city(city_id)
    places = await place_repo.get_by_city(city_id)
    landmarks = sorted(
        [p for p in places if not p.is_lodging],
        key=lambda p: (p.rating or 0, p.user_rating_count or 0),
        reverse=True,
    )[:10]

    return {
        **_city_to_response(city),
        "landmarks": [_place_to_dict(p) for p in landmarks],
        "available_variants": [
            {
                "id": str(v.id),
                "pace": v.pace,
                "budget": v.budget,
                "day_count": v.day_count,
                "quality_score": v.quality_score,
                "status": v.status,
            }
            for v in variants
            if v.status in ("published", "draft")
        ],
    }


@router.get("/{city_id}/variants")
async def list_variants(
    city_id: UUID,
    pace: str | None = None,
    budget: str | None = None,
    variant_repo: VariantRepository = Depends(get_variant_repo),
):
    """List available plan variants for a city."""
    variants = await variant_repo.list_by_city(city_id, pace=pace, budget=budget)
    return {
        "variants": [
            {
                "id": str(v.id),
                "pace": v.pace,
                "budget": v.budget,
                "day_count": v.day_count,
                "quality_score": v.quality_score,
                "status": v.status,
                "cost_total": v.cost_breakdown.get("total") if v.cost_breakdown else None,
            }
            for v in variants
            if v.status in ("published", "draft")
        ]
    }


@router.get("/{city_id}/variants/{variant_id}")
async def get_variant_detail(
    city_id: UUID,
    variant_id: UUID,
    variant_repo: VariantRepository = Depends(get_variant_repo),
):
    """Get full variant with day plans, activities, routes."""
    variant = await variant_repo.get_detail(variant_id)
    if not variant or variant.city_id != city_id:
        raise HTTPException(status_code=404, detail="Variant not found")
    return _variant_to_detail(variant)


def _city_to_response(city) -> dict:
    return {
        "id": str(city.id),
        "name": city.name,
        "country": city.country,
        "country_code": city.country_code,
        "location": city.location,
        "timezone": city.timezone,
        "currency": city.currency,
        "population_tier": city.population_tier,
        "region": city.region,
        "created_at": city.created_at.isoformat() if city.created_at else None,
    }


def _place_to_dict(place) -> dict:
    return {
        "id": str(place.id),
        "name": place.name,
        "google_place_id": place.google_place_id,
        "address": place.address,
        "location": place.location,
        "types": place.types,
        "rating": place.rating,
        "user_rating_count": place.user_rating_count,
        "photo_references": place.photo_references,
        "editorial_summary": place.editorial_summary,
    }


def _variant_to_detail(variant) -> dict:
    day_plans = []
    for dp in sorted(variant.day_plans, key=lambda d: d.day_number):
        activities = []
        for act in sorted(dp.activities, key=lambda a: a.sequence):
            place = act.place
            activities.append({
                "id": str(act.id),
                "place_id": str(act.place_id),
                "place_name": place.name if place else "",
                "place_address": place.address if place else None,
                "place_location": place.location if place else {},
                "place_rating": place.rating if place else None,
                "place_photo_url": (
                    f"/api/places/photo/{place.photo_references[0]}"
                    if place and place.photo_references
                    else None
                ),
                "place_types": place.types if place else [],
                "place_opening_hours": place.opening_hours if place else None,
                "sequence": act.sequence,
                "start_time": act.start_time.isoformat() if act.start_time else None,
                "end_time": act.end_time.isoformat() if act.end_time else None,
                "duration_minutes": act.duration_minutes,
                "category": act.category,
                "description": act.description,
                "is_meal": act.is_meal,
                "meal_type": act.meal_type,
                "estimated_cost_usd": act.estimated_cost_usd,
            })
        routes = [
            {
                "from_activity_sequence": r.from_activity_id,
                "to_activity_sequence": r.to_activity_id,
                "travel_mode": r.travel_mode,
                "distance_meters": r.distance_meters,
                "duration_seconds": r.duration_seconds,
                "polyline": r.polyline,
            }
            for r in dp.routes
        ]
        day_plans.append({
            "day_number": dp.day_number,
            "theme": dp.theme,
            "theme_description": dp.theme_description,
            "activities": activities,
            "routes": routes,
        })

    return {
        "id": str(variant.id),
        "city_id": str(variant.city_id),
        "pace": variant.pace,
        "budget": variant.budget,
        "day_count": variant.day_count,
        "quality_score": variant.quality_score,
        "status": variant.status,
        "accommodation": None,
        "accommodation_alternatives": variant.accommodation_alternatives or [],
        "booking_hint": variant.booking_hint,
        "cost_breakdown": variant.cost_breakdown,
        "day_plans": day_plans,
    }
