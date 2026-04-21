import pytest
from app.pipelines.costing import CostingPipeline, CostBreakdown


def test_compute_basic():
    pipeline = CostingPipeline()
    result = pipeline.compute(
        accommodation_nightly_usd=150.0,
        day_count=3,
        day_plans=[
            {"activities": [
                {"estimated_cost_usd": 0, "is_meal": False},  # free museum
                {"estimated_cost_usd": 15.0, "is_meal": True, "meal_type": "lunch"},
                {"estimated_cost_usd": 30.0, "is_meal": True, "meal_type": "dinner"},
            ]},
            {"activities": [
                {"estimated_cost_usd": 20.0, "is_meal": False},  # paid attraction
                {"estimated_cost_usd": 10.0, "is_meal": True, "meal_type": "lunch"},
            ]},
            {"activities": []},
        ],
        routes_by_day=[
            [{"travel_mode": "walk", "distance_meters": 1000}],
            [{"travel_mode": "transit", "distance_meters": 5000}],
            [],
        ],
    )
    assert result.accommodation == 450.0  # 150 * 3
    assert result.dining == 55.0  # 15 + 30 + 10
    assert result.activities == 20.0  # 0 + 20
    assert result.transport == 2.5  # 1 transit trip
    assert result.total == 527.5
    assert len(result.per_day) == 3


def test_compute_empty():
    pipeline = CostingPipeline()
    result = pipeline.compute(
        accommodation_nightly_usd=100.0,
        day_count=1,
        day_plans=[{"activities": []}],
        routes_by_day=[[]],
    )
    assert result.accommodation == 100.0
    assert result.dining == 0
    assert result.activities == 0
    assert result.transport == 0
    assert result.total == 100.0


def test_compute_drive_transport():
    pipeline = CostingPipeline()
    result = pipeline.compute(
        accommodation_nightly_usd=0,
        day_count=1,
        day_plans=[{"activities": []}],
        routes_by_day=[[{"travel_mode": "drive", "distance_meters": 10000}]],  # 10km
    )
    assert result.transport == 1.5  # 10km * $0.15/km
