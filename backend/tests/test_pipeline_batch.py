"""Tests for batch pipeline and draft pipeline orchestration."""

import uuid
from dataclasses import dataclass
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipelines.batch import BatchPipeline, BatchResult
from app.pipelines.draft import DraftPipeline, DraftResult


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_discovery_result():
    """Build a minimal DiscoveryResult-like object."""
    @dataclass
    class FakeDiscovery:
        city_metadata: dict
        candidates: list
        lodging_candidates: list
        data_hash: str

    return FakeDiscovery(
        city_metadata={"name": "Tokyo", "country": "Japan", "lat": 35.68, "lng": 139.76},
        candidates=[
            {"place_id": "gp1", "name": "Senso-ji", "location": {"lat": 35.7, "lng": 139.8},
             "types": ["temple"], "rating": 4.5, "user_rating_count": 1000},
        ],
        lodging_candidates=[
            {"place_id": "gp_hotel", "name": "Hotel Tokyo", "location": {"lat": 35.69, "lng": 139.77},
             "types": ["hotel"], "rating": 4.2, "user_rating_count": 500, "is_lodging": True},
        ],
        data_hash="abc123",
    )


def _make_curation_result():
    """Build a minimal CurationOutput-like object."""
    act = MagicMock(
        google_place_id="gp1", category="cultural", description="Visit temple",
        duration_minutes=60, is_meal=False, meal_type=None, estimated_cost_usd=0,
    )
    day = MagicMock(day_number=1, theme="Temples", theme_description="Temple tour", activities=[act])
    accom = MagicMock(google_place_id="gp_hotel", estimated_nightly_usd=120)
    return MagicMock(days=[day], accommodation=accom, accommodation_alternatives=[], booking_hint="Book early")


def _make_routing_result():
    """Build a minimal DayRoutingResult-like object."""
    return MagicMock(
        ordered_activities=[
            {"google_place_id": "gp1", "location": {"lat": 35.7, "lng": 139.8},
             "name": "Senso-ji", "category": "cultural", "sequence": 1,
             "duration_minutes": 60, "is_meal": False},
        ],
        routes=[],
    )


def _make_scheduled():
    """Build a minimal list of ScheduledActivity-like objects."""
    return [MagicMock(
        sequence=1, start_time=time(9, 0), end_time=time(10, 0),
        duration_minutes=60,
        data={"google_place_id": "gp1", "category": "cultural",
              "description": "Visit temple", "is_meal": False,
              "meal_type": None, "estimated_cost_usd": 0},
    )]


def _make_review_fix_result(score=85):
    """Build a ReviewFixResult-like object."""
    return MagicMock(best_plan={}, best_score=score, iterations_used=1, final_issues=[])


def _make_cost_breakdown():
    """Build a CostBreakdown-like object."""
    return MagicMock(
        accommodation=360, transport=20, dining=90, activities=30, total=500, per_day=[166.67],
    )


def _make_place():
    """Build a fake Place ORM object."""
    place = MagicMock()
    place.id = uuid.uuid4()
    return place


def _make_variant():
    """Build a fake PlanVariant ORM object."""
    variant = MagicMock()
    variant.id = uuid.uuid4()
    return variant


def _make_job():
    """Build a fake GenerationJob ORM object."""
    job = MagicMock()
    job.id = uuid.uuid4()
    return job


def _build_batch_pipeline():
    """Create a BatchPipeline with all mocked dependencies."""
    discovery = AsyncMock()
    discovery.discover = AsyncMock(return_value=_make_discovery_result())

    curation = AsyncMock()
    curation.curate = AsyncMock(return_value=_make_curation_result())

    routing = AsyncMock()
    routing.route_day = AsyncMock(return_value=_make_routing_result())

    scheduling = MagicMock()
    scheduling.schedule_day = MagicMock(return_value=_make_scheduled())

    review = AsyncMock()
    review.review_and_fix = AsyncMock(return_value=_make_review_fix_result(85))

    costing = MagicMock()
    costing.compute = MagicMock(return_value=_make_cost_breakdown())

    place_repo = AsyncMock()
    place_repo.upsert_from_google = AsyncMock(side_effect=lambda **kw: _make_place())

    variant_repo = AsyncMock()
    variant_repo.create = AsyncMock(return_value=_make_variant())

    day_plan_repo = AsyncMock()
    day_plan_repo.create_with_activities = AsyncMock()

    return BatchPipeline(
        discovery=discovery,
        curation=curation,
        routing=routing,
        scheduling=scheduling,
        review=review,
        costing=costing,
        place_repo=place_repo,
        variant_repo=variant_repo,
        day_plan_repo=day_plan_repo,
    )


def _build_draft_pipeline():
    """Create a DraftPipeline with all mocked dependencies."""
    discovery = AsyncMock()
    discovery.discover = AsyncMock(return_value=_make_discovery_result())

    curation = AsyncMock()
    curation.curate = AsyncMock(return_value=_make_curation_result())

    routing = AsyncMock()
    routing.route_day = AsyncMock(return_value=_make_routing_result())

    scheduling = MagicMock()
    scheduling.schedule_day = MagicMock(return_value=_make_scheduled())

    costing = MagicMock()
    costing.compute = MagicMock(return_value=_make_cost_breakdown())

    place_repo = AsyncMock()
    place_repo.upsert_from_google = AsyncMock(side_effect=lambda **kw: _make_place())

    variant_repo = AsyncMock()
    variant_repo.create = AsyncMock(return_value=_make_variant())

    day_plan_repo = AsyncMock()
    day_plan_repo.create_with_activities = AsyncMock()

    job_repo = AsyncMock()
    job_repo.create = AsyncMock(return_value=_make_job())

    return DraftPipeline(
        discovery=discovery,
        curation=curation,
        routing=routing,
        scheduling=scheduling,
        costing=costing,
        place_repo=place_repo,
        variant_repo=variant_repo,
        day_plan_repo=day_plan_repo,
        job_repo=job_repo,
    )


# ---------------------------------------------------------------------------
# Batch pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_pipeline_calls_all_steps():
    """All 6 pipeline steps are called in order."""
    pipeline = _build_batch_pipeline()
    city_id = uuid.uuid4()

    result = await pipeline.generate(
        city_id=city_id, city_name="Tokyo", country="Japan",
        pace="moderate", budget="moderate", day_count=3,
    )

    assert isinstance(result, BatchResult)
    assert result.status == "published"
    assert result.quality_score == 85
    assert result.variant_id is not None

    # Verify all steps called
    pipeline.discovery.discover.assert_awaited_once()
    pipeline.curation.curate.assert_awaited_once()
    pipeline.routing.route_day.assert_awaited()
    pipeline.scheduling.schedule_day.assert_called()
    pipeline.review.review_and_fix.assert_awaited_once()
    pipeline.costing.compute.assert_called_once()
    pipeline.variant_repo.create.assert_awaited_once()
    pipeline.day_plan_repo.create_with_activities.assert_awaited()


@pytest.mark.asyncio
async def test_batch_pipeline_draft_status_on_low_score():
    """Variant gets draft status when score < BATCH_MIN_SCORE."""
    pipeline = _build_batch_pipeline()
    pipeline.review.review_and_fix = AsyncMock(return_value=_make_review_fix_result(60))

    result = await pipeline.generate(
        city_id=uuid.uuid4(), city_name="Tokyo", country="Japan",
        pace="moderate", budget="moderate", day_count=3,
    )

    assert result.status == "draft"
    assert result.quality_score == 60


@pytest.mark.asyncio
async def test_batch_pipeline_progress_callback():
    """Progress callback is called with increasing percentages."""
    pipeline = _build_batch_pipeline()
    progress_values = []

    async def track_progress(pct: int):
        progress_values.append(pct)

    await pipeline.generate(
        city_id=uuid.uuid4(), city_name="Tokyo", country="Japan",
        pace="moderate", budget="moderate", day_count=3,
        on_progress=track_progress,
    )

    assert progress_values == [5, 15, 25, 40, 55, 80, 90, 100]


# ---------------------------------------------------------------------------
# Draft pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_pipeline_no_review():
    """Draft pipeline skips review/fix loop."""
    pipeline = _build_draft_pipeline()

    result = await pipeline.generate(
        city_id=uuid.uuid4(), city_name="Tokyo", country="Japan",
        pace="moderate", budget="moderate", day_count=3,
    )

    assert isinstance(result, DraftResult)
    assert result.status == "draft"
    assert result.variant_id is not None
    assert result.upgrade_job_id is not None

    # Discovery called with reduced candidates
    pipeline.discovery.discover.assert_awaited_once()

    # Upgrade job queued
    pipeline.job_repo.create.assert_awaited_once()
    call_kwargs = pipeline.job_repo.create.call_args.kwargs
    assert call_kwargs["job_type"] == "upgrade_draft"
