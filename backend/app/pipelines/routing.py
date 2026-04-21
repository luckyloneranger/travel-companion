"""Routing pipeline — TSP optimization + Google Routes for activity sequences."""

import asyncio
import logging
from dataclasses import dataclass

from app.models.common import Location
from app.services.google.routes import GoogleRoutesService
from app.algorithms.tsp import RouteOptimizer, haversine_distance

logger = logging.getLogger(__name__)

# Pace-aware walk thresholds (seconds)
WALK_THRESHOLDS = {
    "relaxed": 25 * 60,    # 25 min
    "moderate": 20 * 60,   # 20 min
    "packed": 15 * 60,     # 15 min
}


@dataclass
class RouteResult:
    """Route between two activities."""
    from_sequence: int
    to_sequence: int
    travel_mode: str  # walk / drive
    distance_meters: int
    duration_seconds: int
    polyline: str | None = None


@dataclass
class DayRoutingResult:
    """Routing result for all activities in a day."""
    ordered_activities: list[dict]  # activities in TSP-optimized order
    routes: list[RouteResult]


class RoutingPipeline:
    """TSP optimization + Google Routes for day activity sequences."""

    def __init__(self, routes_service: GoogleRoutesService):
        self.routes = routes_service
        self.optimizer = RouteOptimizer()

    async def route_day(
        self,
        activities: list[dict],
        pace: str = "moderate",
    ) -> DayRoutingResult:
        """Route a day's activities: TSP optimize order, then compute routes.

        Args:
            activities: list of dicts with 'location' ({lat, lng}), 'sequence', etc.
            pace: relaxed/moderate/packed — affects walk threshold.

        Returns:
            DayRoutingResult with ordered activities and routes between them.
        """
        if len(activities) <= 1:
            return DayRoutingResult(ordered_activities=activities, routes=[])

        # TSP optimize order
        ordered = self._tsp_optimize(activities)

        # Compute routes between consecutive activities
        walk_threshold = WALK_THRESHOLDS.get(pace, WALK_THRESHOLDS["moderate"])
        routes = await self._compute_routes(ordered, walk_threshold)

        return DayRoutingResult(ordered_activities=ordered, routes=routes)

    def _tsp_optimize(self, activities: list[dict]) -> list[dict]:
        """Reorder activities using nearest-neighbor TSP."""
        locations = []
        for act in activities:
            loc = act.get("location", {})
            locations.append(Location(lat=loc.get("lat", 0), lng=loc.get("lng", 0)))

        if len(locations) < 2:
            return activities

        # Nearest-neighbor greedy ordering
        n = len(locations)
        visited = [False] * n
        order = [0]
        visited[0] = True

        for _ in range(n - 1):
            current = order[-1]
            best_next = -1
            best_dist = float("inf")
            for j in range(n):
                if not visited[j]:
                    d = haversine_distance(locations[current], locations[j])
                    if d < best_dist:
                        best_dist = d
                        best_next = j
            order.append(best_next)
            visited[best_next] = True

        # Reorder activities and update sequences
        reordered = []
        for idx, orig_idx in enumerate(order):
            act = dict(activities[orig_idx])
            act["sequence"] = idx + 1
            reordered.append(act)

        return reordered

    async def _compute_routes(
        self, activities: list[dict], walk_threshold: int
    ) -> list[RouteResult]:
        """Compute routes between consecutive activities in parallel."""
        tasks = []
        for i in range(len(activities) - 1):
            loc_a = activities[i].get("location", {})
            loc_b = activities[i + 1].get("location", {})
            origin = Location(lat=loc_a.get("lat", 0), lng=loc_a.get("lng", 0))
            dest = Location(lat=loc_b.get("lat", 0), lng=loc_b.get("lng", 0))
            tasks.append(self._compute_one_route(origin, dest, i, walk_threshold))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        routes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Route computation failed for leg %d: %s", i, result)
                routes.append(RouteResult(
                    from_sequence=i + 1,
                    to_sequence=i + 2,
                    travel_mode="walk",
                    distance_meters=800,
                    duration_seconds=720,
                ))
            else:
                routes.append(result)

        return routes

    async def _compute_one_route(
        self, origin: Location, dest: Location, index: int, walk_threshold: int
    ) -> RouteResult:
        """Compute a single route, choosing walk vs drive based on threshold."""
        route = await self.routes.compute_best_route(
            origin, dest, walk_threshold_seconds=walk_threshold
        )
        travel_mode = route.travel_mode
        if hasattr(travel_mode, "value"):
            travel_mode = travel_mode.value
        return RouteResult(
            from_sequence=index + 1,
            to_sequence=index + 2,
            travel_mode=str(travel_mode).lower(),
            distance_meters=route.distance_meters,
            duration_seconds=route.duration_seconds,
            polyline=getattr(route, "polyline", None),
        )
