"""Route optimizer using TSP algorithms (nearest-neighbor + 2-opt).

Ported from the battle-tested RouteOptimizer in the original codebase.
This version is decoupled from Google APIs and accepts a generic distance
function, making it testable without network calls.
"""

import logging
import math
from typing import Callable, Optional

from app.models.common import Location
from app.models.internal import PlaceCandidate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Haversine utility
# ---------------------------------------------------------------------------

def haversine_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate distance between two Location objects using the Haversine formula.

    Args:
        loc1: First location.
        loc2: Second location.

    Returns:
        Distance in meters.
    """
    R = 6_371_000  # Earth's radius in metres
    lat1_rad = math.radians(loc1.lat)
    lat2_rad = math.radians(loc2.lat)
    delta_lat = math.radians(loc2.lat - loc1.lat)
    delta_lng = math.radians(loc2.lng - loc1.lng)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# Type alias for the distance callback.
DistanceFn = Callable[[Location, Location], float]


class RouteOptimizer:
    """
    Service for optimizing visit order using TSP algorithms.

    The optimizer works in two modes controlled by ``preserve_order``:

    * **preserve_order=True** (default) -- keeps the AI-determined order and
      only optimises the start/end leg if a ``start_location`` is given.
    * **preserve_order=False** -- runs nearest-neighbour + 2-opt for the
      shortest-route ordering.

    Note: This only optimises for travel efficiency (shortest route).
    Logical ordering (meal timing, activity flow) is handled by the AI planner.
    """

    def __init__(self, distance_fn: Optional[DistanceFn] = None):
        """
        Initialise route optimizer.

        Args:
            distance_fn: A callable ``(Location, Location) -> float`` returning
                distance in metres.  Defaults to Haversine.
        """
        self.distance_fn = distance_fn or haversine_distance

    def optimize_day(
        self,
        activities: list[PlaceCandidate],
        distance_fn: Optional[DistanceFn] = None,
        start_location: Optional[Location] = None,
        preserve_order: bool = True,
    ) -> list[PlaceCandidate]:
        """
        Optimize or verify route for a day's activities.

        Args:
            activities: List of places to visit (in AI-determined order).
            distance_fn: Optional override for per-call distance function.
                Falls back to the instance-level distance_fn.
            start_location: Optional starting point (e.g., hotel).
            preserve_order: If True, keep AI's order (only add start/end
                optimization).  If False, run full TSP.

        Returns:
            Ordered list of PlaceCandidate forming the optimised route.
        """
        dist = distance_fn or self.distance_fn
        n = len(activities)

        # Trivial cases
        if n <= 1:
            return list(activities)

        if n == 2:
            if start_location is not None:
                # Place the closer one first
                d0 = dist(start_location, activities[0].location)
                d1 = dist(start_location, activities[1].location)
                if d1 < d0:
                    return [activities[1], activities[0]]
            return list(activities)

        # If preserving AI order, optionally re-anchor to start_location
        if preserve_order:
            return self._preserve_with_start(activities, dist, start_location)

        # Full TSP optimisation
        return self._optimize_tsp(activities, dist, start_location)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _preserve_with_start(
        self,
        places: list[PlaceCandidate],
        dist: DistanceFn,
        start_location: Optional[Location],
    ) -> list[PlaceCandidate]:
        """Keep AI order but rotate so the closest place to start is first."""
        if start_location is None:
            return list(places)

        # Find index of the place closest to start_location
        best_idx = 0
        best_dist = float("inf")
        for i, p in enumerate(places):
            d = dist(start_location, p.location)
            if d < best_dist:
                best_dist = d
                best_idx = i

        if best_idx == 0:
            return list(places)

        # Rotate: closest-to-start first, then the rest in original order
        return places[best_idx:] + places[:best_idx]

    def _optimize_tsp(
        self,
        places: list[PlaceCandidate],
        dist: DistanceFn,
        start_location: Optional[Location],
    ) -> list[PlaceCandidate]:
        """Pure TSP optimization for shortest route."""
        n = len(places)

        # Build distance matrix
        matrix = self._build_distance_matrix(places, dist)

        # Nearest neighbour starting from index 0 (or closest to start)
        start_idx = 0
        if start_location is not None:
            start_idx = min(
                range(n),
                key=lambda i: dist(start_location, places[i].location),
            )

        order = self._nearest_neighbor(matrix, start_idx=start_idx)
        order = self._two_opt_improve(order, matrix)

        return [places[i] for i in order]

    def _build_distance_matrix(
        self,
        places: list[PlaceCandidate],
        dist: DistanceFn,
    ) -> list[list[float]]:
        """Build a symmetric distance matrix between all places."""
        n = len(places)
        matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = dist(places[i].location, places[j].location)
                matrix[i][j] = d
                matrix[j][i] = d
        return matrix

    def _nearest_neighbor(
        self, matrix: list[list[float]], start_idx: int = 0
    ) -> list[int]:
        """
        Build tour using nearest-neighbour heuristic.

        Time:    O(n^2)
        Quality: Typically within 25% of optimal.
        """
        n = len(matrix)
        visited = {start_idx}
        tour = [start_idx]
        current = start_idx

        while len(tour) < n:
            nearest = None
            nearest_dist = float("inf")

            for j in range(n):
                if j not in visited and matrix[current][j] < nearest_dist:
                    nearest = j
                    nearest_dist = matrix[current][j]

            if nearest is None:
                # Shouldn't happen, but handle gracefully
                for j in range(n):
                    if j not in visited:
                        nearest = j
                        break

            assert nearest is not None, "No unvisited node found"
            tour.append(nearest)
            visited.add(nearest)
            current = nearest

        return tour

    def _two_opt_improve(
        self,
        tour: list[int],
        matrix: list[list[float]],
        max_iterations: int = 100,
    ) -> list[int]:
        """
        Improve tour using 2-opt swaps.

        2-opt: Remove two edges, reconnect differently.
        Keep swapping until no improvement found.

        Time: O(n^2) per iteration.
        """
        n = len(tour)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1

            for i in range(n - 1):
                for j in range(i + 2, n):
                    gain = self._two_opt_gain(tour, i, j, matrix)
                    if gain > 0:
                        tour[i + 1 : j + 1] = reversed(tour[i + 1 : j + 1])
                        improved = True

        logger.debug(f"2-opt completed in {iterations} iterations")
        return tour

    def _two_opt_gain(
        self,
        tour: list[int],
        i: int,
        j: int,
        matrix: list[list[float]],
    ) -> float:
        """
        Calculate improvement from a 2-opt swap.

        Returns a positive value if the swap improves the tour.
        """
        n = len(tour)
        a, b = tour[i], tour[i + 1]
        c, d = tour[j], tour[(j + 1) % n]

        current_dist = matrix[a][b] + matrix[c][d]
        new_dist = matrix[a][c] + matrix[b][d]

        return current_dist - new_dist


def simple_optimize_by_location(
    places: list[PlaceCandidate],
) -> list[PlaceCandidate]:
    """
    Simple optimisation by sorting places by latitude/longitude.

    Fallback when no distance function / API is available.
    """
    if len(places) <= 2:
        return places
    return sorted(places, key=lambda p: (p.location.lat + p.location.lng))
