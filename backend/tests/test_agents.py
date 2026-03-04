"""Unit tests for Scout and Reviewer agents."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.agents.scout import ScoutAgent
from app.agents.reviewer import ReviewerAgent
from app.models.common import Pace, TransportMode, TravelMode
from app.models.journey import (
    CityStop,
    JourneyPlan,
    ReviewResult,
    ReviewIssue,
    TravelLeg,
)
from app.models.trip import TripRequest


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
                from_city="London",
                to_city="Rome",
                mode=TransportMode.FLIGHT,
                duration_hours=2.5,
            ),
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
        plan_data = _make_journey_plan().model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=plan_data)

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
        plan_data = _make_journey_plan().model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=plan_data)

        agent = ScoutAgent(llm=mock_llm)
        result = await agent.generate_plan(_make_request())

        assert isinstance(result, JourneyPlan)
        assert result.theme == "Italian Discovery"
        assert len(result.cities) == 2

    @pytest.mark.asyncio
    async def test_generate_plan_preserves_origin(self):
        """ScoutAgent should set origin from request."""
        mock_llm = MagicMock()
        plan_data = _make_journey_plan().model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=plan_data)

        agent = ScoutAgent(llm=mock_llm)
        result = await agent.generate_plan(_make_request(origin="Paris"))

        assert isinstance(result, JourneyPlan)

    @pytest.mark.asyncio
    async def test_generate_plan_validates_legs(self):
        """ScoutAgent validates that travel legs exist."""
        mock_llm = MagicMock()
        plan_data = _make_journey_plan().model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=plan_data)

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
        review_data = ReviewResult(
            is_acceptable=True,
            score=85,
            issues=[],
            summary="Good plan",
            iteration=1,
        ).model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=review_data)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request())

        mock_llm.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_returns_review_result(self):
        """ReviewerAgent returns a valid ReviewResult."""
        mock_llm = MagicMock()
        review_data = ReviewResult(
            is_acceptable=True,
            score=85,
            issues=[],
            summary="Good plan overall",
            iteration=1,
        ).model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=review_data)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request())

        assert isinstance(result, ReviewResult)
        assert result.score == 85
        assert result.is_acceptable is True

    @pytest.mark.asyncio
    async def test_review_with_issues(self):
        """ReviewerAgent handles review with issues."""
        mock_llm = MagicMock()
        review_data = ReviewResult(
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
        ).model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=review_data)

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
        review_data = ReviewResult(
            is_acceptable=True,
            score=90,
            issues=[],
            summary="Excellent plan",
            iteration=3,
        ).model_dump(mode="json")
        mock_llm.generate_structured = AsyncMock(return_value=review_data)

        agent = ReviewerAgent(llm=mock_llm)
        result = await agent.review(_make_journey_plan(), _make_request(), iteration=3)

        assert result.iteration == 3

    @pytest.mark.asyncio
    async def test_review_score_boundaries(self):
        """ReviewerAgent score is bounded 0-100."""
        mock_llm = MagicMock()

        for score_val in [0, 50, 100]:
            review_data = ReviewResult(
                is_acceptable=score_val >= 70,
                score=score_val,
                issues=[],
                summary="Test",
                iteration=1,
            ).model_dump(mode="json")
            mock_llm.generate_structured = AsyncMock(return_value=review_data)

            agent = ReviewerAgent(llm=mock_llm)
            result = await agent.review(_make_journey_plan(), _make_request())
            assert 0 <= result.score <= 100
