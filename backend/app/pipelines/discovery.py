"""Discovery pipeline — Google Places API grounding for city content."""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.google.places import GooglePlacesService
from app.config.planning import (
    INTEREST_TO_TYPES,
    LODGING_TYPES,
    get_adaptive_place_filters,
)
from app.models.internal import PlaceCandidate

logger = logging.getLogger(__name__)

# Default cap for activity candidates returned by discovery.
DEFAULT_MAX_CANDIDATES: int = 80


@dataclass
class DiscoveryResult:
    """Result of a city discovery pipeline run."""

    city_metadata: dict[str, Any]  # geocode result: name, country, lat, lng, timezone, etc.
    candidates: list[dict[str, Any]]  # activity candidates (non-lodging), each with place_id
    lodging_candidates: list[dict[str, Any]]  # hotel candidates
    data_hash: str  # SHA-256 of sorted place_ids for refresh diff detection


class DiscoveryPipeline:
    """Discovers places in a city using Google Places API.

    Orchestrates geocoding, parallel nearby/text searches, deduplication,
    adaptive quality filtering, and lodging separation.
    """

    def __init__(self, places_service: GooglePlacesService):
        self.places = places_service

    async def discover(
        self,
        city_name: str,
        interests: list[str] | None = None,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
    ) -> DiscoveryResult:
        """Discover places in a city using Google Places API.

        1. Geocode the city
        2. Parallel: searchNearby per interest category + searchText (4 landmark queries) + lodging search
        3. Deduplicate by place_id
        4. Apply adaptive quality filters
        5. Separate lodging from activity candidates
        6. Compute data hash for refresh detection
        """
        # Step 1: Geocode
        city_metadata = await self.places.geocode(city_name)
        location = _make_location(city_metadata["lat"], city_metadata["lng"])

        # Step 2: Parallel discovery
        interest_list = interests or list(INTEREST_TO_TYPES.keys())

        tasks: list[asyncio.Task] = []

        # Nearby discovery per interest category
        tasks.append(asyncio.ensure_future(
            self.places.discover_places(location, interest_list)
        ))

        # Text search for landmarks (4 queries)
        landmark_queries = [
            f"famous landmarks in {city_name}",
            f"best places to visit in {city_name}",
            f"entertainment in {city_name}",
            f"nature parks gardens in {city_name}",
        ]
        for query in landmark_queries:
            tasks.append(asyncio.ensure_future(
                self.places.text_search_places(query, location, max_results=10)
            ))

        # Lodging search
        tasks.append(asyncio.ensure_future(
            self._discover_lodging(city_name, location)
        ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 3: Collect and deduplicate
        all_candidates: list[PlaceCandidate] = []
        lodging_candidates: list[PlaceCandidate] = []
        seen_ids: set[str] = set()

        # Last result is lodging
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Discovery task %d failed: %s", i, result)
                continue

            if i == len(results) - 1:
                # Lodging result (last task)
                for candidate in (result if isinstance(result, list) else []):
                    if candidate.place_id and candidate.place_id not in seen_ids:
                        seen_ids.add(candidate.place_id)
                        lodging_candidates.append(candidate)
                continue

            candidates_list = result if isinstance(result, list) else []
            for candidate in candidates_list:
                if not candidate.place_id or candidate.place_id in seen_ids:
                    continue
                seen_ids.add(candidate.place_id)

                # Separate lodging from activities
                if any(t in LODGING_TYPES for t in (candidate.types or [])):
                    lodging_candidates.append(candidate)
                else:
                    all_candidates.append(candidate)

        # Step 4: Quality filter
        filters = get_adaptive_place_filters(len(all_candidates))
        min_rating = filters["min_rating"]
        min_reviews = filters["min_ratings_count"]

        filtered = [
            c for c in all_candidates
            if (c.rating is not None and c.rating >= min_rating)
            and (c.user_ratings_total is not None and c.user_ratings_total >= min_reviews)
        ]

        # Sort by quality and cap
        filtered.sort(
            key=lambda c: (c.rating or 0, c.user_ratings_total or 0),
            reverse=True,
        )
        filtered = filtered[:max_candidates]

        # Step 5: Convert to dicts
        candidate_dicts = [self._candidate_to_dict(c) for c in filtered]
        lodging_dicts = [self._candidate_to_dict(c) for c in lodging_candidates]

        # Step 6: Compute data hash
        all_ids = sorted(
            [c["place_id"] for c in candidate_dicts + lodging_dicts]
        )
        data_hash = hashlib.sha256(json.dumps(all_ids).encode()).hexdigest()

        return DiscoveryResult(
            city_metadata=city_metadata,
            candidates=candidate_dicts,
            lodging_candidates=lodging_dicts,
            data_hash=data_hash,
        )

    async def _discover_lodging(self, city_name: str, location: Any) -> list[PlaceCandidate]:
        """Search for lodging options."""
        results: list[PlaceCandidate] = []
        queries = [
            f"hotels in {city_name}",
            f"boutique hotels {city_name}",
            f"hostels {city_name}",
        ]
        for query in queries:
            try:
                hotel = await self.places.search_lodging(query, location)
                if hotel:
                    results.append(hotel)
            except Exception as e:
                logger.warning("Lodging search failed for '%s': %s", query, e)
        return results

    def _candidate_to_dict(self, candidate: PlaceCandidate) -> dict[str, Any]:
        """Convert a PlaceCandidate to a plain dict."""
        return {
            "place_id": candidate.place_id,
            "name": candidate.name,
            "address": candidate.address,
            "location": {
                "lat": candidate.location.lat,
                "lng": candidate.location.lng,
            } if candidate.location else None,
            "types": candidate.types or [],
            "rating": candidate.rating,
            "user_rating_count": candidate.user_ratings_total,
            "price_level": candidate.price_level,
            "opening_hours": [
                oh.model_dump() for oh in (candidate.opening_hours or [])
            ],
            "photo_references": candidate.photo_references or [],
            "editorial_summary": candidate.editorial_summary,
            "website_url": candidate.website,
            "is_lodging": any(t in LODGING_TYPES for t in (candidate.types or [])),
            "business_status": candidate.business_status or "OPERATIONAL",
        }


def _make_location(lat: float, lng: float) -> Any:
    """Create a Location-like object from lat/lng."""
    from app.models.common import Location
    return Location(lat=lat, lng=lng)
