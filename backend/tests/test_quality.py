"""Tests for the quality evaluation module."""

import pytest
from datetime import date

from app.generators.day_plan.quality import ItineraryScorer, QualityReport, QualityGrade
from app.generators.day_plan.quality.models import MetricResult, QualityScore, METRIC_WEIGHTS
from app.generators.day_plan.quality.evaluators import (
    MealTimingEvaluator,
    GeographicClusteringEvaluator,
    VarietyEvaluator,
)
from app.models import (
    ItineraryResponse,
    DayPlan,
    Activity,
    Place,
    Location,
    Destination,
    TripDates,
    Summary,
    GenerationMode,
)


class TestQualityModels:
    """Tests for quality data models."""

    def test_quality_grade_from_score(self):
        """Test grade assignment from scores."""
        assert QualityGrade.from_score(95) == QualityGrade.A_PLUS
        assert QualityGrade.from_score(92) == QualityGrade.A
        assert QualityGrade.from_score(87) == QualityGrade.A_MINUS
        assert QualityGrade.from_score(82) == QualityGrade.B_PLUS
        assert QualityGrade.from_score(77) == QualityGrade.B
        assert QualityGrade.from_score(72) == QualityGrade.B_MINUS
        assert QualityGrade.from_score(67) == QualityGrade.C_PLUS
        assert QualityGrade.from_score(62) == QualityGrade.C
        assert QualityGrade.from_score(57) == QualityGrade.C_MINUS
        assert QualityGrade.from_score(52) == QualityGrade.D
        assert QualityGrade.from_score(45) == QualityGrade.F

    def test_metric_result_creation(self):
        """Test MetricResult creation and grade assignment."""
        result = MetricResult(
            name="Test Metric",
            score=85.5,
            weight=0.2,
            issues=["Issue 1"],
            suggestions=["Suggestion 1"],
        )
        
        assert result.name == "Test Metric"
        assert result.score == 85.5
        assert result.grade == QualityGrade.A_MINUS
        assert len(result.issues) == 1

    def test_metric_weights_sum_to_one(self):
        """Verify metric weights sum to 1.0."""
        total = sum(METRIC_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, should be ~1.0"


class TestItineraryScorer:
    """Tests for the ItineraryScorer."""

    @pytest.fixture
    def scorer(self):
        return ItineraryScorer()

    @pytest.fixture
    def sample_itinerary(self):
        """Create a sample itinerary for testing."""
        return ItineraryResponse(
            destination=Destination(
                name="Test City",
                place_id="test_place_123",
                location=Location(lat=23.0, lng=72.0),
                country="Test Country",
                timezone="UTC",
            ),
            trip_dates=TripDates(
                start=date(2026, 3, 1),
                end=date(2026, 3, 2),
                duration_days=2,
            ),
            days=[
                DayPlan(
                    date=date(2026, 3, 1),
                    day_number=1,
                    theme="Heritage Walk",
                    activities=[
                        Activity(
                            time_start="09:00",
                            time_end="10:00",
                            duration_minutes=60,
                            place=Place(
                                place_id="p1",
                                name="Test Museum",
                                address="123 Test St",
                                location=Location(lat=23.0, lng=72.0),
                                category="museum",
                                rating=4.5,
                            ),
                        ),
                        Activity(
                            time_start="10:30",
                            time_end="11:30",
                            duration_minutes=60,
                            place=Place(
                                place_id="p2",
                                name="Historic Fort",
                                address="456 Fort Rd",
                                location=Location(lat=23.01, lng=72.01),
                                category="attraction",
                                rating=4.3,
                            ),
                        ),
                        Activity(
                            time_start="12:30",
                            time_end="13:30",
                            duration_minutes=60,
                            place=Place(
                                place_id="p3",
                                name="Local Restaurant",
                                address="789 Food St",
                                location=Location(lat=23.02, lng=72.02),
                                category="dining",
                                rating=4.2,
                            ),
                        ),
                        Activity(
                            time_start="19:00",
                            time_end="20:00",
                            duration_minutes=60,
                            place=Place(
                                place_id="p4",
                                name="Evening Cafe",
                                address="321 Night Rd",
                                location=Location(lat=23.03, lng=72.03),
                                category="restaurant",
                                rating=4.4,
                            ),
                        ),
                    ],
                ),
            ],
            summary=Summary(
                total_activities=4,
                total_distance_km=5.0,
                interests_covered=["history", "food"],
            ),
            generated_at="2026-03-01T00:00:00Z",
            generation_mode=GenerationMode.FAST,
        )

    def test_scorer_evaluate_returns_report(self, scorer, sample_itinerary):
        """Test that scorer returns a QualityReport."""
        report = scorer.evaluate(sample_itinerary)
        
        assert isinstance(report, QualityReport)
        assert 0 <= report.overall_score <= 100
        assert report.overall_grade in QualityGrade
        assert report.destination == "Test City"
        assert report.num_days == 1

    def test_scorer_has_all_evaluators(self, scorer):
        """Verify scorer has all expected evaluators."""
        evaluator_names = {e.name for e in scorer.evaluators}
        
        expected = {
            "Meal Timing",
            "Geographic Clustering",
            "Travel Efficiency",
            "Variety & Diversity",
            "Opening Hours",
            "Theme Alignment",
            "Duration Appropriateness",
        }
        
        assert evaluator_names == expected

    def test_quick_score(self, scorer, sample_itinerary):
        """Test quick score method."""
        score, grade = scorer.get_quick_score(sample_itinerary)
        
        assert isinstance(score, float)
        assert isinstance(grade, str)
        assert grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]


class TestMealTimingEvaluator:
    """Tests for meal timing evaluation."""

    @pytest.fixture
    def evaluator(self):
        return MealTimingEvaluator()

    def test_evaluator_properties(self, evaluator):
        """Test evaluator name and weight."""
        assert evaluator.name == "Meal Timing"
        assert evaluator.weight == METRIC_WEIGHTS["meal_timing"]


class TestGeographicClusteringEvaluator:
    """Tests for geographic clustering evaluation."""

    @pytest.fixture
    def evaluator(self):
        return GeographicClusteringEvaluator()

    def test_haversine_calculation(self, evaluator):
        """Test distance calculation via centralized utility."""
        from app.utils.geo import haversine_distance
        # NYC to LA is roughly 3,940 km
        distance = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900 < distance < 4000


class TestVarietyEvaluator:
    """Tests for variety evaluation."""

    @pytest.fixture
    def evaluator(self):
        return VarietyEvaluator()

    def test_evaluator_properties(self, evaluator):
        """Test evaluator name and weight."""
        assert evaluator.name == "Variety & Diversity"
        assert evaluator.weight == METRIC_WEIGHTS["variety"]
