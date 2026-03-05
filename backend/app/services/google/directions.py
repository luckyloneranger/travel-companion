"""Google Directions API service for transit, ferry, and driving routes.

Uses the legacy Directions API at
``https://maps.googleapis.com/maps/api/directions/json``
because the new Routes API does not yet expose full transit details
(line names, stop info, transfers, etc.).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.models.common import Location

logger = logging.getLogger(__name__)

BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"
from app.config.planning import GOOGLE_API_TIMEOUT as REQUEST_TIMEOUT


# ── Internal data classes (not API-facing) ──────────────────────────────


@dataclass
class TransitLine:
    """A single transit line (bus, metro, train, ferry, etc.)."""

    name: str = ""
    short_name: str = ""
    vehicle_type: str = ""
    color: str = ""
    agency: str = ""
    url: str = ""


@dataclass
class TransitStop:
    """A transit stop / station."""

    name: str = ""
    location: dict[str, float] = field(default_factory=dict)


@dataclass
class TransitStep:
    """One step of a transit journey (a single vehicle leg)."""

    line: TransitLine = field(default_factory=TransitLine)
    departure_stop: TransitStop = field(default_factory=TransitStop)
    arrival_stop: TransitStop = field(default_factory=TransitStop)
    departure_time: str = ""
    arrival_time: str = ""
    num_stops: int = 0
    duration_seconds: int = 0
    distance_meters: int = 0
    instructions: str = ""
    travel_mode: str = "TRANSIT"


@dataclass
class TransitRoute:
    """A complete transit route (may contain multiple steps / transfers)."""

    duration_seconds: int = 0
    distance_meters: int = 0
    departure_time: str = ""
    arrival_time: str = ""
    steps: list[TransitStep] = field(default_factory=list)
    num_transfers: int = 0
    fare: str | None = None
    polyline: str | None = None
    summary: str = ""


@dataclass
class DrivingRoute:
    """A driving route summary."""

    duration_seconds: int = 0
    distance_meters: int = 0
    duration_text: str = ""
    distance_text: str = ""
    polyline: str | None = None
    summary: str = ""


@dataclass
class TransportOptions:
    """Aggregated transport options between two points."""

    driving: DrivingRoute | None = None
    transit_routes: list[TransitRoute] = field(default_factory=list)
    origin: str = ""
    destination: str = ""


class GoogleDirectionsService:
    """Async wrapper around the legacy Google Directions API.

    Used specifically for transit and ferry routing where the new Routes
    API lacks detailed information.

    Parameters
    ----------
    api_key:
        Google API key with Directions API enabled.
    client:
        Shared ``httpx.AsyncClient`` — the caller owns its lifecycle.
    """

    def __init__(self, api_key: str, client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.client = client

    # ── Public methods ──────────────────────────────────────────────────

    async def get_driving_route(
        self,
        origin: Location,
        destination: Location,
    ) -> DrivingRoute | None:
        """Get a driving route between two locations.

        Returns ``None`` on failure.
        """
        params: dict[str, str] = {
            "origin": f"{origin.lat},{origin.lng}",
            "destination": f"{destination.lat},{destination.lng}",
            "mode": "driving",
            "key": self.api_key,
        }

        try:
            resp = await self.client.get(
                BASE_URL, params=params, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Driving route error: %s", exc)
            return None

        if data.get("status") != "OK":
            logger.warning("Driving route status: %s", data.get("status"))
            return None

        routes = data.get("routes", [])
        if not routes:
            return None

        route = routes[0]
        leg = route.get("legs", [{}])[0]

        return DrivingRoute(
            duration_seconds=leg.get("duration", {}).get("value", 0),
            distance_meters=leg.get("distance", {}).get("value", 0),
            duration_text=leg.get("duration", {}).get("text", ""),
            distance_text=leg.get("distance", {}).get("text", ""),
            polyline=route.get("overview_polyline", {}).get("points"),
            summary=route.get("summary", ""),
        )

    async def get_transit_routes(
        self,
        origin: Location,
        destination: Location,
        mode: str = "transit",
        transit_mode: str | None = None,
        alternatives: bool = True,
    ) -> list[TransitRoute]:
        """Get transit routes between two locations.

        Parameters
        ----------
        mode:
            Directions API mode — ``"transit"`` for public transit.
        transit_mode:
            Optional comma-separated transit sub-modes, e.g. ``"train,bus"``.
        alternatives:
            Whether to request alternative routes.
        """
        params: dict[str, str] = {
            "origin": f"{origin.lat},{origin.lng}",
            "destination": f"{destination.lat},{destination.lng}",
            "mode": mode,
            "alternatives": str(alternatives).lower(),
            "key": self.api_key,
        }
        if transit_mode:
            params["transit_mode"] = transit_mode

        try:
            resp = await self.client.get(
                BASE_URL, params=params, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Transit route error: %s", exc)
            return []

        if data.get("status") != "OK":
            logger.warning("Transit route status: %s", data.get("status"))
            return []

        return [
            self._parse_transit_route(r) for r in data.get("routes", [])
        ]

    async def get_all_transport_options(
        self,
        origin: Location,
        destination: Location,
        origin_name: str = "",
        destination_name: str = "",
    ) -> TransportOptions:
        """Fetch driving and transit options in parallel.

        Returns a ``TransportOptions`` bundle with both driving and
        transit results.
        """
        driving_task = asyncio.ensure_future(
            self.get_driving_route(origin, destination)
        )
        transit_task = asyncio.ensure_future(
            self.get_transit_routes(origin, destination)
        )

        driving, transit = await asyncio.gather(
            driving_task, transit_task, return_exceptions=True
        )

        driving_result = driving if isinstance(driving, DrivingRoute) else None
        transit_result = transit if isinstance(transit, list) else []

        return TransportOptions(
            driving=driving_result,
            transit_routes=transit_result,
            origin=origin_name,
            destination=destination_name,
        )

    # ── Private helpers ─────────────────────────────────────────────────

    def _parse_transit_route(self, raw_route: dict[str, Any]) -> TransitRoute:
        """Parse a single route from the Directions API response."""
        leg = raw_route.get("legs", [{}])[0]

        steps: list[TransitStep] = []
        for step in leg.get("steps", []):
            if step.get("travel_mode") == "TRANSIT":
                steps.append(self._parse_transit_step(step))
            elif step.get("travel_mode") == "WALKING":
                # Include walking segments for completeness.
                steps.append(
                    TransitStep(
                        duration_seconds=step.get("duration", {}).get("value", 0),
                        distance_meters=step.get("distance", {}).get("value", 0),
                        instructions=step.get("html_instructions", "Walk"),
                        travel_mode="WALKING",
                    )
                )

        # Count transfers (number of TRANSIT steps minus 1, minimum 0).
        transit_count = sum(1 for s in steps if s.travel_mode == "TRANSIT")
        num_transfers = max(0, transit_count - 1)

        # Extract fare if available.
        fare_info = raw_route.get("fare")
        fare = None
        if fare_info:
            fare = f"{fare_info.get('currency', '')} {fare_info.get('text', '')}".strip()

        return TransitRoute(
            duration_seconds=leg.get("duration", {}).get("value", 0),
            distance_meters=leg.get("distance", {}).get("value", 0),
            departure_time=leg.get("departure_time", {}).get("text", ""),
            arrival_time=leg.get("arrival_time", {}).get("text", ""),
            steps=steps,
            num_transfers=num_transfers,
            fare=fare,
            polyline=raw_route.get("overview_polyline", {}).get("points"),
            summary=raw_route.get("summary", ""),
        )

    @staticmethod
    def _parse_transit_step(step: dict[str, Any]) -> TransitStep:
        """Parse a single TRANSIT step from the Directions API."""
        transit_details = step.get("transit_details", {})
        line_info = transit_details.get("line", {})
        vehicle = line_info.get("vehicle", {})

        agencies = line_info.get("agencies", [])
        agency_name = agencies[0].get("name", "") if agencies else ""
        agency_url = agencies[0].get("url", "") if agencies else ""

        dep_stop = transit_details.get("departure_stop", {})
        arr_stop = transit_details.get("arrival_stop", {})

        dep_loc = dep_stop.get("location", {})
        arr_loc = arr_stop.get("location", {})

        return TransitStep(
            line=TransitLine(
                name=line_info.get("name", ""),
                short_name=line_info.get("short_name", ""),
                vehicle_type=vehicle.get("type", ""),
                color=line_info.get("color", ""),
                agency=agency_name,
                url=agency_url,
            ),
            departure_stop=TransitStop(
                name=dep_stop.get("name", ""),
                location={
                    "lat": dep_loc.get("lat", 0.0),
                    "lng": dep_loc.get("lng", 0.0),
                },
            ),
            arrival_stop=TransitStop(
                name=arr_stop.get("name", ""),
                location={
                    "lat": arr_loc.get("lat", 0.0),
                    "lng": arr_loc.get("lng", 0.0),
                },
            ),
            departure_time=transit_details.get("departure_time", {}).get(
                "text", ""
            ),
            arrival_time=transit_details.get("arrival_time", {}).get("text", ""),
            num_stops=transit_details.get("num_stops", 0),
            duration_seconds=step.get("duration", {}).get("value", 0),
            distance_meters=step.get("distance", {}).get("value", 0),
            instructions=step.get("html_instructions", ""),
            travel_mode="TRANSIT",
        )
