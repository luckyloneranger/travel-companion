"""Google Places API (New) service.

Uses the Places API (New) — field-mask based endpoints at
``https://places.googleapis.com/v1``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.models.common import Location
from app.models.internal import OpeningHours, PlaceCandidate

logger = logging.getLogger(__name__)

BASE_URL = "https://places.googleapis.com/v1"
from app.config.planning import GOOGLE_API_TIMEOUT as REQUEST_TIMEOUT, PLACES_MIN_RATING as MIN_RATING, PLACES_MIN_RATINGS_COUNT as MIN_RATINGS_COUNT, PLACES_DISCOVERY_RADIUS_KM, LODGING_TYPES

from app.config.planning import INTEREST_TO_TYPES as INTEREST_TYPE_MAP

# Types we always include, but skip if the user's interests already cover them.
DEFAULT_ESSENTIAL_TYPES: list[str] = [
    "tourist_attraction",
    "museum",
    "park",
    "historical_landmark",
]

DINING_TYPES: list[str] = ["restaurant", "cafe", "bakery"]


def _get_essential_types(interests: list[str]) -> list[str]:
    """Return essential place types, filtering out those already covered by interests.

    For example, if the user's interests include 'nature' (which maps to 'park',
    'national_park', etc.), there's no need to also search 'park' as an essential.
    """
    interest_types: set[str] = set()
    for interest in interests:
        key = interest.lower().strip()
        if key in INTEREST_TYPE_MAP:
            interest_types.update(INTEREST_TYPE_MAP[key])
    return [t for t in DEFAULT_ESSENTIAL_TYPES if t not in interest_types]


class GooglePlacesService:
    """Thin async wrapper around the Google Places API (New).

    Parameters
    ----------
    api_key:
        Google API key with Places API (New) enabled.
    client:
        Shared ``httpx.AsyncClient`` — the caller owns its lifecycle.
    """

    def __init__(self, api_key: str, client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.client = client

    # ── Public methods ──────────────────────────────────────────────────

    async def geocode(self, query: str) -> dict[str, Any]:
        """Geocode a place name and return basic info.

        Returns a dict with keys: ``name``, ``place_id``, ``lat``, ``lng``,
        ``country``, ``timezone``.
        """
        url = f"{BASE_URL}/places:searchText"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.id,places.location,"
                "places.addressComponents,places.utcOffsetMinutes,"
                "places.formattedAddress"
            ),
        }
        body = {"textQuery": query, "maxResultCount": 1}

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Geocode HTTP error for %r: %s", query, exc)
            raise
        except httpx.RequestError as exc:
            logger.error("Geocode request error for %r: %s", query, exc)
            raise

        places = data.get("places", [])
        if not places:
            raise ValueError(f"No geocode results for query: {query!r}")

        place = places[0]
        loc = place.get("location", {})
        country = self._extract_country(place.get("addressComponents", []))
        utc_offset = place.get("utcOffsetMinutes")
        timezone = self._offset_to_timezone(utc_offset) if utc_offset is not None else ""

        return {
            "name": place.get("displayName", {}).get("text", query),
            "place_id": place.get("id", ""),
            "lat": loc.get("latitude", 0.0),
            "lng": loc.get("longitude", 0.0),
            "country": country,
            "timezone": timezone,
            "utc_offset_minutes": utc_offset,
        }

    async def discover_places(
        self,
        location: Location,
        interests: list[str],
        radius_km: float = PLACES_DISCOVERY_RADIUS_KM,
        price_levels: list[str] | None = None,
    ) -> list[PlaceCandidate]:
        """Discover places near *location* based on interests.

        Runs parallel nearby searches for essential types, interest-derived
        types, and dining types, then deduplicates and quality-filters.
        """
        # Build unique type sets from interests.
        interest_types: set[str] = set()
        for interest in interests:
            key = interest.lower().strip()
            if key in INTEREST_TYPE_MAP:
                interest_types.update(INTEREST_TYPE_MAP[key])

        # Compute essential types that aren't already covered by interests
        essential_types = _get_essential_types(interests)

        # Remove types already covered by essentials.
        interest_types -= set(essential_types)
        # Remove dining if already present.
        interest_types -= set(DINING_TYPES)

        radius_meters = radius_km * 1000

        # Run all category searches in parallel.
        tasks: list[asyncio.Task[list[PlaceCandidate]]] = []

        # Essential types (interest-aware)
        for t in essential_types:
            tasks.append(
                asyncio.ensure_future(
                    self._nearby_search(location, [t], radius_meters)
                )
            )

        # Interest types
        for t in interest_types:
            tasks.append(
                asyncio.ensure_future(
                    self._nearby_search(location, [t], radius_meters)
                )
            )

        # Dining
        tasks.append(
            asyncio.ensure_future(
                self._nearby_search(location, DINING_TYPES, radius_meters)
            )
        )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_places: list[PlaceCandidate] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Nearby search failed: %s", result)
                continue
            all_places.extend(result)

        # Dynamic radius expansion for sparse results
        if len(all_places) < 5:
            logger.info("[Places] Sparse results (%d) — expanding search radius to 15km", len(all_places))
            # Build type batches from all categories used above
            type_batches: list[list[str]] = [[t] for t in essential_types]
            type_batches.extend([[t] for t in interest_types])
            type_batches.append(DINING_TYPES)
            for types_batch in type_batches:
                expanded = await self._nearby_search(
                    location=location,
                    included_types=types_batch,
                    radius_meters=15000,
                    max_results=10,
                )
                existing_ids = {p.place_id for p in all_places}
                for p in expanded:
                    if p.place_id not in existing_ids:
                        all_places.append(p)
                        existing_ids.add(p.place_id)

        # Deduplicate by place_id and quality-filter.
        return self._filter_and_rank_by_quality(all_places)

    async def search_lodging(
        self,
        query: str,
        location: Location,
        radius_meters: int = 10_000,
    ) -> PlaceCandidate | None:
        """Search for a lodging option near *location*.

        Returns the top-rated lodging ``PlaceCandidate`` or ``None``.
        """
        url = f"{BASE_URL}/places:searchText"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.types,places.rating,"
                "places.userRatingCount,places.priceLevel,"
                "places.regularOpeningHours,places.photos,"
                "places.websiteUri,places.editorialSummary"
            ),
        }
        body: dict[str, Any] = {
            "textQuery": query,
            "includedType": "lodging",
            "maxResultCount": 5,
            "locationBias": {
                "circle": {
                    "center": {"latitude": location.lat, "longitude": location.lng},
                    "radius": float(radius_meters),
                }
            },
        }

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Lodging search error for %r: %s", query, exc)
            return None

        places = data.get("places", [])
        if not places:
            return None

        # Pick highest-rated result.
        best = max(places, key=lambda p: p.get("rating", 0))
        return self._parse_place(best)

    async def text_search_places(
        self,
        query: str,
        location: Location,
        radius_meters: int = 15_000,
        max_results: int = 5,
        price_levels: list[str] | None = None,
    ) -> list[PlaceCandidate]:
        """Text search returning PlaceCandidate objects, biased to a location.

        Useful for finding specific named attractions (e.g. "Coffee Plantation
        Walk Coorg") that nearby-by-type searches would miss.
        """
        url = f"{BASE_URL}/places:searchText"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.types,places.rating,"
                "places.userRatingCount,places.priceLevel,"
                "places.regularOpeningHours,places.photos,"
                "places.websiteUri,places.editorialSummary,"
                "places.goodForChildren,places.goodForGroups,"
                "places.servesVegetarianFood,places.servesBrunch,"
                "places.servesLunch,places.servesDinner"
            ),
        }
        body: dict[str, Any] = {
            "textQuery": query,
            "maxResultCount": min(max_results, 20),
            "locationBias": {
                "circle": {
                    "center": {"latitude": location.lat, "longitude": location.lng},
                    "radius": float(radius_meters),
                }
            },
        }

        if price_levels:
            body["priceLevels"] = price_levels

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("Text search error for %r: %s", query, exc)
            return []

        return [self._parse_place(p) for p in data.get("places", [])]

    async def text_search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Free-text search returning raw place dicts."""
        url = f"{BASE_URL}/places:searchText"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.types,places.rating,"
                "places.userRatingCount,places.photos,"
                "places.editorialSummary"
            ),
        }
        body = {"textQuery": query, "maxResultCount": min(max_results, 20)}

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Text search error for %r: %s", query, exc)
            return []

        results: list[dict[str, Any]] = []
        for p in data.get("places", []):
            loc = p.get("location", {})
            photos = p.get("photos", [])
            photo_ref = photos[0].get("name", "") if photos else None
            results.append(
                {
                    "place_id": p.get("id", ""),
                    "name": p.get("displayName", {}).get("text", ""),
                    "address": p.get("formattedAddress", ""),
                    "lat": loc.get("latitude", 0.0),
                    "lng": loc.get("longitude", 0.0),
                    "types": p.get("types", []),
                    "rating": p.get("rating"),
                    "user_ratings_total": p.get("userRatingCount"),
                    "photo_reference": photo_ref,
                    "editorial_summary": (
                        p.get("editorialSummary", {}).get("text")
                        if p.get("editorialSummary")
                        else None
                    ),
                }
            )
        return results

    async def discover_landmarks(
        self, destination: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Discover a destination's most popular attractions by review count.

        Uses multiple search queries to cast a wide net (landmarks, theme
        parks, nature, best places), deduplicates, and guarantees diversity
        by taking top results per query before merging.
        No hardcoded names — Google's review data determines what's iconic.
        """
        queries = [
            f"top attractions and landmarks in {destination}",
            f"best places to visit {destination}",
            f"theme parks and entertainment in {destination}",
            f"famous natural landmarks and scenic spots in {destination}",
        ]
        import asyncio as _asyncio
        results_lists = await _asyncio.gather(
            *(self.text_search(q, max_results=15) for q in queries),
            return_exceptions=True,
        )
        # Take top results per query to ensure category diversity,
        # then merge and sort globally. This prevents urban attractions
        # from drowning out nature/scenic results.
        per_query_limit = max(max_results // len(queries), 5)
        seen: set[str] = set()
        all_results: list[dict[str, Any]] = []
        for results in results_lists:
            if isinstance(results, Exception):
                continue
            count = 0
            for r in results:
                pid = r.get("place_id", "")
                if pid and pid not in seen:
                    seen.add(pid)
                    all_results.append(r)
                    count += 1
                    if count >= per_query_limit:
                        break
        all_results.sort(key=lambda p: p.get("user_ratings_total") or 0, reverse=True)
        return all_results[:max_results]

    async def discover_destination_landscape(
        self, destination: str
    ) -> str:
        """Discover what types of experiences a destination offers.

        Returns a formatted landscape summary for Scout context — categorized
        by type with top attractions by review count. Used to inform Scout's
        experience_themes, NOT for specific attraction selection.
        """
        landmarks = await self.discover_landmarks(destination, max_results=30)
        if not landmarks:
            return ""

        categories: dict[str, list[dict[str, Any]]] = {
            "Theme parks & entertainment": [],
            "Nature & wildlife": [],
            "Cultural & historical": [],
            "Religious & spiritual": [],
            "Shopping & markets": [],
            "Landmarks & viewpoints": [],
            "Other attractions": [],
        }

        type_map = {
            "amusement_park": "Theme parks & entertainment",
            "theme_park": "Theme parks & entertainment",
            "water_park": "Theme parks & entertainment",
            "zoo": "Nature & wildlife",
            "aquarium": "Nature & wildlife",
            "park": "Nature & wildlife",
            "national_park": "Nature & wildlife",
            "garden": "Nature & wildlife",
            "mountain_peak": "Nature & wildlife",
            "natural_feature": "Nature & wildlife",
            "scenic_spot": "Nature & wildlife",
            "hiking_area": "Nature & wildlife",
            "wildlife_park": "Nature & wildlife",
            "nature_preserve": "Nature & wildlife",
            "museum": "Cultural & historical",
            "art_gallery": "Cultural & historical",
            "historical_landmark": "Cultural & historical",
            "monument": "Cultural & historical",
            "castle": "Cultural & historical",
            "temple": "Religious & spiritual",
            "church": "Religious & spiritual",
            "mosque": "Religious & spiritual",
            "hindu_temple": "Religious & spiritual",
            "buddhist_temple": "Religious & spiritual",
            "shinto_shrine": "Religious & spiritual",
            "shopping_mall": "Shopping & markets",
            "market": "Shopping & markets",
            "tourist_attraction": "Landmarks & viewpoints",
        }

        for lm in landmarks:
            placed = False
            for t in lm.get("types", []):
                if t in type_map:
                    categories[type_map[t]].append(lm)
                    placed = True
                    break
            if not placed:
                categories["Other attractions"].append(lm)

        lines = [
            "## DESTINATION LANDSCAPE (from Google data)",
            f"Top experiences available in {destination} by visitor popularity:",
            "",
        ]
        for cat_name, places in categories.items():
            if places:
                top = ", ".join(
                    f"{p['name']} ({p.get('user_ratings_total', 0):,} reviews)"
                    for p in places[:3]
                )
                lines.append(f"- **{cat_name}**: {top}")

        lines.append("")
        lines.append("Use this landscape to set experience_themes and allocate days.")
        lines.append("Do NOT copy specific attraction names — describe experience categories instead.")

        return "\n".join(lines)

    async def get_place_details(self, place_id: str) -> dict[str, Any]:
        """Fetch full details for a single place by its ID."""
        url = f"{BASE_URL}/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,location,types,"
                "rating,userRatingCount,priceLevel,"
                "regularOpeningHours,photos,websiteUri,"
                "editorialSummary,currentOpeningHours"
            ),
        }

        try:
            resp = await self.client.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Place details error for %r: %s", place_id, exc)
            return {}

        loc = data.get("location", {})
        photos = data.get("photos", [])
        photo_ref = photos[0].get("name", "") if photos else None
        opening_hours = self._parse_opening_hours(
            data.get("regularOpeningHours", {})
        )

        return {
            "place_id": data.get("id", place_id),
            "name": data.get("displayName", {}).get("text", ""),
            "address": data.get("formattedAddress", ""),
            "lat": loc.get("latitude", 0.0),
            "lng": loc.get("longitude", 0.0),
            "types": data.get("types", []),
            "rating": data.get("rating"),
            "user_ratings_total": data.get("userRatingCount"),
            "price_level": self._parse_price_level(data.get("priceLevel")),
            "opening_hours": [oh.model_dump() for oh in opening_hours],
            "photo_reference": photo_ref,
            "website": data.get("websiteUri"),
            "editorial_summary": (
                data.get("editorialSummary", {}).get("text")
                if data.get("editorialSummary")
                else None
            ),
        }

    def get_photo_url(
        self, photo_reference: str, max_width: int = 400
    ) -> str:
        """Build a proxied photo URL that does not expose the API key.

        *photo_reference* is the ``name`` field from the Photos array,
        e.g. ``places/PLACE_ID/photos/PHOTO_REF``.
        """
        from urllib.parse import quote
        return f"/api/places/photo/{quote(photo_reference, safe='')}"

    def get_direct_photo_url(
        self, photo_reference: str, max_width: int = 400
    ) -> str:
        """Build the direct Google Places photo URL (server-side only)."""
        return (
            f"{BASE_URL}/{photo_reference}/media"
            f"?maxWidthPx={max_width}&key={self.api_key}"
        )

    # ── Private helpers ─────────────────────────────────────────────────

    async def _nearby_search(
        self,
        location: Location,
        included_types: list[str],
        radius_meters: float,
        max_results: int = 20,
        price_levels: list[str] | None = None,
    ) -> list[PlaceCandidate]:
        """Run a nearby search for the given place types."""
        url = f"{BASE_URL}/places:searchNearby"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.types,places.rating,"
                "places.userRatingCount,places.priceLevel,"
                "places.regularOpeningHours,places.currentOpeningHours,"
                "places.photos,places.websiteUri,places.editorialSummary,"
                "places.businessStatus,"
                "places.goodForChildren,places.goodForGroups,"
                "places.servesVegetarianFood,places.servesBrunch,"
                "places.servesLunch,places.servesDinner"
            ),
        }
        body: dict[str, Any] = {
            "includedTypes": included_types,
            "maxResultCount": min(max_results, 20),
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": location.lat,
                        "longitude": location.lng,
                    },
                    "radius": radius_meters,
                }
            },
            "rankPreference": "POPULARITY",
        }

        if price_levels:
            body["priceLevels"] = price_levels

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Nearby search HTTP error for types %s: %s",
                included_types,
                exc,
            )
            return []
        except httpx.RequestError as exc:
            logger.warning(
                "Nearby search request error for types %s: %s",
                included_types,
                exc,
            )
            return []

        return [
            self._parse_place(p)
            for p in data.get("places", [])
        ]

    def _parse_place(self, raw: dict[str, Any]) -> PlaceCandidate:
        """Convert a raw Places API (New) response object to a ``PlaceCandidate``."""
        loc = raw.get("location", {})
        photos = raw.get("photos", [])
        photo_ref = photos[0].get("name", "") if photos else None
        photo_refs = [p.get("name", "") for p in photos[:3] if p.get("name")]

        # Prefer currentOpeningHours (accounts for holidays/temp closures)
        # over regularOpeningHours
        hours_data = raw.get("currentOpeningHours") or raw.get("regularOpeningHours", {})
        opening_hours = self._parse_opening_hours(hours_data)

        return PlaceCandidate(
            place_id=raw.get("id", ""),
            name=raw.get("displayName", {}).get("text", ""),
            address=raw.get("formattedAddress", ""),
            location=Location(
                lat=loc.get("latitude", 0.0),
                lng=loc.get("longitude", 0.0),
            ),
            types=raw.get("types", []),
            rating=raw.get("rating"),
            user_ratings_total=raw.get("userRatingCount"),
            price_level=self._parse_price_level(raw.get("priceLevel")),
            opening_hours=opening_hours if opening_hours else None,
            business_status=raw.get("businessStatus"),
            photo_reference=photo_ref,
            photo_references=photo_refs,
            website=raw.get("websiteUri"),
            editorial_summary=(
                raw.get("editorialSummary", {}).get("text")
                if raw.get("editorialSummary")
                else None
            ),
            good_for_children=raw.get("goodForChildren"),
            good_for_groups=raw.get("goodForGroups"),
            serves_vegetarian_food=raw.get("servesVegetarianFood"),
            serves_brunch=raw.get("servesBrunch"),
            serves_lunch=raw.get("servesLunch"),
            serves_dinner=raw.get("servesDinner"),
        )

    @staticmethod
    def _parse_opening_hours(
        hours_data: dict[str, Any],
    ) -> list[OpeningHours]:
        """Parse ``regularOpeningHours`` from the Places API (New) into
        a list of ``OpeningHours`` models.
        """
        if not hours_data:
            return []

        periods = hours_data.get("periods", [])
        result: list[OpeningHours] = []

        for period in periods:
            open_info = period.get("open", {})
            close_info = period.get("close", {})
            day = open_info.get("day")
            if day is None:
                continue

            open_hour = open_info.get("hour", 0)
            open_minute = open_info.get("minute", 0)
            close_hour = close_info.get("hour", 23)
            close_minute = close_info.get("minute", 59)

            result.append(
                OpeningHours(
                    day=day,
                    open_time=f"{open_hour:02d}:{open_minute:02d}",
                    close_time=f"{close_hour:02d}:{close_minute:02d}",
                )
            )

        return result

    @staticmethod
    def _parse_price_level(raw_level: Any) -> int | None:
        """Normalise price level from API enum strings or ints to 0-4 int."""
        if raw_level is None:
            return None

        if isinstance(raw_level, int):
            return max(0, min(raw_level, 4))

        # The new API returns enum strings like "PRICE_LEVEL_MODERATE".
        mapping: dict[str, int] = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        return mapping.get(str(raw_level))

    @staticmethod
    def _filter_and_rank_by_quality(
        candidates: list[PlaceCandidate],
    ) -> list[PlaceCandidate]:
        """Deduplicate by ``place_id`` and keep only quality places.

        Quality thresholds:
        - rating >= ``MIN_RATING``
        - user_ratings_total >= ``MIN_RATINGS_COUNT``
        - business_status is OPERATIONAL (or unknown)

        Sorted by (rating descending, user_ratings_total descending).
        """
        # Non-operational statuses to exclude
        _CLOSED_STATUSES = {"CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"}

        seen: set[str] = set()
        unique: list[PlaceCandidate] = []
        for c in candidates:
            if c.place_id in seen:
                continue
            seen.add(c.place_id)
            unique.append(c)

        filtered = [
            c
            for c in unique
            if (c.rating is not None and c.rating >= MIN_RATING)
            and (
                c.user_ratings_total is not None
                and c.user_ratings_total >= MIN_RATINGS_COUNT
            )
            and (c.business_status is None or c.business_status not in _CLOSED_STATUSES)
            and not any(t in LODGING_TYPES for t in c.types)
        ]

        filtered.sort(
            key=lambda c: (c.rating or 0, c.user_ratings_total or 0),
            reverse=True,
        )
        return filtered

    # ── Geocode helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_country(components: list[dict[str, Any]]) -> str:
        """Pull the country short name from ``addressComponents``."""
        for comp in components:
            types = comp.get("types", [])
            if "country" in types:
                return comp.get("shortText", comp.get("longText", ""))
        return ""

    @staticmethod
    def _offset_to_timezone(offset_minutes: int) -> str:
        """Convert UTC-offset minutes to a rough ``+HH:MM`` string.

        This is a best-effort approximation; a proper timezone database
        lookup is beyond this helper's scope.
        """
        sign = "+" if offset_minutes >= 0 else "-"
        total = abs(offset_minutes)
        hours = total // 60
        minutes = total % 60
        return f"UTC{sign}{hours:02d}:{minutes:02d}"
