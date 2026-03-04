"""Unit tests for TSP route optimizer."""

import pytest
from app.algorithms.tsp import RouteOptimizer, haversine_distance, simple_optimize_by_location
from app.models.common import Location
from app.models.internal import PlaceCandidate


def _make_place(name: str, lat: float, lng: float) -> PlaceCandidate:
    """Helper to create a PlaceCandidate with minimal fields."""
    return PlaceCandidate(
        place_id=f"place_{name}",
        name=name,
        address=f"{name} address",
        location=Location(lat=lat, lng=lng),
        types=["tourist_attraction"],
    )


class TestHaversineDistance:
    """Tests for haversine distance calculation."""

    def test_same_point_is_zero(self):
        loc = Location(lat=48.8566, lng=2.3522)
        assert haversine_distance(loc, loc) == 0.0

    def test_known_distance(self):
        # Paris to London is approximately 344 km
        paris = Location(lat=48.8566, lng=2.3522)
        london = Location(lat=51.5074, lng=-0.1278)
        distance = haversine_distance(paris, london)
        assert 340_000 < distance < 350_000  # within 5km tolerance

    def test_symmetry(self):
        a = Location(lat=40.7128, lng=-74.0060)  # NYC
        b = Location(lat=34.0522, lng=-118.2437)  # LA
        assert haversine_distance(a, b) == pytest.approx(haversine_distance(b, a))

    def test_antipodal_points(self):
        # North pole to south pole ≈ 20,015 km
        north = Location(lat=90, lng=0)
        south = Location(lat=-90, lng=0)
        distance = haversine_distance(north, south)
        assert 20_000_000 < distance < 20_100_000


class TestRouteOptimizer:
    """Tests for the RouteOptimizer TSP algorithms."""

    def test_empty_list(self):
        opt = RouteOptimizer()
        result = opt.optimize_day([], preserve_order=False)
        assert result == []

    def test_single_place(self):
        opt = RouteOptimizer()
        place = _make_place("A", 48.0, 2.0)
        result = opt.optimize_day([place], preserve_order=False)
        assert len(result) == 1
        assert result[0].name == "A"

    def test_two_places_no_start(self):
        opt = RouteOptimizer()
        places = [_make_place("A", 48.0, 2.0), _make_place("B", 48.1, 2.1)]
        result = opt.optimize_day(places, preserve_order=False)
        assert len(result) == 2

    def test_two_places_closer_first_with_start(self):
        opt = RouteOptimizer()
        start = Location(lat=48.0, lng=2.0)
        far = _make_place("Far", 49.0, 3.0)
        close = _make_place("Close", 48.01, 2.01)
        result = opt.optimize_day([far, close], start_location=start, preserve_order=False)
        assert result[0].name == "Close"
        assert result[1].name == "Far"

    def test_preserve_order_no_start(self):
        opt = RouteOptimizer()
        places = [_make_place("A", 48.0, 2.0), _make_place("B", 49.0, 3.0), _make_place("C", 50.0, 4.0)]
        result = opt.optimize_day(places, preserve_order=True)
        assert [p.name for p in result] == ["A", "B", "C"]

    def test_preserve_order_rotates_to_closest(self):
        opt = RouteOptimizer()
        start = Location(lat=50.0, lng=4.0)  # Closest to C
        places = [
            _make_place("A", 48.0, 2.0),
            _make_place("B", 49.0, 3.0),
            _make_place("C", 50.01, 4.01),
        ]
        result = opt.optimize_day(places, start_location=start, preserve_order=True)
        assert result[0].name == "C"  # Rotated to start with closest

    def test_tsp_produces_valid_permutation(self):
        opt = RouteOptimizer()
        places = [
            _make_place("A", 48.0, 2.0),
            _make_place("B", 48.5, 2.5),
            _make_place("C", 49.0, 3.0),
            _make_place("D", 49.5, 3.5),
        ]
        result = opt.optimize_day(places, preserve_order=False)
        assert sorted([p.name for p in result]) == ["A", "B", "C", "D"]

    def test_tsp_shorter_than_reverse(self):
        """TSP should produce a route no worse than the reversed input."""
        opt = RouteOptimizer()
        # Places in a line: A-B-C-D. Reversed order would be suboptimal.
        places = [
            _make_place("D", 51.0, 5.0),
            _make_place("A", 48.0, 2.0),
            _make_place("C", 50.0, 4.0),
            _make_place("B", 49.0, 3.0),
        ]
        result = opt.optimize_day(places, preserve_order=False)

        def total_distance(route):
            return sum(
                haversine_distance(route[i].location, route[i + 1].location)
                for i in range(len(route) - 1)
            )

        assert total_distance(result) <= total_distance(places)

    def test_custom_distance_fn(self):
        """RouteOptimizer accepts a custom distance function."""
        calls = []

        def mock_dist(a: Location, b: Location) -> float:
            calls.append((a, b))
            return abs(a.lat - b.lat) + abs(a.lng - b.lng)

        opt = RouteOptimizer(distance_fn=mock_dist)
        places = [_make_place("A", 0, 0), _make_place("B", 1, 1), _make_place("C", 2, 2)]
        opt.optimize_day(places, preserve_order=False)
        assert len(calls) > 0  # Custom fn was actually used


class TestSimpleOptimizeByLocation:
    """Tests for the fallback location-based sort."""

    def test_empty(self):
        assert simple_optimize_by_location([]) == []

    def test_single(self):
        p = _make_place("A", 1, 1)
        assert simple_optimize_by_location([p]) == [p]

    def test_two_places(self):
        a = _make_place("A", 1, 1)
        b = _make_place("B", 2, 2)
        result = simple_optimize_by_location([b, a])
        assert result == [b, a]  # 2 or fewer returned as-is

    def test_sorts_by_lat_plus_lng(self):
        a = _make_place("A", 3, 3)  # sum=6
        b = _make_place("B", 1, 1)  # sum=2
        c = _make_place("C", 2, 2)  # sum=4
        result = simple_optimize_by_location([a, c, b])
        assert [p.name for p in result] == ["B", "C", "A"]
