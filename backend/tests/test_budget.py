"""Tests for budget and cost tracking."""

from app.models.common import Budget
from app.models.day_plan import Activity, DayPlan, Place, Weather
from app.models.internal import AIPlan, DayGroup
from app.models.trip import TripRequest
from app.models.common import Location
from datetime import date


class TestBudgetModels:
    def test_trip_request_budget_defaults(self):
        req = TripRequest(destination="Paris", total_days=3, start_date=date(2026, 7, 1))
        assert req.budget == Budget.MODERATE
        assert req.budget_usd is None
        assert req.home_currency == "USD"

    def test_trip_request_with_budget(self):
        req = TripRequest(
            destination="Paris", total_days=3, start_date=date(2026, 7, 1),
            budget=Budget.BUDGET, budget_usd=1000, home_currency="EUR",
        )
        assert req.budget == Budget.BUDGET
        assert req.budget_usd == 1000

    def test_activity_cost_fields(self):
        a = Activity(
            time_start="10:00", time_end="12:00", duration_minutes=120,
            place=Place(place_id="p1", name="Museum", location=Location(lat=0, lng=0)),
            estimated_cost_usd=15.0, estimated_cost_local="€13", price_tier="moderate",
        )
        assert a.estimated_cost_usd == 15.0
        assert a.price_tier == "moderate"

    def test_activity_cost_defaults_none(self):
        a = Activity(
            time_start="10:00", time_end="12:00", duration_minutes=120,
            place=Place(place_id="p1", name="Museum", location=Location(lat=0, lng=0)),
        )
        assert a.estimated_cost_usd is None
        assert a.price_tier is None

    def test_day_plan_daily_cost(self):
        dp = DayPlan(date="2026-07-01", day_number=1, daily_cost_usd=85.0)
        assert dp.daily_cost_usd == 85.0

    def test_ai_plan_cost_estimates(self):
        plan = AIPlan(
            selected_place_ids=["p1"], day_groups=[DayGroup(theme="Art", place_ids=["p1"])],
            durations={"p1": 120}, cost_estimates={"p1": 15.0},
        )
        assert plan.cost_estimates["p1"] == 15.0


class TestPriceLevelToTier:
    def test_none(self):
        from app.algorithms.scheduler import _price_level_to_tier
        assert _price_level_to_tier(None) is None

    def test_free(self):
        from app.algorithms.scheduler import _price_level_to_tier
        assert _price_level_to_tier(0) == "free"

    def test_moderate(self):
        from app.algorithms.scheduler import _price_level_to_tier
        assert _price_level_to_tier(2) == "moderate"

    def test_luxury(self):
        from app.algorithms.scheduler import _price_level_to_tier
        assert _price_level_to_tier(4) == "luxury"


class TestBudgetPriceMapping:
    """Tests for budget-to-price-level mapping and price adjustment."""

    def test_budget_to_price_levels(self):
        from app.config.planning import get_target_price_levels
        assert get_target_price_levels("budget") == [1, 2]
        assert get_target_price_levels("moderate") == [2, 3]
        assert get_target_price_levels("expensive") == [3, 4]
        assert get_target_price_levels("luxury") == [4]

    def test_budget_to_price_levels_default(self):
        from app.config.planning import get_target_price_levels
        assert get_target_price_levels("unknown") == [2, 3]

    def test_budget_usd_range(self):
        from app.config.planning import get_budget_usd_range
        lo, hi = get_budget_usd_range("budget")
        assert lo == 30 and hi == 80
        lo, hi = get_budget_usd_range("luxury")
        assert lo == 250 and hi == 600

    def test_budget_fallback_nightly(self):
        from app.config.planning import get_budget_fallback_nightly
        assert get_budget_fallback_nightly("budget") == 55
        assert get_budget_fallback_nightly("moderate") == 140
        assert get_budget_fallback_nightly("luxury") == 425

    def test_adjust_price_clamps_high(self):
        from app.config.planning import adjust_price_for_budget
        adjusted = adjust_price_for_budget(200, price_level=1, budget="moderate")
        assert adjusted <= 80

    def test_adjust_price_raises_low(self):
        from app.config.planning import adjust_price_for_budget
        adjusted = adjust_price_for_budget(80, price_level=4, budget="luxury")
        assert adjusted >= 250

    def test_adjust_price_no_price_level_keeps_estimate(self):
        from app.config.planning import adjust_price_for_budget
        adjusted = adjust_price_for_budget(170, price_level=None, budget="moderate")
        assert adjusted == 170

    def test_adjust_price_within_range_unchanged(self):
        from app.config.planning import adjust_price_for_budget
        adjusted = adjust_price_for_budget(120, price_level=2, budget="moderate")
        assert adjusted == 120

    def test_price_level_matches_budget(self):
        from app.config.planning import price_level_matches_budget
        assert price_level_matches_budget(2, "moderate") is True
        assert price_level_matches_budget(1, "luxury") is False
        assert price_level_matches_budget(4, "budget") is False
        assert price_level_matches_budget(None, "moderate") is True
