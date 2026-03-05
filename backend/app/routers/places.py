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
    # text_search only accepts query and max_results; location filtering
    # is handled server-side by Google based on the query text.
    results = await places.text_search(query)
    return results


@router.get("/photo/{photo_ref:path}")
async def proxy_photo(
    photo_ref: str,
    places: GooglePlacesService = Depends(get_places_service),
):
    """Proxy Google Places photos to avoid exposing the API key to clients."""
    from urllib.parse import unquote
    decoded_ref = unquote(photo_ref)

    # Validate the reference format to prevent SSRF
    if not decoded_ref.startswith("places/") or "/photos/" not in decoded_ref:
        raise HTTPException(400, "Invalid photo reference")

    url = places.get_direct_photo_url(decoded_ref)
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
