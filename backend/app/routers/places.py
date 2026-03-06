import re

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response

from app.dependencies import get_places_service
from app.services.google.places import GooglePlacesService

router = APIRouter(prefix="/api/places", tags=["places"])

# Matches a URL-encoded Places photo reference: places%2F<id>%2Fphotos%2F<ref>
_PHOTO_REF_PATTERN = re.compile(
    r"^places%2F[A-Za-z0-9_-]+%2Fphotos%2F[A-Za-z0-9_-]+$"
)


@router.get("/search")
async def search_places(
    query: str = Query(..., min_length=2),
    lat: float = Query(0),
    lng: float = Query(0),
    radius: float = Query(5000),
    places: GooglePlacesService = Depends(get_places_service),
):
    """Search for places using Google Places text search.

    When lat/lng are provided, the query is augmented with location context
    for more relevant results.
    """
    # TODO: Add IP-based rate limiting (no user context available on this public endpoint)
    # text_search only accepts query and max_results; location filtering
    # is handled server-side by Google based on the query text.
    results = await places.text_search(query)
    return results


@router.get("/alternatives")
async def get_alternatives(
    place_id: str = Query(..., min_length=1),
    lat: float = Query(...),
    lng: float = Query(...),
    places: GooglePlacesService = Depends(get_places_service),
):
    """Get alternative accommodation options near a location.

    Returns up to 3 lodging alternatives near the given coordinates,
    excluding the currently-selected hotel (identified by place_id).
    """
    # TODO: Add IP-based rate limiting (no user context available on this public endpoint)
    from app.models.common import Location

    location = Location(lat=lat, lng=lng)

    # Use text_search_places with "hotel" query, biased to the location.
    # Request extra results so we still have 3 after filtering out current.
    candidates = await places.text_search_places(
        query="hotels",
        location=location,
        radius_meters=5000,
        max_results=10,
    )

    alternatives = []
    for c in candidates:
        if c.place_id == place_id:
            continue
        # Only include lodging-type results
        if not any(t in c.types for t in ("lodging", "hotel", "resort_hotel")):
            continue
        alternatives.append({
            "name": c.name,
            "address": c.address,
            "rating": c.rating,
            "price_level": c.price_level,
            "place_id": c.place_id,
            "photo_url": (
                places.get_photo_url(c.photo_reference)
                if c.photo_reference
                else None
            ),
            "editorial_summary": c.editorial_summary,
        })
        if len(alternatives) >= 3:
            break

    return alternatives


@router.get("/photo/{photo_ref:path}")
async def proxy_photo(
    photo_ref: str,
    w: int = Query(default=800, ge=100, le=1600),
    places: GooglePlacesService = Depends(get_places_service),
):
    """Proxy Google Places photos to avoid exposing the API key to clients."""
    from urllib.parse import unquote
    decoded_ref = unquote(photo_ref)

    # Validate the reference format to prevent SSRF
    if not decoded_ref.startswith("places/") or "/photos/" not in decoded_ref:
        raise HTTPException(400, "Invalid photo reference")

    url = places.get_direct_photo_url(decoded_ref, max_width=w)
    try:
        resp = await places.client.get(url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        raise HTTPException(502, "Failed to fetch photo")

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
    )
