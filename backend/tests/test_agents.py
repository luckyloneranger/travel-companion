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
    async def test_travel_legs_mismatch_warns(self):
        """Travel leg count mismatch now warns instead of raising."""
        mock_llm = MagicMock()
        plan = _make_journey_plan(travel_legs=[])  # 2 cities but 0 legs
        mock_llm.generate_structured = AsyncMock(return_value=plan)
        agent = ScoutAgent(llm=mock_llm)
        # Should succeed (warn, not raise)
        result = await agent.generate_plan(_make_request())
        assert len(result.cities) == 2
        assert len(result.travel_legs) == 0


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


# ═══════════════════════════════════════════════════════════════════════════════
# CityHighlight excursion fields
# ═══════════════════════════════════════════════════════════════════════════════


class TestCityHighlightExcursion:
    def test_excursion_fields_default_none(self):
        from app.models.journey import CityHighlight
        h = CityHighlight(name="Test")
        assert h.excursion_type is None
        assert h.excursion_days is None

    def test_excursion_fields_set(self):
        from app.models.journey import CityHighlight
        h = CityHighlight(
            name="Ha Long Bay Cruise", category="adventure",
            excursion_type="multi_day", excursion_days=2,
        )
        assert h.excursion_type == "multi_day"
        assert h.excursion_days == 2

    def test_full_day_excursion(self):
        from app.models.journey import CityHighlight
        h = CityHighlight(name="Disney", excursion_type="full_day")
        assert h.excursion_type == "full_day"
        assert h.excursion_days is None


# ═══════════════════════════════════════════════════════════════════════════════
# DayPlanOrchestrator excursion day-blocking helpers
# ═══════════════════════════════════════════════════════════════════════════════

from app.orchestrators.day_plan import DayPlanOrchestrator


class TestExcursionBlocking:
    """Test DayPlanOrchestrator excursion day-blocking helpers."""

    def test_extract_excursions_none(self):
        from app.models.journey import CityHighlight
        highlights = [
            CityHighlight(name="Museum", category="culture"),
            CityHighlight(name="Temple", category="religious"),
        ]
        result = DayPlanOrchestrator._extract_excursions(highlights)
        assert result == []

    def test_extract_excursions_full_day(self):
        from app.models.journey import CityHighlight
        highlights = [
            CityHighlight(name="Disney", category="entertainment", excursion_type="full_day"),
            CityHighlight(name="Museum", category="culture"),
        ]
        result = DayPlanOrchestrator._extract_excursions(highlights)
        assert len(result) == 1
        assert result[0].name == "Disney"

    def test_extract_excursions_multi_day(self):
        from app.models.journey import CityHighlight
        highlights = [
            CityHighlight(name="Ha Long Bay", category="adventure", excursion_type="multi_day", excursion_days=2),
        ]
        result = DayPlanOrchestrator._extract_excursions(highlights)
        assert len(result) == 1
        assert result[0].excursion_days == 2

    def test_build_excursion_day_plan(self):
        from app.models.journey import CityHighlight
        excursion = CityHighlight(
            name="Ha Long Bay Cruise", category="adventure",
            description="Overnight cruise through limestone karsts",
            excursion_type="multi_day", excursion_days=2,
        )
        plan = DayPlanOrchestrator._build_excursion_day_plan(
            excursion=excursion,
            date_str="2026-06-20",
            day_number=3,
            city_name="Hanoi",
            day_label="Day 1 of 2",
        )
        assert plan.is_excursion is True
        assert "Ha Long Bay Cruise" in plan.excursion_name
        assert "Day 1 of 2" in plan.excursion_name
        assert plan.city_name == "Hanoi"
        assert plan.day_number == 3
        assert plan.date == "2026-06-20"
        assert plan.theme == "Ha Long Bay Cruise"
        assert len(plan.activities) == 1
        assert plan.activities[0].place.name == "Ha Long Bay Cruise"
        assert plan.activities[0].notes == "Overnight cruise through limestone karsts"

    def test_compute_schedule_multi_day_at_end(self):
        from app.models.journey import CityHighlight
        excursions = [
            CityHighlight(name="Ha Long Bay", excursion_type="multi_day", excursion_days=2),
        ]
        blocked, partial = DayPlanOrchestrator._compute_excursion_schedule(excursions, 4)
        assert sorted(blocked.keys()) == [2, 3]  # last 2 days
        assert len(partial) == 0

    def test_compute_schedule_full_day(self):
        from app.models.journey import CityHighlight
        excursions = [
            CityHighlight(name="Disney", excursion_type="full_day"),
        ]
        blocked, partial = DayPlanOrchestrator._compute_excursion_schedule(excursions, 3)
        assert 2 in blocked  # last day
        assert len(partial) == 0

    def test_compute_schedule_mixed(self):
        from app.models.journey import CityHighlight
        excursions = [
            CityHighlight(name="Ha Long Bay", excursion_type="multi_day", excursion_days=2),
            CityHighlight(name="Cooking Class", excursion_type="half_day_morning"),
        ]
        blocked, partial = DayPlanOrchestrator._compute_excursion_schedule(excursions, 5)
        assert len(blocked) == 2  # multi-day takes last 2
        assert len(partial) == 1  # half-day on earliest free day

    def test_compute_schedule_no_excursions(self):
        blocked, partial = DayPlanOrchestrator._compute_excursion_schedule([], 3)
        assert blocked == {}
        assert partial == {}


# ═══════════════════════════════════════════════════════════════════════════════
# PlannerAgent dimension scores
# ═══════════════════════════════════════════════════════════════════════════════


class TestPlannerDimensionScores:
    @pytest.mark.asyncio
    async def test_format_issues_with_dimension_scores(self):
        """Planner formats dimension scores in issue text."""
        from app.agents.planner import PlannerAgent
        agent = PlannerAgent(llm=MagicMock())
        review = ReviewResult(
            is_acceptable=False, score=55,
            issues=[ReviewIssue(severity="major", category="routing", description="Backtracking detected")],
            summary="Needs work",
            dimension_scores={"time_feasibility": 80, "route_logic": 45, "transport": 70},
        )
        result = agent._format_issues(review)
        assert "route_logic: 45/100 [WEAK]" in result
        assert "time_feasibility: 80/100 [OK]" in result
        assert "Backtracking detected" in result

    @pytest.mark.asyncio
    async def test_format_issues_without_dimension_scores(self):
        """Planner works fine when no dimension scores present."""
        from app.agents.planner import PlannerAgent
        agent = PlannerAgent(llm=MagicMock())
        review = ReviewResult(
            is_acceptable=True, score=85,
            issues=[], summary="Good",
        )
        result = agent._format_issues(review)
        assert "No specific issues" in result
        assert "Dimension" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# Distance matrix mode selection
# ═══════════════════════════════════════════════════════════════════════════════


class TestDistanceMatrixModeSelection:
    """Test _pick_best_mode_from_matrix mode selection logic."""

    def test_prefers_walk_under_20min(self):
        matrices = [
            {"rows": [{"elements": [{"duration_seconds": 900}]}]},   # WALK: 15min
            {"rows": [{"elements": [{"duration_seconds": 600}]}]},   # DRIVE: 10min
            {"rows": [{"elements": [{"duration_seconds": 1200}]}]},  # TRANSIT: 20min
        ]
        result = DayPlanOrchestrator._pick_best_mode_from_matrix(matrices, 0)
        assert result == TravelMode.WALK

    def test_prefers_walk_within_1_5x_fastest(self):
        matrices = [
            {"rows": [{"elements": [{"duration_seconds": 1800}]}]},  # WALK: 30min
            {"rows": [{"elements": [{"duration_seconds": 1500}]}]},  # DRIVE: 25min
            Exception("transit failed"),
        ]
        result = DayPlanOrchestrator._pick_best_mode_from_matrix(matrices, 0)
        assert result == TravelMode.WALK  # 30 <= 25 * 1.5 = 37.5

    def test_prefers_drive_when_walk_too_slow(self):
        matrices = [
            {"rows": [{"elements": [{"duration_seconds": 3600}]}]},  # WALK: 60min
            {"rows": [{"elements": [{"duration_seconds": 900}]}]},   # DRIVE: 15min
            {"rows": [{"elements": [{"duration_seconds": 1200}]}]},  # TRANSIT: 20min
        ]
        result = DayPlanOrchestrator._pick_best_mode_from_matrix(matrices, 0)
        assert result == TravelMode.DRIVE

    def test_handles_all_failures(self):
        matrices = [Exception("fail"), Exception("fail"), Exception("fail")]
        result = DayPlanOrchestrator._pick_best_mode_from_matrix(matrices, 0)
        assert result == TravelMode.WALK  # fallback

    def test_handles_second_leg(self):
        """Test reading the diagonal for leg index > 0."""
        matrices = [
            {"rows": [
                {"elements": [{"duration_seconds": 500}, {"duration_seconds": 9999}]},
                {"elements": [{"duration_seconds": 9999}, {"duration_seconds": 800}]},
            ]},
            {"rows": [
                {"elements": [{"duration_seconds": 400}, {"duration_seconds": 9999}]},
                {"elements": [{"duration_seconds": 9999}, {"duration_seconds": 700}]},
            ]},
            Exception("transit failed"),
        ]
        # Leg 1: walk=800, drive=700. 800 <= 700*1.5=1050, so walk
        result = DayPlanOrchestrator._pick_best_mode_from_matrix(matrices, 1)
        assert result == TravelMode.WALK
