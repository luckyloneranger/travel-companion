"""Google Places API service for place discovery and details."""

import logging
from typing import Optional, Self

import httpx

from app.config import get_settings
from app.config.planning import INTEREST_TYPE_MAP
from app.config.tuning import DISCOVERY
from app.core.clients import HTTPClientPool
from app.models import Destination, Location, PlaceCandidate, OpeningHours

logger = logging.getLogger(__name__)


class GooglePlacesService:
    """Service for interacting with Google Places API (New).
    
    Uses shared HTTP client from HTTPClientPool for connection pooling.
    """

    BASE_URL = "https://places.googleapis.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Google Places service."""
        settings = get_settings()
        self.api_key = api_key or settings.google_places_api_key

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the shared HTTP client."""
        return HTTPClientPool.get_places_client()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # No-op: HTTPClientPool manages lifecycle
        pass

    async def close(self):
        """Close method for backward compatibility.
        
        Note: Actual cleanup is handled by HTTPClientPool.close_all()
        """
        pass

    def _get_headers(self, field_mask: str) -> dict:
        """Get headers for Google Places API requests."""
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

    async def geocode(self, query: str) -> Destination:
        """
        Geocode a destination query to get location and details.

        Args:
            query: Destination name (e.g., "Paris, France")

        Returns:
            Destination with location, name, country, timezone
        """
        field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.utcOffsetMinutes"

        response = await self.client.post(
            f"{self.BASE_URL}/places:searchText",
            headers=self._get_headers(field_mask),
            json={
                "textQuery": query,
                "maxResultCount": 1,
            },
        )

        if response.status_code != 200:
            logger.error(f"Geocode failed: {response.text}")
            raise Exception(f"Geocode failed: {response.status_code}")

        data = response.json()
        if not data.get("places"):
            raise Exception(f"No results found for: {query}")

        place = data["places"][0]

        # Extract country from address components
        country = ""
        for component in place.get("addressComponents", []):
            if "country" in component.get("types", []):
                country = component.get("longText", "")
                break

        # Calculate timezone from UTC offset
        utc_offset = place.get("utcOffsetMinutes", 0)
        timezone = f"UTC{'+' if utc_offset >= 0 else ''}{utc_offset // 60}:00"

        return Destination(
            name=place["displayName"]["text"],
            place_id=place["id"],
            location=Location(
                lat=place["location"]["latitude"],
                lng=place["location"]["longitude"],
            ),
            country=country,
            timezone=timezone,
        )

    async def text_search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict]:
        """
        Search for places using free-form text query.
        
        Args:
            query: Search query (e.g., "tourist destinations in South India")
            max_results: Maximum number of results to return
            
        Returns:
            List of place dictionaries with displayName, formattedAddress, location, etc.
        """
        field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.addressComponents"
        
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/places:searchText",
                headers=self._get_headers(field_mask),
                json={
                    "textQuery": query,
                    "maxResultCount": min(max_results, 20),  # API max is 20
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Text search failed: {response.text}")
                return []
            
            data = response.json()
            return data.get("places", [])
            
        except Exception as e:
            logger.error(f"Text search error for '{query}': {e}")
            return []

    async def discover_places(
        self,
        location: Location,
        interests: list[str],
        radius_km: float = DISCOVERY.default_radius_km,
    ) -> list[PlaceCandidate]:
        """
        Discover candidate places near a location based on interests.

        Args:
            location: Center point for search
            interests: List of interest categories
            radius_km: Search radius in kilometers

        Returns:
            List of PlaceCandidate objects with real data
        """
        all_candidates = []
        seen_place_ids = set()

        # ALWAYS fetch major tourist attractions first (essential for any trip)
        essential_types = [
            ["tourist_attraction"],
            ["museum"],
            ["historical_landmark", "monument"],
            ["park"],
        ]
        
        for place_types in essential_types:
            try:
                candidates = await self._nearby_search(
                    location=location,
                    included_types=place_types,
                    radius_meters=int(radius_km * 1000),
                    max_results=10,
                )
                for candidate in candidates:
                    if candidate.place_id not in seen_place_ids:
                        seen_place_ids.add(candidate.place_id)
                        all_candidates.append(candidate)
            except Exception as e:
                logger.error(f"Failed to search for essential types {place_types}: {e}")

        # ALWAYS fetch dining options (needed for lunch/dinner)
        dining_types = ["restaurant", "cafe"]
        try:
            candidates = await self._nearby_search(
                location=location,
                included_types=dining_types,
                radius_meters=int(radius_km * 1000),
                max_results=15,
            )
            for candidate in candidates:
                if candidate.place_id not in seen_place_ids:
                    seen_place_ids.add(candidate.place_id)
                    all_candidates.append(candidate)
        except Exception as e:
            logger.error(f"Failed to search for dining: {e}")

        # Then fetch based on user interests
        for interest in interests:
            place_types = INTEREST_TYPE_MAP.get(interest.lower(), ["tourist_attraction"])

            try:
                candidates = await self._nearby_search(
                    location=location,
                    included_types=place_types,
                    radius_meters=int(radius_km * 1000),
                    max_results=10,
                )

                for candidate in candidates:
                    if candidate.place_id not in seen_place_ids:
                        seen_place_ids.add(candidate.place_id)
                        all_candidates.append(candidate)

            except Exception as e:
                logger.error(f"Failed to search for {interest}: {e}")
                continue

        # Quality filtering and scoring
        filtered = self._filter_and_rank_by_quality(all_candidates)

        logger.info(f"Discovered {len(filtered)} places from {len(interests)} interests")
        return filtered
    
    def _filter_and_rank_by_quality(
        self, 
        candidates: list[PlaceCandidate],
        min_rating: float = DISCOVERY.min_rating,
        min_reviews_for_high_rating: int = DISCOVERY.min_reviews_high_rating,
        min_reviews_for_any: int = DISCOVERY.min_reviews_any,
    ) -> list[PlaceCandidate]:
        """
        Filter and rank places by quality score.
        
        PHILOSOPHY: Be inclusive, let LLM decide.
        We only filter out places that are clearly problematic:
        1. Permanently closed
        2. Extremely low ratings (< 2.5) with many reviews (clearly bad)
        
        Everything else passes - LLM makes contextual decisions about fit.
        """
        import math
        
        quality_places = []
        
        # Types that are inherently valuable (famous landmarks, cultural sites)
        valuable_types = {
            "monument", "historical_landmark", "tourist_attraction", "museum",
            "church", "hindu_temple", "mosque", "synagogue", "national_park",
            "art_gallery", "performing_arts_theater", "stadium", "zoo", "aquarium"
        }
        
        for c in candidates:
            # Only skip permanently closed places
            if c.business_status == "CLOSED_PERMANENTLY":
                continue
            
            rating = c.rating or 0
            reviews = c.user_ratings_total or 0
            is_valuable_type = bool(set(c.types) & valuable_types)
            
            # Very inclusive filtering:
            # 1. Pass places with decent ratings (>= min_rating) and any reviews
            # 2. Pass places with no rating data (new places, landmarks)
            # 3. Pass valuable types regardless of rating
            # 4. Only exclude if clearly bad: low rating WITH many negative reviews
            passes_filter = False
            
            if rating == 0 or rating is None:
                # No rating data - include it (could be new or unrated landmark)
                passes_filter = True
            elif rating >= min_rating:
                # Meets minimum rating threshold
                passes_filter = True
            elif is_valuable_type:
                # Valuable type - include even with lower rating
                passes_filter = True
            elif rating >= 2.5 or reviews < 50:
                # Not clearly bad, or not enough reviews to judge
                passes_filter = True
            # Only excluded: rating < 2.5 AND reviews >= 50 (clearly problematic)
            
            if passes_filter:
                quality_places.append(c)
        
        # Sort by quality score: rating * log(reviews + 1)
        # This surfaces well-reviewed places while still including newer ones
        def quality_score(c: PlaceCandidate) -> float:
            r = c.rating or 3.5  # Default for unrated
            n = c.user_ratings_total or 1
            return r * math.log(n + 1)
        
        quality_places.sort(key=quality_score, reverse=True)
        
        logger.info(
            f"Quality filter: {len(candidates)} candidates -> {len(quality_places)} passed "
            f"(min_rating={min_rating})"
        )
        
        return quality_places

    async def search_nearby(
        self,
        location: Location,
        included_types: list[str],
        radius_meters: int,
        max_results: int = DISCOVERY.max_results_per_search,
    ) -> list[PlaceCandidate]:
        """
        Search for places near a location.

        Uses Google Places Nearby Search (New) API.
        """
        return await self._nearby_search_impl(location, included_types, radius_meters, max_results)

    async def _nearby_search(
        self,
        location: Location,
        included_types: list[str],
        radius_meters: int,
        max_results: int = DISCOVERY.max_results_per_search,
    ) -> list[PlaceCandidate]:
        """Deprecated: Use search_nearby instead."""
        return await self._nearby_search_impl(location, included_types, radius_meters, max_results)

    async def _nearby_search_impl(
        self,
        location: Location,
        included_types: list[str],
        radius_meters: int,
        max_results: int = DISCOVERY.max_results_per_search,
    ) -> list[PlaceCandidate]:
        """
        Internal implementation of nearby search.

        Uses Google Places Nearby Search (New) API.
        """
        field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.rating,places.userRatingCount,places.priceLevel,places.regularOpeningHours,places.photos,places.businessStatus"

        response = await self.client.post(
            f"{self.BASE_URL}/places:searchNearby",
            headers=self._get_headers(field_mask),
            json={
                "includedTypes": included_types,
                "maxResultCount": max_results,
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": location.lat,
                            "longitude": location.lng,
                        },
                        "radius": float(radius_meters),
                    }
                },
                "rankPreference": "POPULARITY",
            },
        )

        if response.status_code != 200:
            logger.error(f"Nearby search failed: {response.text}")
            return []

        data = response.json()
        places = data.get("places", [])

        candidates = []
        for place in places:
            # Parse opening hours if available
            opening_hours = None
            if "regularOpeningHours" in place:
                opening_hours = self._parse_opening_hours(place["regularOpeningHours"])

            # Get first photo reference if available
            photo_ref = None
            if place.get("photos"):
                photo_ref = place["photos"][0].get("name")

            candidates.append(
                PlaceCandidate(
                    place_id=place["id"],
                    name=place["displayName"]["text"],
                    address=place.get("formattedAddress", ""),
                    location=Location(
                        lat=place["location"]["latitude"],
                        lng=place["location"]["longitude"],
                    ),
                    types=place.get("types", []),
                    rating=place.get("rating"),
                    user_ratings_total=place.get("userRatingCount"),
                    price_level=self._parse_price_level(place.get("priceLevel")),
                    opening_hours=opening_hours,
                    photo_reference=photo_ref,
                    business_status=place.get("businessStatus"),
                )
            )

        return candidates

    def _parse_opening_hours(self, hours_data: dict) -> list[OpeningHours]:
        """Parse Google's opening hours format to our model."""
        periods = hours_data.get("periods", [])
        result = []

        for period in periods:
            open_info = period.get("open", {})
            close_info = period.get("close", {})

            if open_info.get("day") is not None:
                result.append(
                    OpeningHours(
                        day=open_info["day"],
                        open_time=f"{open_info.get('hour', 0):02d}:{open_info.get('minute', 0):02d}",
                        close_time=f"{close_info.get('hour', 23):02d}:{close_info.get('minute', 59):02d}",
                    )
                )

        return result

    def _parse_price_level(self, price_level: Optional[str]) -> Optional[int]:
        """Convert Google's price level enum to integer."""
        if price_level is None:
            return None
        mapping = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        return mapping.get(price_level)

    async def get_place_details(self, place_id: str) -> dict:
        """
        Get detailed information about a specific place.

        Args:
            place_id: Google Place ID

        Returns:
            Place details including photos, website, phone, etc.
        """
        field_mask = "id,displayName,formattedAddress,location,types,rating,userRatingCount,regularOpeningHours,photos,website,nationalPhoneNumber,priceLevel"

        response = await self.client.get(
            f"{self.BASE_URL}/places/{place_id}",
            headers=self._get_headers(field_mask),
        )

        if response.status_code != 200:
            logger.error(f"Place details failed: {response.text}")
            raise Exception(f"Failed to get place details: {response.status_code}")

        return response.json()

    def get_photo_url(self, photo_reference: str, max_width: int = 400) -> str:
        """
        Generate a photo URL for a place photo.

        Args:
            photo_reference: Photo reference from Places API
            max_width: Maximum width in pixels

        Returns:
            URL to fetch the photo
        """
        return f"{self.BASE_URL}/{photo_reference}/media?maxWidthPx={max_width}&key={self.api_key}"
