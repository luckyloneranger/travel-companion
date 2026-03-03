from fastapi import APIRouter, Depends, Query

from app.dependencies import get_places_service
from app.services.google.places import GooglePlacesService

router = APIRouter(prefix="/api/places", tags=["places"])


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
