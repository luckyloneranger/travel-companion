"""Route optimizer service using TSP algorithms."""

import logging
from typing import Optional

from app.models import Location, OptimizationResult, PlaceCandidate
from app.services.external.google_routes import GoogleRoutesService

logger = logging.getLogger(__name__)


class RouteOptimizer:
    """
    Service for optimizing visit order using TSP algorithms.
    
    Note: This only optimizes for travel efficiency (shortest route).
    Logical ordering (meal timing, activity flow) is handled by the AI planner.
    """

    def __init__(self, routes_service: GoogleRoutesService):
        """Initialize route optimizer with routes service."""
        self.routes = routes_service

    async def optimize_day(
        self,
        places: list[PlaceCandidate],
        start_location: Optional[Location] = None,
        preserve_order: bool = True,
    ) -> OptimizationResult:
        """
        Optimize or calculate route metrics for a day's places.

        Args:
            places: List of places to visit (in AI-determined order)
            start_location: Optional starting point (e.g., hotel)
            preserve_order: If True, keep AI's order and just calculate metrics.
                           If False, optimize for shortest route.

        Returns:
            OptimizationResult with place order and total metrics
        """
        n = len(places)

        # Trivial cases
        if n <= 1:
            return OptimizationResult(
                places=places, total_distance_meters=0, total_duration_seconds=0
            )

        if n == 2:
            try:
                route = await self.routes.compute_route(
                    places[0].location, places[1].location
                )
                return OptimizationResult(
                    places=places,
                    total_distance_meters=route.distance_meters,
                    total_duration_seconds=route.duration_seconds,
                )
            except Exception:
                return OptimizationResult(
                    places=places, total_distance_meters=1000, total_duration_seconds=720
                )

        # If preserving AI's order, just calculate route metrics
        if preserve_order:
            total_dist, total_dur = await self._calculate_route_totals(places)
            return OptimizationResult(
                places=places,
                total_distance_meters=total_dist,
                total_duration_seconds=total_dur,
            )

        # Otherwise, optimize with TSP
        return await self._optimize_tsp(places)
    
    async def _calculate_route_totals(
        self, places: list[PlaceCandidate]
    ) -> tuple[int, int]:
        """Calculate total distance and duration for a route in order."""
        total_dist = 0
        total_dur = 0
        
        for i in range(len(places) - 1):
            try:
                route = await self.routes.compute_route(
                    places[i].location, places[i + 1].location
                )
                total_dist += route.distance_meters
                total_dur += route.duration_seconds
            except Exception:
                total_dist += 1000
                total_dur += 600
        
        return total_dist, total_dur
    
    async def _optimize_tsp(
        self, places: list[PlaceCandidate]
    ) -> OptimizationResult:
        """Pure TSP optimization for shortest route."""
        n = len(places)

        # Build distance matrix
        try:
            matrix, dist_matrix = await self._build_distance_matrix(places)
        except Exception as e:
            logger.error(f"Failed to build distance matrix: {e}")
            return OptimizationResult(
                places=places,
                total_distance_meters=n * 500,
                total_duration_seconds=n * 360,
            )

        # Nearest neighbor + 2-opt (operates on duration matrix)
        order = self._nearest_neighbor(matrix, start_idx=0)
        order = self._two_opt_improve(order, matrix)

        # Build result using real distances
        optimized_places = [places[i] for i in order]
        total_dist, total_dur = self._calculate_totals(order, matrix, dist_matrix)

        return OptimizationResult(
            places=optimized_places,
            total_distance_meters=total_dist,
            total_duration_seconds=total_dur,
        )

    async def _build_distance_matrix(
        self, places: list[PlaceCandidate]
    ) -> tuple[list[list[int]], list[list[int]]]:
        """
        Build duration and distance matrices between all pairs of places.

        Uses Google Distance Matrix API.

        Returns:
            Tuple of (duration_matrix, distance_matrix)
        """
        locations = [p.location for p in places]

        # Get matrices from Google Routes
        duration_matrix, distance_matrix = await self.routes.get_distance_matrix(
            origins=locations, destinations=locations
        )

        return duration_matrix, distance_matrix

    def _nearest_neighbor(
        self, matrix: list[list[int]], start_idx: int = 0
    ) -> list[int]:
        """
        Build tour using nearest neighbor heuristic.

        Time: O(n²)
        Quality: Typically within 25% of optimal
        """
        n = len(matrix)
        visited = {start_idx}
        tour = [start_idx]
        current = start_idx

        while len(tour) < n:
            # Find nearest unvisited node
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
        self, tour: list[int], matrix: list[list[int]], max_iterations: int = 100
    ) -> list[int]:
        """
        Improve tour using 2-opt swaps.

        2-opt: Remove two edges, reconnect differently.
        Keep swapping until no improvement found.

        Time: O(n²) per iteration
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
                        # Reverse segment between i+1 and j
                        tour[i + 1 : j + 1] = reversed(tour[i + 1 : j + 1])
                        improved = True

        logger.debug(f"2-opt completed in {iterations} iterations")
        return tour

    def _two_opt_gain(
        self, tour: list[int], i: int, j: int, matrix: list[list[int]]
    ) -> int:
        """
        Calculate improvement from 2-opt swap.

        Returns positive value if swap improves tour.
        """
        n = len(tour)

        # Current edges
        a, b = tour[i], tour[i + 1]
        c, d = tour[j], tour[(j + 1) % n]

        current_dist = matrix[a][b] + matrix[c][d]
        new_dist = matrix[a][c] + matrix[b][d]

        return current_dist - new_dist

    def _calculate_totals(
        self, order: list[int], duration_matrix: list[list[int]], distance_matrix: list[list[int]]
    ) -> tuple[int, int]:
        """Calculate total distance and duration for tour using real data."""
        total_duration = 0
        total_distance = 0
        for i in range(len(order) - 1):
            total_duration += duration_matrix[order[i]][order[i + 1]]
            total_distance += distance_matrix[order[i]][order[i + 1]]

        return total_distance, total_duration


def simple_optimize_by_location(places: list[PlaceCandidate]) -> list[PlaceCandidate]:
    """
    Simple optimization by sorting places by latitude/longitude.

    Fallback when Google API is unavailable.
    """
    if len(places) <= 2:
        return places

    # Sort by a combination of lat and lng to create a rough path
    return sorted(places, key=lambda p: (p.location.lat + p.location.lng))
