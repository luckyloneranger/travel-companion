"""Tests for the routing pipeline — TSP optimization + Google Routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.common import Location, TravelMode
from app.models.day_plan import Route
from app.pipelines.routing import RoutingPipeline, RouteResult, DayRoutingResult


def _make_activity(seq: int, lat: float, lng: float, name: str = "") -> dict:
    return {
        "sequence": seq,
        "name": name or f"Activity {seq}",
        "location": {"lat": lat, "lng": lng},
    }


def _mock_routes_service() -> MagicMock:
    """Create a mock GoogleRoutesService with compute_best_route."""
    svc = MagicMock()
    svc.compute_best_route = AsyncMock(return_value=Route(
        distance_meters=500,
        duration_seconds=360,
        duration_text="6 min",
        travel_mode=TravelMode.WALK,
        polyline="abc123",
    ))
    return svc


@pytest.mark.asyncio
async def test_route_day_basic():
    """3 activities should produce 2 routes."""
    svc = _mock_routes_service()
    pipeline = RoutingPipeline(svc)

    activities = [
        _make_activity(1, 35.6762, 139.6503, "Shinjuku"),
        _make_activity(2, 35.6586, 139.7454, "Tokyo Tower"),
        _make_activity(3, 35.6717, 139.7703, "Imperial Palace"),
    ]

    result = await pipeline.route_day(activities, pace="moderate")

    assert isinstance(result, DayRoutingResult)
    assert len(result.ordered_activities) == 3
    assert len(result.routes) == 2
    assert svc.compute_best_route.call_count == 2

    # Verify route structure
    for route in result.routes:
        assert isinstance(route, RouteResult)
        assert route.travel_mode == "walk"
        assert route.distance_meters == 500
        assert route.polyline == "abc123"


@pytest.mark.asyncio
async def test_route_day_single_activity():
    """1 activity should return empty routes."""
    svc = _mock_routes_service()
    pipeline = RoutingPipeline(svc)

    activities = [_make_activity(1, 35.6762, 139.6503, "Shinjuku")]
    result = await pipeline.route_day(activities)

    assert len(result.ordered_activities) == 1
    assert len(result.routes) == 0
    svc.compute_best_route.assert_not_called()


@pytest.mark.asyncio
async def test_tsp_optimize_order():
    """Activities should be reordered by proximity (nearest-neighbor)."""
    svc = _mock_routes_service()
    pipeline = RoutingPipeline(svc)

    # Place activities far apart: A(0,0), B(0,10), C(0,1)
    # Nearest-neighbor from A: A -> C -> B
    activities = [
        _make_activity(1, 0.0, 0.0, "A"),
        _make_activity(2, 0.0, 10.0, "B"),
        _make_activity(3, 0.0, 1.0, "C"),
    ]

    result = await pipeline.route_day(activities, pace="relaxed")

    names = [a["name"] for a in result.ordered_activities]
    assert names == ["A", "C", "B"]

    # Verify sequences are updated
    seqs = [a["sequence"] for a in result.ordered_activities]
    assert seqs == [1, 2, 3]


@pytest.mark.asyncio
async def test_route_fallback_on_error():
    """When route service fails, fallback route should be used."""
    svc = MagicMock()
    svc.compute_best_route = AsyncMock(side_effect=RuntimeError("API down"))
    pipeline = RoutingPipeline(svc)

    activities = [
        _make_activity(1, 35.6762, 139.6503, "A"),
        _make_activity(2, 35.6586, 139.7454, "B"),
    ]

    result = await pipeline.route_day(activities)

    assert len(result.routes) == 1
    route = result.routes[0]
    assert route.travel_mode == "walk"
    assert route.distance_meters == 800
    assert route.duration_seconds == 720
    assert route.polyline is None
