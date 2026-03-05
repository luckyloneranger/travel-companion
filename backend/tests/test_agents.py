"""Unit tests for Scout, Reviewer, and Planner agents."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.agents.scout import ScoutAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.planner import PlannerAgent
from app.agents.day_planner import DayPlannerAgent
from app.models.common import Location, Pace, TransportMode, TravelMode
from app.models.internal import AIPlan, DayGroup, PlaceCandidate
from app.models.journey import (
    CityStop,
    JourneyPlan,
    ReviewResult,
    ReviewIssue,
    TravelLeg,
)
from app.models.trip import TripRequest
from app.services.llm.exceptions import LLMValidationError


def _make_request(**overrides) -> TripRequest:
    """Build a sample TripRequest."""
    defaults = {
        "destination": "Italy",
        "origin": "London",
        "total_days": 5,
        "start_date": date(2026, 6, 15),
        "interests": ["food", "culture"],
        "pace": Pace.MODERATE,
        "travel_mode": TravelMode.WALK,
    }
    defaults.update(overrides)
    return TripRequest(**defaults)


from app.models.trip import TripRequest


def _make_journey_plan(**overrides) -> JourneyPlan:
    """Build a sample JourneyPlan."""
    defaults = {
        "theme": "Italian Discovery",
        "summary": "A 5-day journey through Italy",
        "origin": "London",
        "cities": [
            CityStop(name="Rome", country="Italy", days=3, why_visit="History"),
            CityStop(name="Florence", country="Italy", days=2, why_visit="Art"),
        ],
        "travel_legs": [
            TravelLeg(
                from_city="Rome",
                to_city="Florence",
                mode=TransportMode.TRAIN,
                duration_hours=1.5,
            ),
        ],
        "total_days": 5,
    }
    defaults.update(overrides)
    return JourneyPlan(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# ScoutAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoutAgent:
    @pytest.mark.asyncio
    async def test_generate_plan_calls_llm(self):
        """ScoutAgent calls generate_structured on the LLM."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(return_value=_make_journey_plan())

        agent = ScoutAgent(llm=mock_llm)
        request = _make_request()
        result = await agent.generate_plan(request)

        mock_llm.generate_structured.assert_called_once()
        call_kwargs = mock_llm.generate_structured.call_args
        assert call_kwargs.kwargs.get("schema") == JourneyPlan or call_kwargs[1].get("schema") == JourneyPlan

    @pytest.mark.asyncio
    async def test_generate_plan_returns_journey_plan(self):
        """ScoutAgent returns a valid JourneyPlan."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(return_value=_make_journey_plan())

        agent = ScoutAgent(llm=mock_llm)
        result = await agent.generate_plan(_make_request())

        assert isinstance(result, JourneyPlan)
        assert result.theme == "Italian Discovery"
        assert len(result.cities) == 2

    @pytest.mark.asyncio
    async def test_generate_plan_preserves_origin(self):
        """ScoutAgent should set origin from request."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(return_value=_make_journey_plan())

        agent = ScoutAgent(llm=mock_llm)
        result = await agent.generate_plan(_make_request(origin="Paris"))

        assert isinstance(result, JourneyPlan)

    @pytest.mark.asyncio
    async def test_generate_plan_validates_legs(self):
        """ScoutAgent validates that travel legs exist."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(return_value=_make_journey_plan())

        agent = ScoutAgent(llm=mock_llm)
        result = await agent.generate_plan(_make_request())
        assert len(result.travel_legs) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# ReviewerAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestReviewerAgent:
    @pytest.mark.asyncio
    async def test_review_calls_llm(self):
        """ReviewerAgent calls generate_structured on the LLM."""
        mock_llm = MagicMock()
        review = ReviewResult(
            is_acceptable=True,
            score=85,
            issues=[],
            summary="Good plan",
            iteration=1,
        )
        mock_llm.generate_structured = AsyncMock(return_value=review)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request())

        mock_llm.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_returns_review_result(self):
        """ReviewerAgent returns a valid ReviewResult."""
        mock_llm = MagicMock()
        review = ReviewResult(
            is_acceptable=True,
            score=85,
            issues=[],
            summary="Good plan overall",
            iteration=1,
        )
        mock_llm.generate_structured = AsyncMock(return_value=review)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request())

        assert isinstance(result, ReviewResult)
        assert result.score == 85
        assert result.is_acceptable is True

    @pytest.mark.asyncio
    async def test_review_with_issues(self):
        """ReviewerAgent handles review with issues."""
        mock_llm = MagicMock()
        review = ReviewResult(
            is_acceptable=False,
            score=45,
            issues=[
                ReviewIssue(
                    severity="major",
                    category="logistics",
                    description="Missing return flight",
                    suggested_fix="Add return leg",
                )
            ],
            summary="Needs improvement",
            iteration=1,
        )
        mock_llm.generate_structured = AsyncMock(return_value=review)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request())

        assert result.is_acceptable is False
        assert result.score == 45
        assert len(result.issues) == 1
        assert result.issues[0].severity == "major"

    @pytest.mark.asyncio
    async def test_review_passes_iteration(self):
        """ReviewerAgent passes iteration parameter correctly."""
        mock_llm = MagicMock()
        review = ReviewResult(
            is_acceptable=True,
            score=90,
            issues=[],
            summary="Excellent plan",
            iteration=1,
        )
        mock_llm.generate_structured = AsyncMock(return_value=review)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request(), iteration=3)

        assert result.iteration == 3

    @pytest.mark.asyncio
    async def test_review_score_boundaries(self):
        """ReviewerAgent score is bounded 0-100."""
        mock_llm = MagicMock()

        for score_val in [0, 50, 100]:
            review = ReviewResult(
                is_acceptable=score_val >= 70,
                score=score_val,
                issues=[],
                summary="Test",
                iteration=1,
            )
            mock_llm.generate_structured = AsyncMock(return_value=review)

            agent = ReviewerAgent(llm=mock_llm)
            result = await agent.review(_make_journey_plan(), _make_request())
            assert 0 <= result.score <= 100


# ═══════════════════════════════════════════════════════════════════════════════
# ScoutAgent validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoutValidation:
    @pytest.mark.asyncio
    async def test_empty_cities_raises(self):
        mock_llm = MagicMock()
        plan = _make_journey_plan(cities=[], travel_legs=[])
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = ScoutAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="No cities"):
            await agent.generate_plan(_make_request())

    @pytest.mark.asyncio
    async def test_city_missing_name_raises(self):
        mock_llm = MagicMock()
        plan = _make_journey_plan(
            cities=[CityStop(name="", country="Italy", days=3, why_visit="")],
            travel_legs=[],
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = ScoutAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="empty name"):
            await agent.generate_plan(_make_request())

    @pytest.mark.asyncio
    async def test_travel_legs_mismatch_raises(self):
        mock_llm = MagicMock()
        plan = _make_journey_plan(travel_legs=[])  # 2 cities but 0 legs
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = ScoutAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="travel legs"):
            await agent.generate_plan(_make_request())


# ═══════════════════════════════════════════════════════════════════════════════
# PlannerAgent validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlannerValidation:
    @pytest.mark.asyncio
    async def test_empty_cities_raises(self):
        mock_llm = MagicMock()
        empty_plan = _make_journey_plan(cities=[], travel_legs=[])
        mock_llm.generate_structured = AsyncMock(return_value=empty_plan)
        agent = PlannerAgent(llm=mock_llm)
        original = _make_journey_plan()
        review = ReviewResult(is_acceptable=False, score=40, issues=[], summary="Bad", iteration=1)
        with pytest.raises(LLMValidationError, match="No cities"):
            await agent.fix_plan(original, review, _make_request())

    @pytest.mark.asyncio
    async def test_valid_fix_returns_plan(self):
        mock_llm = MagicMock()
        fixed = _make_journey_plan(theme="Fixed Plan")
        mock_llm.generate_structured = AsyncMock(return_value=fixed)
        agent = PlannerAgent(llm=mock_llm)
        original = _make_journey_plan()
        review = ReviewResult(is_acceptable=False, score=40, issues=[], summary="Bad", iteration=1)
        result = await agent.fix_plan(original, review, _make_request())
        assert result.theme == "Fixed Plan"


# ═══════════════════════════════════════════════════════════════════════════════
# DayPlannerAgent validation
# ═══════════════════════════════════════════════════════════════════════════════


def _make_candidates(n: int = 5) -> list[PlaceCandidate]:
    return [
        PlaceCandidate(
            place_id=f"place_{i}",
            name=f"Place {i}",
            address=f"Address {i}",
            location=Location(lat=48.8 + i * 0.01, lng=2.3 + i * 0.01),
            types=["tourist_attraction"],
        )
        for i in range(n)
    ]


class TestDayPlannerValidation:
    @pytest.mark.asyncio
    async def test_empty_day_groups_raises(self):
        mock_llm = MagicMock()
        empty_plan = AIPlan(selected_place_ids=[], day_groups=[], durations={})
        mock_llm.generate_structured = AsyncMock(return_value=empty_plan)
        agent = DayPlannerAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="No day groups"):
            await agent.plan_days(
                candidates=_make_candidates(),
                city_name="Paris", num_days=2,
                interests=["art"], pace="moderate",
            )

    @pytest.mark.asyncio
    async def test_day_with_no_valid_places_raises(self):
        mock_llm = MagicMock()
        plan = AIPlan(
            selected_place_ids=["place_0", "orphan_only"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0"]),
                DayGroup(theme="Day 2", place_ids=["orphan_only"]),  # only orphan
            ],
            durations={},
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = DayPlannerAgent(llm=mock_llm)
        with pytest.raises(LLMValidationError, match="no places"):
            await agent.plan_days(
                candidates=_make_candidates(3),
                city_name="Paris", num_days=2,
                interests=["art"], pace="moderate",
            )

    @pytest.mark.asyncio
    async def test_orphan_ids_cleaned(self):
        mock_llm = MagicMock()
        candidates = _make_candidates(3)
        plan = AIPlan(
            selected_place_ids=["place_0", "place_1", "orphan_99"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0", "place_1", "orphan_99"]),
            ],
            durations={"place_0": 60, "orphan_99": 30},
            cost_estimates={"orphan_99": 10.0},
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = DayPlannerAgent(llm=mock_llm)
        result = await agent.plan_days(
            candidates=candidates,
            city_name="Paris", num_days=1,
            interests=["art"], pace="moderate",
        )
        assert "orphan_99" not in result.selected_place_ids
        assert "orphan_99" not in result.day_groups[0].place_ids
        assert "orphan_99" not in result.durations
        assert "orphan_99" not in result.cost_estimates

    @pytest.mark.asyncio
    async def test_valid_plan_passes(self):
        mock_llm = MagicMock()
        candidates = _make_candidates(3)
        plan = AIPlan(
            selected_place_ids=["place_0", "place_1", "place_2"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0", "place_1"]),
                DayGroup(theme="Day 2", place_ids=["place_2"]),
            ],
            durations={"place_0": 60, "place_1": 90, "place_2": 120},
        )
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = DayPlannerAgent(llm=mock_llm)
        result = await agent.plan_days(
            candidates=candidates,
            city_name="Paris", num_days=2,
            interests=["art"], pace="moderate",
        )
        assert len(result.day_groups) == 2
        assert len(result.selected_place_ids) == 3
