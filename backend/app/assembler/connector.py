"""City connector — computes transport between consecutive cities."""

import asyncio
import logging
from app.services.google.directions import GoogleDirectionsService
from app.models.common import Location

logger = logging.getLogger(__name__)


class CityConnector:
    def __init__(self, directions_service: GoogleDirectionsService):
        self.directions = directions_service

    async def connect(self, city_sequence: list[dict]) -> list[dict]:
        """Compute transport options between consecutive cities.

        Args:
            city_sequence: [{city_name, location: {lat, lng}, ...}]
        Returns:
            list of transport leg dicts
        """
        if len(city_sequence) < 2:
            return []

        tasks = []
        for i in range(len(city_sequence) - 1):
            from_city = city_sequence[i]
            to_city = city_sequence[i + 1]
            origin = Location(
                lat=from_city["location"]["lat"],
                lng=from_city["location"]["lng"],
            )
            dest = Location(
                lat=to_city["location"]["lat"],
                lng=to_city["location"]["lng"],
            )
            tasks.append(self._get_transport(
                origin, dest,
                from_city.get("city_name", ""), to_city.get("city_name", ""),
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        legs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Transport lookup failed: {result}")
                legs.append({
                    "from_city": city_sequence[i].get("city_name", ""),
                    "to_city": city_sequence[i + 1].get("city_name", ""),
                    "mode": "unknown",
                    "duration_seconds": 0,
                    "fare": None,
                })
            else:
                legs.append(result)

        return legs

    async def _get_transport(self, origin: Location, dest: Location, from_name: str, to_name: str) -> dict:
        options = await self.directions.get_all_transport_options(
            origin, dest, from_name, to_name,
        )
        # Pick best transit option, fallback to driving
        if options.transit_routes:
            best = options.transit_routes[0]
            return {
                "from_city": from_name,
                "to_city": to_name,
                "mode": "transit",
                "duration_seconds": best.duration_seconds,
                "fare": best.fare,
                "summary": best.summary,
                "polyline": best.polyline,
            }
        if options.driving:
            return {
                "from_city": from_name,
                "to_city": to_name,
                "mode": "drive",
                "duration_seconds": options.driving.duration_seconds,
                "distance_meters": options.driving.distance_meters,
                "polyline": options.driving.polyline,
            }
        return {"from_city": from_name, "to_city": to_name, "mode": "unknown", "duration_seconds": 0}
