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


class TestBudgetFallbackNightly:
    """Tests for budget fallback nightly rates."""

    def test_fallback_values(self):
        from app.config.planning import get_budget_fallback_nightly
        assert get_budget_fallback_nightly("budget") == 50
        assert get_budget_fallback_nightly("moderate") == 120
        assert get_budget_fallback_nightly("expensive") == 250
        assert get_budget_fallback_nightly("luxury") == 400

    def test_fallback_unknown_defaults_moderate(self):
        from app.config.planning import get_budget_fallback_nightly
        assert get_budget_fallback_nightly("unknown") == 120


class TestAccommodationBudgetRange:
    """Tests for destination-aware budget range fields."""

    def test_accommodation_budget_range(self):
        from app.models.journey import Accommodation
        acc = Accommodation(
            name="Hotel Granvia Kyoto",
            budget_range_usd=[120, 180],
            booking_hint="Search Booking.com for hotels in Kyoto Station area",
        )
        assert acc.budget_range_usd == [120, 180]
        assert acc.booking_hint is not None

    def test_accommodation_budget_range_optional(self):
        from app.models.journey import Accommodation
        acc = Accommodation(name="Some Hotel")
        assert acc.budget_range_usd is None
        assert acc.booking_hint is None

    def test_city_stop_alternatives(self):
        from app.models.journey import CityStop, Accommodation
        city = CityStop(
            name="Kyoto", country="Japan", days=3,
            accommodation=Accommodation(name="Hotel A"),
            accommodation_alternatives=[
                Accommodation(name="Hotel B"),
                Accommodation(name="Hotel C"),
            ],
        )
        assert len(city.accommodation_alternatives) == 2

    def test_city_stop_alternatives_default_empty(self):
        from app.models.journey import CityStop
        city = CityStop(name="Tokyo", country="Japan", days=4)
        assert city.accommodation_alternatives == []
