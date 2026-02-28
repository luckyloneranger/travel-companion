"""Google Routes API service for route calculation."""

import asyncio
import logging
import re
from typing import Optional, Self

import httpx

from app.config import get_settings
from app.config.planning import FALLBACK_DISTANCE_METERS, FALLBACK_DURATION_SECONDS
from app.core.clients import HTTPClientPool
from app.models import Location, Route, TravelMode

logger = logging.getLogger(__name__)

# Timeout for individual API requests (seconds)
_REQUEST_TIMEOUT = 15.0

# Shared travel mode mapping
_TRAVEL_MODE_MAP = {
    TravelMode.WALK: "WALK",
    TravelMode.DRIVE: "DRIVE",
    TravelMode.TRANSIT: "TRANSIT",
}


def _parse_duration(duration_str: str) -> int:
    """Parse Google Routes API duration string to seconds.

    Handles formats like "300s", "300", or empty/malformed strings.
    """
    if not duration_str:
        return 0
    match = re.match(r"^(\d+)", duration_str)
    if not match:
        logger.warning(f"Could not parse duration string: {duration_str!r}")
        return 0
    return int(match.group(1))


class GoogleRoutesService:
    """Service for interacting with Google Routes API.
    
    Uses shared HTTP client from HTTPClientPool for connection pooling.
    """

    BASE_URL = "https://routes.googleapis.com"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Google Routes service."""
        settings = get_settings()
        self.api_key = api_key or settings.google_routes_api_key

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the shared HTTP client."""
        return HTTPClientPool.get_routes_client()

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
        """Get headers for Google Routes API requests."""
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

    async def compute_route(
        self,
        origin: Location,
        destination: Location,
        mode: TravelMode = TravelMode.WALK,
    ) -> Route:
        """
        Compute a route between two locations.

        Args:
            origin: Starting location
            destination: Ending location
            mode: Travel mode (WALK, DRIVE, TRANSIT)

        Returns:
            Route with distance, duration, and polyline
        """
        field_mask = "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline"

        response = await self.client.post(
            f"{self.BASE_URL}/directions/v2:computeRoutes",
            headers=self._get_headers(field_mask),
            timeout=_REQUEST_TIMEOUT,
            json={
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
                "travelMode": _TRAVEL_MODE_MAP[mode],
                "computeAlternativeRoutes": False,
                "routeModifiers": {
                    "avoidTolls": False,
                    "avoidHighways": False,
                    "avoidFerries": False,
                },
                "languageCode": "en-US",
                "units": "METRIC",
            },
        )

        if response.status_code != 200:
            logger.error(f"Compute route failed: {response.text}")
            raise Exception(f"Route computation failed: {response.status_code}")

        data = response.json()

        if not data.get("routes"):
            raise Exception("No route found")

        route_data = data["routes"][0]

        # Parse duration
        duration_str = route_data.get("duration", "0s")
        duration_seconds = _parse_duration(duration_str)

        # Format duration text
        if duration_seconds < 60:
            duration_text = f"{duration_seconds} sec"
        elif duration_seconds < 3600:
            duration_text = f"{duration_seconds // 60} min"
        else:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            duration_text = f"{hours}h {minutes}min"

        return Route(
            distance_meters=route_data.get("distanceMeters", 0),
            duration_seconds=duration_seconds,
            duration_text=duration_text,
            travel_mode=mode,
            polyline=route_data.get("polyline", {}).get("encodedPolyline", ""),
        )

    async def compute_routes_batch(
        self,
        waypoints: list[Location],
        mode: TravelMode = TravelMode.WALK,
    ) -> list[Route]:
        """
        Compute routes between consecutive waypoints in parallel.

        Args:
            waypoints: List of locations (at least 2)
            mode: Travel mode for all routes

        Returns:
            List of routes between consecutive waypoints
        """
        if len(waypoints) < 2:
            return []

        # Create tasks for all route computations
        tasks = [
            self.compute_route(
                origin=waypoints[i],
                destination=waypoints[i + 1],
                mode=mode,
            )
            for i in range(len(waypoints) - 1)
        ]
        
        # Execute all route computations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, using fallback for any failures
        routes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to compute route {i} -> {i + 1}: {result}")
                # Add a fallback route with estimated values
                routes.append(
                    Route(
                        distance_meters=FALLBACK_DISTANCE_METERS,
                        duration_seconds=FALLBACK_DURATION_SECONDS,
                        duration_text="~12 min",
                        travel_mode=mode,
                        polyline="",
                    )
                )
            else:
                routes.append(result)

        return routes

    async def get_distance_matrix(
        self,
        origins: list[Location],
        destinations: list[Location],
        mode: TravelMode = TravelMode.WALK,
    ) -> tuple[list[list[int]], list[list[int]]]:
        """
        Get a distance/duration matrix between all origin-destination pairs.

        Args:
            origins: List of origin locations
            destinations: List of destination locations
            mode: Travel mode

        Returns:
            Tuple of (duration_matrix, distance_matrix) where each is
            a 2D list [origin_idx][destination_idx] in seconds and meters respectively
        """
        field_mask = "originIndex,destinationIndex,duration,distanceMeters"

        response = await self.client.post(
            f"{self.BASE_URL}/distanceMatrix/v2:computeRouteMatrix",
            headers=self._get_headers(field_mask),
            timeout=_REQUEST_TIMEOUT,
            json={
                "origins": [
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
                ],
                "destinations": [
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
                ],
                "travelMode": _TRAVEL_MODE_MAP[mode],
            },
        )

        if response.status_code != 200:
            logger.error(f"Distance matrix failed: {response.text}")
            raise Exception(f"Distance matrix computation failed")

        # Parse response into 2D matrices
        n_origins = len(origins)
        n_destinations = len(destinations)
        duration_matrix = [[0] * n_destinations for _ in range(n_origins)]
        distance_matrix = [[0] * n_destinations for _ in range(n_origins)]

        for element in response.json():
            origin_idx = element.get("originIndex", 0)
            dest_idx = element.get("destinationIndex", 0)
            duration_str = element.get("duration", "0s")
            duration_seconds = _parse_duration(duration_str)
            duration_matrix[origin_idx][dest_idx] = duration_seconds
            distance_matrix[origin_idx][dest_idx] = element.get("distanceMeters", 0)

        return duration_matrix, distance_matrix
