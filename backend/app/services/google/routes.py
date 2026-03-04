"""Google Routes API service.

Wraps the ``https://routes.googleapis.com`` endpoints for computing
single routes, batch routes, and distance matrices.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from app.models.common import Location, TravelMode
from app.models.day_plan import Route

logger = logging.getLogger(__name__)

BASE_URL = "https://routes.googleapis.com"
REQUEST_TIMEOUT = 15.0

# Fallback values when the API call fails or returns no data.
FALLBACK_DISTANCE_METERS = 800
FALLBACK_DURATION_SECONDS = 720


class GoogleRoutesService:
    """Async wrapper around the Google Routes API.

    Parameters
    ----------
    api_key:
        Google API key with Routes API enabled.
    client:
        Shared ``httpx.AsyncClient`` — the caller owns its lifecycle.
    """

    def __init__(self, api_key: str, client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.client = client

    # ── Travel-mode mapping ─────────────────────────────────────────────

    _MODE_MAP: dict[TravelMode, str] = {
        TravelMode.WALK: "WALK",
        TravelMode.DRIVE: "DRIVE",
        TravelMode.TRANSIT: "TRANSIT",
    }

    # ── Public methods ──────────────────────────────────────────────────

    async def compute_route(
        self,
        origin: Location,
        destination: Location,
        mode: TravelMode = TravelMode.WALK,
    ) -> Route:
        """Compute a single route between *origin* and *destination*.

        Returns a ``Route`` model. Falls back to heuristic estimates on
        API failure.
        """
        url = f"{BASE_URL}/directions/v2:computeRoutes"
        travel_mode = self._MODE_MAP.get(mode, "WALK")

        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "routes.duration,routes.distanceMeters,"
                "routes.polyline.encodedPolyline"
            ),
        }
        body: dict[str, Any] = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin.lat,
                        "longitude": origin.lng,
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination.lat,
                        "longitude": destination.lng,
                    }
                }
            },
            "travelMode": travel_mode,
            "routingPreference": (
                "TRAFFIC_AWARE" if mode == TravelMode.DRIVE else "ROUTING_PREFERENCE_UNSPECIFIED"
            ),
        }

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning(
                "Route computation failed (%s -> %s, mode=%s): %s",
                origin,
                destination,
                mode,
                exc,
            )
            return self._fallback_route(mode)

        routes = data.get("routes", [])
        if not routes:
            logger.warning(
                "No routes returned (%s -> %s, mode=%s)",
                origin,
                destination,
                mode,
            )
            return self._fallback_route(mode)

        route = routes[0]
        distance = route.get("distanceMeters", FALLBACK_DISTANCE_METERS)
        duration_raw = route.get("duration", f"{FALLBACK_DURATION_SECONDS}s")
        duration_secs = self._parse_duration(duration_raw)
        polyline = route.get("polyline", {}).get("encodedPolyline")

        return Route(
            distance_meters=distance,
            duration_seconds=duration_secs,
            duration_text=self._format_duration(duration_secs),
            travel_mode=mode,
            polyline=polyline,
        )

    async def compute_routes_batch(
        self,
        pairs: list[tuple[Location, Location]],
        mode: TravelMode = TravelMode.WALK,
    ) -> list[Route]:
        """Compute routes for multiple origin/destination pairs in parallel.

        Each pair is ``(origin, destination)``. Returns a list of ``Route``
        in the same order as *pairs*.
        """
        tasks = [
            asyncio.ensure_future(self.compute_route(orig, dest, mode))
            for orig, dest in pairs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        routes: list[Route] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Batch route failed: %s", r)
                routes.append(self._fallback_route(mode))
            else:
                routes.append(r)
        return routes

    async def compute_best_route(
        self,
        origin: Location,
        destination: Location,
    ) -> Route:
        """Compute routes for WALK and DRIVE in parallel, return the best one.

        Selection logic:
        - If walk <= 20 min, prefer walk (healthier, no parking hassle).
        - If walk <= 1.5x drive time, prefer walk (close enough).
        - Otherwise, use the faster mode (drive).

        Falls back to walk-only on errors.
        """
        walk_task = asyncio.ensure_future(
            self.compute_route(origin, destination, TravelMode.WALK)
        )
        drive_task = asyncio.ensure_future(
            self.compute_route(origin, destination, TravelMode.DRIVE)
        )

        results = await asyncio.gather(walk_task, drive_task, return_exceptions=True)

        walk_route = results[0] if not isinstance(results[0], Exception) else None
        drive_route = results[1] if not isinstance(results[1], Exception) else None

        # If only one succeeded, return it
        if walk_route and not drive_route:
            return walk_route
        if drive_route and not walk_route:
            return drive_route
        if not walk_route and not drive_route:
            return self._fallback_route(TravelMode.WALK)

        # Both succeeded — pick the better option
        walk_secs = walk_route.duration_seconds
        drive_secs = drive_route.duration_seconds

        # Prefer walking for short trips (<=20 min) or when it's
        # not much slower than driving (<=1.5x).
        if walk_secs <= 1200:  # 20 minutes
            return walk_route
        if drive_secs > 0 and walk_secs <= drive_secs * 1.5:
            return walk_route

        return drive_route

    async def get_distance_matrix(
        self,
        origins: list[Location],
        destinations: list[Location],
        mode: TravelMode = TravelMode.WALK,
    ) -> dict[str, Any]:
        """Compute a distance matrix via the Routes API.

        Returns a dict with ``rows`` where each row contains ``elements``
        with ``distance_meters`` and ``duration_seconds``.
        """
        url = f"{BASE_URL}/distanceMatrix/v2:computeRouteMatrix"
        travel_mode = self._MODE_MAP.get(mode, "WALK")

        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "originIndex,destinationIndex,"
                "duration,distanceMeters,status"
            ),
        }

        origin_waypoints = [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": loc.lat,
                            "longitude": loc.lng,
                        }
                    }
                }
            }
            for loc in origins
        ]
        dest_waypoints = [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": loc.lat,
                            "longitude": loc.lng,
                        }
                    }
                }
            }
            for loc in destinations
        ]

        body: dict[str, Any] = {
            "origins": origin_waypoints,
            "destinations": dest_waypoints,
            "travelMode": travel_mode,
        }

        try:
            resp = await self.client.post(
                url, json=body, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            raw_elements = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Distance matrix error: %s", exc)
            return self._fallback_matrix(len(origins), len(destinations))

        # The API returns a flat list; reshape into rows x cols.
        n_origins = len(origins)
        n_dests = len(destinations)
        matrix: list[list[dict[str, int]]] = [
            [
                {
                    "distance_meters": FALLBACK_DISTANCE_METERS,
                    "duration_seconds": FALLBACK_DURATION_SECONDS,
                }
                for _ in range(n_dests)
            ]
            for _ in range(n_origins)
        ]

        if isinstance(raw_elements, list):
            for elem in raw_elements:
                oi = elem.get("originIndex", 0)
                di = elem.get("destinationIndex", 0)
                if 0 <= oi < n_origins and 0 <= di < n_dests:
                    matrix[oi][di] = {
                        "distance_meters": elem.get(
                            "distanceMeters", FALLBACK_DISTANCE_METERS
                        ),
                        "duration_seconds": self._parse_duration(
                            elem.get("duration", f"{FALLBACK_DURATION_SECONDS}s")
                        ),
                    }

        return {
            "rows": [{"elements": row} for row in matrix],
        }

    # ── Private helpers ─────────────────────────────────────────────────

    @staticmethod
    def _parse_duration(raw: str | int | None) -> int:
        """Parse a duration value from the Routes API.

        The API typically returns strings like ``"300s"`` or ``"1200s"``.
        Also handles raw int (seconds) or ``None``.
        """
        if raw is None:
            return FALLBACK_DURATION_SECONDS
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            match = re.match(r"^(\d+)", raw)
            if match:
                return int(match.group(1))
        return FALLBACK_DURATION_SECONDS

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format seconds into a human-readable string like ``'12 min'``."""
        if seconds < 60:
            return f"{seconds} sec"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        remaining = minutes % 60
        if remaining == 0:
            return f"{hours} hr"
        return f"{hours} hr {remaining} min"

    @staticmethod
    def _fallback_route(mode: TravelMode) -> Route:
        """Return a heuristic fallback route."""
        return Route(
            distance_meters=FALLBACK_DISTANCE_METERS,
            duration_seconds=FALLBACK_DURATION_SECONDS,
            duration_text="~12 min",
            travel_mode=mode,
        )

    @staticmethod
    def _fallback_matrix(
        n_origins: int, n_dests: int
    ) -> dict[str, Any]:
        """Return a fallback distance matrix filled with defaults."""
        return {
            "rows": [
                {
                    "elements": [
                        {
                            "distance_meters": FALLBACK_DISTANCE_METERS,
                            "duration_seconds": FALLBACK_DURATION_SECONDS,
                        }
                        for _ in range(n_dests)
                    ]
                }
                for _ in range(n_origins)
            ],
        }
