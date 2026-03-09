"""Unit tests for the quality scorer and evaluators."""

import pytest
from app.algorithms.quality.scorer import ItineraryScorer, _grade_from_score
from app.algorithms.quality.evaluators import (
    MealTimingEvaluator,
    GeographicClusteringEvaluator,
    TravelEfficiencyEvaluator,
    VarietyEvaluator,
    OpeningHoursEvaluator,
    ThemeAlignmentEvaluator,
    DurationAppropriatenessEvaluator,
)
from app.models.common import Location, TravelMode
from app.models.day_plan import Activity, DayPlan, Place, Route


def _make_activity(
    name: str,
    category: str,
    time_start: str,
    time_end: str,
    duration: int,
    lat: float = 48.0,
    lng: float = 2.0,
    route_to_next: Route | None = None,
    opening_hours: list[str] | None = None,
) -> Activity:
    """Helper to create an Activity."""
    return Activity(
        time_start=time_start,
        time_end=time_end,
        duration_minutes=duration,
        place=Place(
            place_id=f"place_{name.replace(' ', '_')}",
            name=name,
            address=f"{name} address",
            location=Location(lat=lat, lng=lng),
            category=category,
            opening_hours=opening_hours or [],
        ),
        route_to_next=route_to_next,
    )


def _make_day(
    day_number: int,
    activities: list[Activity],
    theme: str = "General Exploration",
    date: str = "2026-03-04",
    city_name: str = "Paris",
) -> DayPlan:
    """Helper to create a DayPlan."""
    return DayPlan(
        date=date,
        day_number=day_number,
        theme=theme,
        activities=activities,
        city_name=city_name,
    )


def _make_good_day() -> DayPlan:
    """Create a well-structured day plan for testing."""
    return _make_day(
        day_number=1,
        theme="Heritage & Culture",
        activities=[
            _make_activity("Louvre Museum", "museum", "09:00", "11:00", 120, lat=48.860, lng=2.337),
            _make_activity("Café de Flore", "restaurant", "12:30", "13:30", 60, lat=48.854, lng=2.333,
                           route_to_next=Route(distance_meters=800, duration_seconds=600)),
            _make_activity("Notre Dame", "tourist_attraction", "14:00", "15:30", 90, lat=48.853, lng=2.349,
                           route_to_next=Route(distance_meters=500, duration_seconds=420)),
            _make_activity("Sacré-Cœur", "tourist_attraction", "16:00", "17:00", 60, lat=48.887, lng=2.343,
                           route_to_next=Route(distance_meters=2000, duration_seconds=1200)),
            _make_activity("Le Petit Cler", "restaurant", "18:30", "19:30", 60, lat=48.856, lng=2.311),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Grade helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestGradeFromScore:
    def test_a_grade(self):
        assert _grade_from_score(95) == "A"

    def test_b_grade(self):
        assert _grade_from_score(75) == "B"

    def test_d_grade(self):
        assert _grade_from_score(50) == "D"


# ═══════════════════════════════════════════════════════════════════════════════
# ItineraryScorer
# ═══════════════════════════════════════════════════════════════════════════════

class TestItineraryScorer:
    def test_empty_day_plans(self):
        scorer = ItineraryScorer()
        report = scorer.evaluate([])
        assert report.overall_score is not None
        assert report.overall_grade is not None

    def test_good_day_gets_decent_score(self):
        scorer = ItineraryScorer()
        report = scorer.evaluate([_make_good_day()])
        assert report.overall_score >= 40  # Should be decent

    def test_has_all_7_metrics(self):
        scorer = ItineraryScorer()
        report = scorer.evaluate([_make_good_day()])
        assert len(report.metrics) == 7

    def test_quick_score_returns_tuple(self):
        scorer = ItineraryScorer()
        score, grade = scorer.get_quick_score([_make_good_day()])
        assert isinstance(score, float)
        assert isinstance(grade, str)

    def test_weights_sum_to_one(self):
        scorer = ItineraryScorer()
        total_weight = sum(ev.weight for ev in scorer.evaluators)
        assert total_weight == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# Individual Evaluators
# ═══════════════════════════════════════════════════════════════════════════════

class TestMealTimingEvaluator:
    def test_empty(self):
        ev = MealTimingEvaluator()
        result = ev.evaluate([])
        assert result.score == 0

    def test_day_with_proper_meals(self):
        ev = MealTimingEvaluator()
        day = _make_good_day()  # Has lunch at 12:30 and dinner at 18:30
        result = ev.evaluate([day])
        assert result.score > 50

    def test_day_without_meals(self):
        ev = MealTimingEvaluator()
        day = _make_day(1, [
            _make_activity("Museum", "museum", "09:00", "11:00", 120),
            _make_activity("Park", "park", "11:30", "13:00", 90),
        ])
        result = ev.evaluate([day])
        assert "No lunch" in result.issues[0] or "No dinner" in result.issues[0]


class TestGeographicClusteringEvaluator:
    def test_empty(self):
        ev = GeographicClusteringEvaluator()
        result = ev.evaluate([])
        assert result.score == 100

    def test_clustered_activities(self):
        ev = GeographicClusteringEvaluator()
        day = _make_day(1, [
            _make_activity("A", "museum", "09:00", "10:00", 60, lat=48.860, lng=2.337),
            _make_activity("B", "park", "10:30", "11:30", 60, lat=48.861, lng=2.338),
            _make_activity("C", "cafe", "12:00", "13:00", 60, lat=48.859, lng=2.336),
        ])
        result = ev.evaluate([day])
        assert result.score >= 80  # Close together

    def test_scattered_activities_penalized(self):
        ev = GeographicClusteringEvaluator()
        day = _make_day(1, [
            _make_activity("A", "museum", "09:00", "10:00", 60, lat=48.0, lng=2.0),
            _make_activity("B", "park", "10:30", "11:30", 60, lat=49.0, lng=3.0),
            _make_activity("C", "cafe", "12:00", "13:00", 60, lat=47.0, lng=1.0),
        ])
        result = ev.evaluate([day])
        assert result.score < 80  # Spread far apart


class TestTravelEfficiencyEvaluator:
    def test_empty(self):
        ev = TravelEfficiencyEvaluator()
        result = ev.evaluate([])
        assert result.score == 100

    def test_short_travel_times(self):
        ev = TravelEfficiencyEvaluator()
        day = _make_day(1, [
            _make_activity("A", "museum", "09:00", "10:00", 60,
                           route_to_next=Route(distance_meters=500, duration_seconds=300)),
            _make_activity("B", "park", "10:30", "11:30", 60),
        ])
        result = ev.evaluate([day])
        assert result.score >= 90

    def test_long_travel_penalized(self):
        ev = TravelEfficiencyEvaluator()
        day = _make_day(1, [
            _make_activity("A", "museum", "09:00", "10:00", 60,
                           route_to_next=Route(distance_meters=50000, duration_seconds=3600)),
            _make_activity("B", "park", "11:00", "12:00", 60),
        ])
        result = ev.evaluate([day])
        assert result.score < 90


class TestVarietyEvaluator:
    def test_empty(self):
        ev = VarietyEvaluator()
        result = ev.evaluate([])
        assert result.score == 100

    def test_diverse_activities(self):
        ev = VarietyEvaluator()
        day = _make_day(1, [
            _make_activity("Museum", "museum", "09:00", "10:00", 60),
            _make_activity("Lunch", "restaurant", "12:00", "13:00", 60),
            _make_activity("Park", "park", "14:00", "15:00", 60),
            _make_activity("Temple", "tourist_attraction", "16:00", "17:00", 60),
        ])
        result = ev.evaluate([day])
        assert result.score >= 70

    def test_repetitive_penalized(self):
        ev = VarietyEvaluator()
        day = _make_day(1, [
            _make_activity("Museum A", "museum", "09:00", "10:00", 60),
            _make_activity("Museum B", "museum", "10:30", "11:30", 60),
            _make_activity("Museum C", "museum", "12:00", "13:00", 60),
            _make_activity("Museum D", "museum", "14:00", "15:00", 60),
        ])
        result = ev.evaluate([day])
        assert any("repetitive" in issue.lower() for issue in result.issues)


class TestOpeningHoursEvaluator:
    def test_empty(self):
        ev = OpeningHoursEvaluator()
        result = ev.evaluate([])
        assert result.score == 100

    def test_no_opening_hours_is_unknown(self):
        ev = OpeningHoursEvaluator()
        day = _make_day(1, [
            _make_activity("A", "museum", "09:00", "10:00", 60),
        ])
        result = ev.evaluate([day])
        assert result.score == 100  # Unknown counts as valid


class TestThemeAlignmentEvaluator:
    def test_empty(self):
        ev = ThemeAlignmentEvaluator()
        result = ev.evaluate([])
        assert result.score == 100

    def test_matching_theme(self):
        ev = ThemeAlignmentEvaluator()
        day = _make_day(1, theme="Heritage & Culture", activities=[
            _make_activity("Old Fort", "fort", "09:00", "11:00", 120),
            _make_activity("Lunch", "restaurant", "12:00", "13:00", 60),
            _make_activity("National Museum", "museum", "14:00", "16:00", 120),
        ])
        result = ev.evaluate([day])
        assert result.score >= 50

    def test_mismatched_theme(self):
        ev = ThemeAlignmentEvaluator()
        day = _make_day(1, theme="Nature & Parks", activities=[
            _make_activity("Shopping Mall A", "shopping", "09:00", "11:00", 120),
            _make_activity("Lunch", "restaurant", "12:00", "13:00", 60),
            _make_activity("Shopping Mall B", "shopping", "14:00", "16:00", 120),
        ])
        result = ev.evaluate([day])
        # Shopping doesn't match nature theme
        assert result.score < 100


class TestDurationAppropriatenessEvaluator:
    def test_empty(self):
        ev = DurationAppropriatenessEvaluator()
        result = ev.evaluate([])
        assert result.score == 100

    def test_appropriate_durations(self):
        ev = DurationAppropriatenessEvaluator()
        day = _make_day(1, [
            _make_activity("Museum", "museum", "09:00", "11:00", 120),  # 90-180 range
            _make_activity("Lunch", "restaurant", "12:00", "13:00", 60),  # 45-90 range
        ])
        result = ev.evaluate([day])
        assert result.score >= 80

    def test_unrealistic_duration_flagged(self):
        ev = DurationAppropriatenessEvaluator()
        day = _make_day(1, [
            _make_activity("Museum", "museum", "09:00", "17:00", 500),  # >480 min
        ])
        result = ev.evaluate([day])
        assert any("unrealistic" in i.lower() for i in result.issues)

    def test_too_short_flagged(self):
        ev = DurationAppropriatenessEvaluator()
        day = _make_day(1, [
            _make_activity("Museum", "museum", "09:00", "09:10", 10),  # <15 min
        ])
        result = ev.evaluate([day])
        assert any("too short" in i.lower() for i in result.issues)


class TestOpeningHoursEndTimeCheck:
    """Tests that evaluator checks activity END time, not just start."""

    def test_activity_ending_after_close_flagged(self):
        """Activity starting within hours but ending after close should be flagged."""
        act = _make_activity(
            "Museum", "museum", "15:30", "17:30", 120,  # 15:30 + 120min = 17:30
            opening_hours=["Wed: 09:00 \u2013 17:00"],
        )
        day = _make_day(1, [act], date="2026-04-15")  # Wednesday
        evaluator = OpeningHoursEvaluator()
        result = evaluator.evaluate([day])
        assert result.issues, "Should flag activity ending after 17:00 close"
        assert any("17:00" in issue for issue in result.issues)

    def test_activity_fitting_within_hours_not_flagged(self):
        """Activity fully within opening hours should not be flagged."""
        act = _make_activity(
            "Museum", "museum", "14:00", "15:30", 90,  # 14:00 + 90min = 15:30
            opening_hours=["Wed: 09:00 \u2013 17:00"],
        )
        day = _make_day(1, [act], date="2026-04-15")  # Wednesday
        evaluator = OpeningHoursEvaluator()
        result = evaluator.evaluate([day])
        opening_issues = [i for i in result.issues if "close" in i.lower() or "17:00" in i]
        assert not opening_issues, "Should not flag activity that fits within hours"
