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
    Accommodation,
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
            CityStop(
                name="Rome", country="Italy", days=3, why_visit="History",
                accommodation=Accommodation(name="Hotel Roma", estimated_nightly_usd=120),
            ),
            CityStop(
                name="Florence", country="Italy", days=2, why_visit="Art",
                accommodation=Accommodation(name="Hotel Firenze", estimated_nightly_usd=110),
            ),
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
        # Add a dining candidate so dining validation passes
        dining_candidate = PlaceCandidate(
            place_id="dining_0",
            name="Restaurant 0",
            address="Dining Address",
            location=Location(lat=48.85, lng=2.35),
            types=["restaurant"],
        )
        candidates.append(dining_candidate)
        plan = AIPlan(
            selected_place_ids=["place_0", "place_1", "dining_0", "orphan_99"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0", "place_1", "dining_0", "orphan_99"]),
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
        # Add dining candidates so dining validation passes
        for i in range(2):
            candidates.append(PlaceCandidate(
                place_id=f"dining_{i}",
                name=f"Restaurant {i}",
                address=f"Dining Address {i}",
                location=Location(lat=48.85 + i * 0.01, lng=2.35 + i * 0.01),
                types=["restaurant"],
            ))
        plan = AIPlan(
            selected_place_ids=["place_0", "place_1", "dining_0", "place_2", "dining_1"],
            day_groups=[
                DayGroup(theme="Day 1", place_ids=["place_0", "place_1", "dining_0"]),
                DayGroup(theme="Day 2", place_ids=["place_2", "dining_1"]),
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
        assert len(result.selected_place_ids) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# CityHighlight excursion fields
# ═══════════════════════════════════════════════════════════════════════════════


class TestCityHighlightExcursion:
    def test_excursion_fields_default_none(self):
        from app.models.journey import CityHighlight
        h = CityHighlight(name="Test")
        assert h.excursion_type is None
        assert h.excursion_days is None
        assert h.destination_name is None

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

    def test_destination_name_set(self):
        from app.models.journey import CityHighlight
        h = CityHighlight(
            name="Forest shrines in mountain regions",
            category="excursion",
            destination_name="Nikko",
            excursion_type="full_day",
        )
        assert h.destination_name == "Nikko"


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


# ═══════════════════════════════════════════════════════════════════════════════
# destination_name propagation & LODGING_TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class TestDestinationNameField:
    """Verify destination_name on ExperienceTheme and CityHighlight."""

    def test_experience_theme_defaults_none(self):
        from app.models.journey import ExperienceTheme
        et = ExperienceTheme(theme="Temple circuit", category="religious")
        assert et.destination_name is None

    def test_experience_theme_set(self):
        from app.models.journey import ExperienceTheme
        et = ExperienceTheme(
            theme="Forest shrines in mountain regions",
            category="excursion",
            destination_name="Nikko",
            excursion_type="full_day",
            distance_from_city_km=130,
        )
        assert et.destination_name == "Nikko"

    def test_extract_excursions_preserves_destination_name(self):
        from app.models.journey import ExperienceTheme
        themes = [
            ExperienceTheme(
                theme="Limestone bay cruise",
                category="excursion",
                destination_name="Ha Long Bay",
                excursion_type="multi_day",
                excursion_days=2,
            ),
            ExperienceTheme(
                theme="Street food markets",
                category="food",
            ),
        ]
        result = DayPlanOrchestrator._extract_excursions(
            highlights=[], experience_themes=themes,
        )
        assert len(result) == 1
        assert result[0].destination_name == "Ha Long Bay"
        assert result[0].excursion_type == "multi_day"


class TestLodgingTypes:
    """Verify LODGING_TYPES exists and has expected members."""

    def test_lodging_types_exists(self):
        from app.config.planning import LODGING_TYPES
        assert isinstance(LODGING_TYPES, set)
        assert len(LODGING_TYPES) >= 5

    def test_lodging_types_contains_expected(self):
        from app.config.planning import LODGING_TYPES
        for expected in ("lodging", "hotel", "resort_hotel", "hostel", "bed_and_breakfast"):
            assert expected in LODGING_TYPES

    def test_lodging_types_no_overlap_with_dining(self):
        from app.config.planning import DINING_TYPES, LODGING_TYPES
        assert not (DINING_TYPES & LODGING_TYPES), "DINING_TYPES and LODGING_TYPES must not overlap"


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


class TestParallelLandmarkSearch:
    """Landmark text searches should run in parallel via asyncio.gather."""

    @pytest.mark.asyncio
    async def test_landmark_searches_deduplicate(self):
        """Parallel landmark searches should still deduplicate by place_id."""
        from app.orchestrators.day_plan import DayPlanOrchestrator

        mock_places = AsyncMock()
        mock_places.text_search_places = AsyncMock(side_effect=[
            [PlaceCandidate(place_id="p1", name="Temple A", address="Kyoto, Japan", location=Location(lat=35, lng=139), types=[])],
            [PlaceCandidate(place_id="p1", name="Temple A duplicate", address="Kyoto, Japan", location=Location(lat=35, lng=139), types=[])],
            [PlaceCandidate(place_id="p2", name="Shrine B", address="Kyoto, Japan", location=Location(lat=35.1, lng=139.1), types=[])],
        ])

        candidates = []
        existing_ids = set()
        city_landmarks = [{"name": "Temple A"}, {"name": "Temple A alt"}, {"name": "Shrine B"}]
        city_name = "Kyoto"
        location = Location(lat=35, lng=139)

        async def _search_landmark(lm_name: str):
            try:
                return await mock_places.text_search_places(
                    query=f"{lm_name} {city_name}",
                    location=location,
                    max_results=1,
                )
            except Exception:
                return []

        import asyncio
        lm_results_all = await asyncio.gather(
            *(_search_landmark(lm["name"]) for lm in city_landmarks)
        )
        for lm_results in lm_results_all:
            for lc in lm_results:
                if lc.place_id not in existing_ids:
                    candidates.append(lc)
                    existing_ids.add(lc.place_id)

        assert len(candidates) == 2
        assert {c.place_id for c in candidates} == {"p1", "p2"}


class TestParallelExcursionProcessing:
    """Excursion days should process in parallel via asyncio.gather."""

    @pytest.mark.asyncio
    async def test_excursion_grouping(self):
        """Independent excursions should be grouped correctly for parallel processing."""
        from app.models.journey import CityHighlight

        excursions_by_day = {
            0: CityHighlight(name="Nikko", excursion_type="full_day"),
            2: CityHighlight(name="Hakone", excursion_type="full_day"),
        }

        exc_groups = {}
        for day_idx, exc in sorted(excursions_by_day.items()):
            key = exc.name
            if key not in exc_groups:
                exc_groups[key] = (exc, [])
            exc_groups[key][1].append(day_idx)

        assert len(exc_groups) == 2
        assert exc_groups["Nikko"][1] == [0]
        assert exc_groups["Hakone"][1] == [2]

    @pytest.mark.asyncio
    async def test_multi_day_excursion_grouped_together(self):
        """Multi-day excursions sharing same object should form one group."""
        from app.models.journey import CityHighlight

        shared_exc = CityHighlight(name="Ha Long Bay", excursion_type="multi_day", excursion_days=2)
        excursions_by_day = {
            3: shared_exc,
            4: shared_exc,
        }

        exc_groups = {}
        for day_idx, exc in sorted(excursions_by_day.items()):
            key = exc.name
            if key not in exc_groups:
                exc_groups[key] = (exc, [])
            exc_groups[key][1].append(day_idx)

        assert len(exc_groups) == 1
        assert exc_groups["Ha Long Bay"][1] == [3, 4]


# ═══════════════════════════════════════════════════════════════════════════════
# City-level parallelism configuration and computation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCityParallelism:
    """City-level parallel processing via Queue + Semaphore."""

    @pytest.mark.asyncio
    async def test_day_offset_computed_from_city_index(self):
        """Each city computes its own day_offset without shared state."""
        journey = _make_journey_plan()
        # Rome = 3 days, Florence = 2 days
        # Rome day_offset = 0, Florence day_offset = 3
        day_offset_0 = sum(journey.cities[i].days for i in range(0))
        day_offset_1 = sum(journey.cities[i].days for i in range(1))
        assert day_offset_0 == 0
        assert day_offset_1 == 3

    @pytest.mark.asyncio
    async def test_max_concurrent_cities_config_exists(self):
        """MAX_CONCURRENT_CITIES should be importable from planning config."""
        from app.config.planning import MAX_CONCURRENT_CITIES
        assert isinstance(MAX_CONCURRENT_CITIES, int)
        assert MAX_CONCURRENT_CITIES > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Must-See Iconic Attractions
# ═══════════════════════════════════════════════════════════════════════════════

class TestMustSeeModels:
    """MustSeeAttraction / MustSeeAttractions model validation."""

    def test_must_see_model_valid(self):
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        result = MustSeeAttractions(attractions=[
            MustSeeAttraction(
                name="Colosseum",
                city_or_region="Rome",
                why_iconic="Ancient gladiatorial arena, symbol of the Roman Empire",
            ),
        ])
        assert len(result.attractions) == 1
        assert result.attractions[0].name == "Colosseum"

    def test_must_see_model_rejects_empty(self):
        from app.models.journey import MustSeeAttractions
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            MustSeeAttractions(attractions=[])

    def test_must_see_model_max_length(self):
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            MustSeeAttractions(attractions=[
                MustSeeAttraction(name=f"Place{i}", city_or_region="City", why_iconic="Reason")
                for i in range(8)
            ])


class TestMustSeeFormatting:
    """JourneyOrchestrator must-see context formatting."""

    def _make_orchestrator(self):
        from app.orchestrators.journey import JourneyOrchestrator
        from unittest.mock import MagicMock
        llm = MagicMock()
        places = MagicMock()
        routes = MagicMock()
        directions = MagicMock()
        return JourneyOrchestrator(llm, places, routes, directions)

    def test_format_must_see_context(self):
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        orch = self._make_orchestrator()
        result = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Eiffel Tower", city_or_region="Paris", why_iconic="Iconic iron lattice tower"),
            MustSeeAttraction(name="Louvre Museum", city_or_region="Paris", why_iconic="World's largest art museum"),
        ])
        context = orch._format_must_see_context(result, [])
        assert "Eiffel Tower" in context
        assert "Louvre Museum" in context
        assert "Must-See Iconic Attractions" in context

    def test_format_merges_user_must_include(self):
        from app.models.journey import MustSeeAttraction, MustSeeAttractions
        orch = self._make_orchestrator()
        result = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Eiffel Tower", city_or_region="Paris", why_iconic="Iconic tower"),
        ])
        context = orch._format_must_see_context(result, ["Mont Saint-Michel", "Eiffel Tower"])
        assert "Mont Saint-Michel" in context
        assert "highest priority" in context
        # Eiffel Tower should NOT appear twice (dedup)
        assert context.count("Eiffel Tower") == 1

    def test_format_user_must_include_only(self):
        context = TestMustSeeFormatting._make_orchestrator(self)._format_user_must_include_only(["Taj Mahal"])
        assert "Taj Mahal" in context
        assert "highest priority" in context


# ═══════════════════════════════════════════════════════════════════════════════
# Tiered Route Computation
# ═══════════════════════════════════════════════════════════════════════════════

class TestHaversineModeSelection:
    """Haversine-based transport mode selection for efficient/minimal tiers."""

    def test_short_distance_selects_walk(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        from app.models.common import Location, Pace
        # ~500m apart (well within walk threshold)
        origin = Location(lat=35.6762, lng=139.6503)
        destination = Location(lat=35.6795, lng=139.6503)
        mode = DayPlanOrchestrator._pick_mode_from_haversine(origin, destination, Pace.MODERATE)
        assert mode.value == "WALK"

    def test_long_distance_selects_drive(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        from app.models.common import Location, Pace
        # ~10km apart (far beyond walk threshold)
        origin = Location(lat=35.6762, lng=139.6503)
        destination = Location(lat=35.7620, lng=139.6503)
        mode = DayPlanOrchestrator._pick_mode_from_haversine(origin, destination, Pace.MODERATE)
        assert mode.value == "DRIVE"

    def test_relaxed_pace_walks_further(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        from app.models.common import Location, Pace
        # ~1.5km — walkable for relaxed, borderline for packed
        origin = Location(lat=35.6762, lng=139.6503)
        destination = Location(lat=35.6898, lng=139.6503)
        relaxed = DayPlanOrchestrator._pick_mode_from_haversine(origin, destination, Pace.RELAXED)
        packed = DayPlanOrchestrator._pick_mode_from_haversine(origin, destination, Pace.PACKED)
        assert relaxed.value == "WALK"
        assert packed.value == "DRIVE"

    def test_format_duration(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        assert DayPlanOrchestrator._format_duration(30) == "1 min"
        assert DayPlanOrchestrator._format_duration(600) == "10 min"
        assert DayPlanOrchestrator._format_duration(3600) == "1 hr"
        assert DayPlanOrchestrator._format_duration(5400) == "1 hr 30 min"

    def test_route_computation_mode_config(self):
        from app.config.planning import ROUTE_COMPUTATION_MODE
        assert isinstance(ROUTE_COMPUTATION_MODE, str)
        assert ROUTE_COMPUTATION_MODE in ("full", "efficient", "minimal")


class TestPlaceCandidateSourceDestination:
    def test_source_destination_default_none(self):
        from app.models.internal import PlaceCandidate
        from app.models.common import Location
        pc = PlaceCandidate(place_id="p1", name="Test", address="Addr", location=Location(lat=0, lng=0))
        assert pc.source_destination is None

    def test_source_destination_set(self):
        from app.models.internal import PlaceCandidate
        from app.models.common import Location
        pc = PlaceCandidate(
            place_id="p1", name="Toshogu Shrine", address="Nikko",
            location=Location(lat=36.7, lng=139.6),
            source_destination="Nikko",
        )
        assert pc.source_destination == "Nikko"


class TestGeographicContext:
    """Geographic context building for Scout anti-backtracking."""

    def _make_orchestrator(self):
        from app.orchestrators.journey import JourneyOrchestrator
        llm = MagicMock()
        places = MagicMock()
        routes = MagicMock()
        directions = MagicMock()
        return JourneyOrchestrator(llm, places, routes, directions)

    @pytest.mark.asyncio
    async def test_build_geographic_context_basic(self):
        """Geographic context should show distances and flow."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions

        orch = self._make_orchestrator()

        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Grand Palace", city_or_region="Bangkok", why_iconic="Royal palace"),
            MustSeeAttraction(name="Angkor Wat", city_or_region="Siem Reap", why_iconic="Temple complex"),
            MustSeeAttraction(name="Ha Long Bay", city_or_region="Hanoi", why_iconic="Limestone karsts"),
        ])

        async def mock_geocode(city):
            coords = {
                "Chiang Mai": {"lat": 18.79, "lng": 98.98, "name": "Chiang Mai"},
                "Bangkok": {"lat": 13.76, "lng": 100.50, "name": "Bangkok"},
                "Siem Reap": {"lat": 13.36, "lng": 103.86, "name": "Siem Reap"},
                "Hanoi": {"lat": 21.03, "lng": 105.85, "name": "Hanoi"},
            }
            if city in coords:
                return coords[city]
            raise ValueError(f"No geocode for {city}")

        orch.places.geocode = AsyncMock(side_effect=mock_geocode)

        context = await orch._build_geographic_context(must_see, "Chiang Mai")
        assert "GEOGRAPHIC CONTEXT" in context
        assert "Chiang Mai" in context
        assert "Bangkok" in context
        assert "km" in context
        assert "backtracking" in context.lower()

    @pytest.mark.asyncio
    async def test_geographic_context_empty_for_single_city(self):
        """Single-city destinations should return empty context."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions

        orch = self._make_orchestrator()

        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Marina Bay Sands", city_or_region="Singapore", why_iconic="Iconic hotel"),
            MustSeeAttraction(name="Gardens by the Bay", city_or_region="Singapore", why_iconic="Nature park"),
            MustSeeAttraction(name="Merlion", city_or_region="Singapore", why_iconic="Symbol"),
        ])

        # Only 1 unique city + origin (same city) = 1 unique. Needs >= 3.
        context = await orch._build_geographic_context(must_see, "Singapore")
        assert context == ""

    @pytest.mark.asyncio
    async def test_geographic_context_handles_geocode_failures(self):
        """Should gracefully degrade when geocode fails for all cities."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions

        orch = self._make_orchestrator()

        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Place A", city_or_region="CityA", why_iconic="Reason"),
            MustSeeAttraction(name="Place B", city_or_region="CityB", why_iconic="Reason"),
            MustSeeAttraction(name="Place C", city_or_region="CityC", why_iconic="Reason"),
        ])

        orch.places.geocode = AsyncMock(side_effect=ValueError("No results"))

        context = await orch._build_geographic_context(must_see, "Origin")
        assert context == ""

    @pytest.mark.asyncio
    async def test_geographic_context_deduplicates_cities(self):
        """Multiple attractions in same city should only geocode once."""
        from app.models.journey import MustSeeAttraction, MustSeeAttractions

        orch = self._make_orchestrator()

        must_see = MustSeeAttractions(attractions=[
            MustSeeAttraction(name="Grand Palace", city_or_region="Bangkok", why_iconic="Royal palace"),
            MustSeeAttraction(name="Wat Pho", city_or_region="Bangkok", why_iconic="Reclining Buddha"),
            MustSeeAttraction(name="Angkor Wat", city_or_region="Siem Reap", why_iconic="Temple complex"),
            MustSeeAttraction(name="Ha Long Bay", city_or_region="Hanoi", why_iconic="Limestone karsts"),
        ])

        call_count = 0

        async def mock_geocode(city):
            nonlocal call_count
            call_count += 1
            coords = {
                "Tokyo": {"lat": 35.68, "lng": 139.69, "name": "Tokyo"},
                "Bangkok": {"lat": 13.76, "lng": 100.50, "name": "Bangkok"},
                "Siem Reap": {"lat": 13.36, "lng": 103.86, "name": "Siem Reap"},
                "Hanoi": {"lat": 21.03, "lng": 105.85, "name": "Hanoi"},
            }
            return coords[city]

        orch.places.geocode = AsyncMock(side_effect=mock_geocode)

        context = await orch._build_geographic_context(must_see, "Tokyo")
        # Tokyo + Bangkok (deduped) + Siem Reap + Hanoi = 4 geocode calls, NOT 5
        assert call_count == 4
        assert "GEOGRAPHIC CONTEXT" in context


# ═══════════════════════════════════════════════════════════════════════════════
# Web Search Grounding base class defaults
# ═══════════════════════════════════════════════════════════════════════════════


class TestSearchGrounding:
    """Tests for web search grounding base class defaults."""

    @pytest.mark.asyncio
    async def test_generate_with_search_default_fallback(self):
        """Default implementation falls back to generate() with empty citations."""
        from tests.conftest import MockLLMService
        llm = MockLLMService()
        text, citations = await llm.generate_with_search(
            system_prompt="test", user_prompt="test"
        )
        assert isinstance(text, str)
        assert citations == []

    @pytest.mark.asyncio
    async def test_generate_structured_with_search_default_fallback(self):
        """Default implementation falls back to generate_structured() with empty citations."""
        from pydantic import BaseModel
        from tests.conftest import MockLLMService

        class SimpleSchema(BaseModel):
            message: str = "default"

        llm = MockLLMService()
        result, citations = await llm.generate_structured_with_search(
            system_prompt="test", user_prompt="test", schema=SimpleSchema
        )
        assert isinstance(result, SimpleSchema)
        assert citations == []

    def test_search_citation_model(self):
        """SearchCitation model validates correctly."""
        from app.services.llm.base import SearchCitation
        citation = SearchCitation(url="https://example.com", title="Example", cited_text="some text")
        assert citation.url == "https://example.com"
        assert citation.title == "Example"
        assert citation.cited_text == "some text"

    def test_search_citation_minimal(self):
        """SearchCitation works with just url and title."""
        from app.services.llm.base import SearchCitation
        citation = SearchCitation(url="https://example.com", title="Example")
        assert citation.cited_text == ""

    def test_should_use_search_grounding_full(self):
        """Full mode enables all tiers."""
        from app.config.planning import should_use_search_grounding
        import app.config.planning as planning
        original = planning.SEARCH_GROUNDING_MODE
        try:
            planning.SEARCH_GROUNDING_MODE = "full"
            assert should_use_search_grounding("selective") is True
            assert should_use_search_grounding("full") is True
        finally:
            planning.SEARCH_GROUNDING_MODE = original

    def test_should_use_search_grounding_selective(self):
        """Selective mode only enables selective tier."""
        from app.config.planning import should_use_search_grounding
        import app.config.planning as planning
        original = planning.SEARCH_GROUNDING_MODE
        try:
            planning.SEARCH_GROUNDING_MODE = "selective"
            assert should_use_search_grounding("selective") is True
            assert should_use_search_grounding("full") is False
        finally:
            planning.SEARCH_GROUNDING_MODE = original

    def test_should_use_search_grounding_none(self):
        """None mode disables all tiers."""
        from app.config.planning import should_use_search_grounding
        import app.config.planning as planning
        original = planning.SEARCH_GROUNDING_MODE
        try:
            planning.SEARCH_GROUNDING_MODE = "none"
            assert should_use_search_grounding("selective") is False
            assert should_use_search_grounding("full") is False
        finally:
            planning.SEARCH_GROUNDING_MODE = original


# ═══════════════════════════════════════════════════════════════════════════════
# Gemini Search Grounding
# ═══════════════════════════════════════════════════════════════════════════════


class TestGeminiSearchGrounding:
    """Tests for Gemini web search grounding implementation."""

    @pytest.mark.asyncio
    async def test_generate_with_search_extracts_citations(self):
        """Gemini search grounding extracts citations from grounding metadata."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.gemini import GeminiLLMService
        from app.services.llm.base import SearchCitation

        service = GeminiLLMService.__new__(GeminiLLMService)
        service.model = "gemini-2.5-flash"
        service.client = MagicMock()

        mock_chunk = MagicMock()
        mock_chunk.web.uri = "https://example.com/hotels"
        mock_chunk.web.title = "Tokyo Hotels Guide"

        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata.grounding_chunks = [mock_chunk]

        mock_response = MagicMock()
        mock_response.text = "Hotel recommendations..."
        mock_response.candidates = [mock_candidate]

        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        text, citations = await service.generate_with_search(
            system_prompt="You are a travel expert.",
            user_prompt="Best hotels in Tokyo?",
        )

        assert text == "Hotel recommendations..."
        assert len(citations) == 1
        assert citations[0].url == "https://example.com/hotels"
        assert citations[0].title == "Tokyo Hotels Guide"

    @pytest.mark.asyncio
    async def test_generate_with_search_no_grounding_metadata(self):
        """Returns empty citations when no grounding metadata present."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.gemini import GeminiLLMService

        service = GeminiLLMService.__new__(GeminiLLMService)
        service.model = "gemini-2.5-flash"
        service.client = MagicMock()

        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = None

        mock_response = MagicMock()
        mock_response.text = "Some response"
        mock_response.candidates = [mock_candidate]

        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="test",
        )

        assert text == "Some response"
        assert citations == []

    @pytest.mark.asyncio
    async def test_generate_with_search_fallback_on_error(self):
        """Falls back to regular generate on search error."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.llm.gemini import GeminiLLMService

        service = GeminiLLMService.__new__(GeminiLLMService)
        service.model = "gemini-2.5-flash"
        service.client = MagicMock()

        call_count = 0
        async def mock_generate_content(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Search tool not available")
            mock_resp = MagicMock()
            mock_resp.text = "Fallback response"
            return mock_resp

        service.client.aio.models.generate_content = mock_generate_content

        text, citations = await service.generate_with_search(
            system_prompt="test", user_prompt="test",
        )

        assert text == "Fallback response"
        assert citations == []
