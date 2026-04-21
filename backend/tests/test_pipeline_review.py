"""Tests for the review pipeline."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipelines.review import (
    LLMReviewResponse,
    ReviewFixResult,
    ReviewPipeline,
    ReviewResult,
)


def _make_mock_llm(review_responses: list[LLMReviewResponse], fix_response: str = "{}"):
    """Create a mock LLM service with predefined responses."""
    llm = AsyncMock()
    llm.generate_structured = AsyncMock(side_effect=review_responses)
    llm.generate = AsyncMock(return_value=fix_response)
    return llm


def _sample_plan():
    return {
        "days": [
            {
                "day_number": 1,
                "theme": "Historic Tokyo",
                "activities": [
                    {"name": "Senso-ji", "google_place_id": "gp_1"},
                    {"name": "Meiji Shrine", "google_place_id": "gp_2"},
                ],
            }
        ]
    }


@pytest.mark.asyncio
async def test_review_returns_score():
    """Mock LLM returns structured score, verify ReviewResult fields."""
    mock_response = LLMReviewResponse(
        overall_score=72,
        is_acceptable=False,
        issues=["Missing lunch slot on day 1", "No landmark coverage"],
        dimension_scores={"theme_coherence": 80, "landmark_coverage": 60},
    )
    llm = _make_mock_llm([mock_response])
    pipeline = ReviewPipeline(llm)

    result = await pipeline.review(_sample_plan(), "Tokyo", "moderate", 1)

    assert isinstance(result, ReviewResult)
    assert result.score == 72
    assert result.is_acceptable is False
    assert len(result.issues) == 2
    assert "theme_coherence" in result.dimension_scores
    llm.generate_structured.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_and_fix_loop_accepts_on_high_score():
    """Verify loop stops early when score meets threshold."""
    responses = [
        LLMReviewResponse(overall_score=65, is_acceptable=False, issues=["Pacing too tight"]),
        LLMReviewResponse(overall_score=85, is_acceptable=True, issues=[]),
    ]
    fixed_plan = json.dumps(_sample_plan())
    llm = _make_mock_llm(responses, fix_response=fixed_plan)
    pipeline = ReviewPipeline(llm)

    result = await pipeline.review_and_fix(
        plan=_sample_plan(),
        city_name="Tokyo",
        pace="moderate",
        day_count=1,
        candidates=[{"google_place_id": "gp_3", "name": "Tokyo Tower"}],
        max_iterations=5,
        min_score=80,
    )

    assert isinstance(result, ReviewFixResult)
    assert result.best_score == 85
    assert result.iterations_used == 2
    assert result.final_issues == []
    # 1 fix call between iteration 1 and 2
    assert llm.generate.await_count == 1


@pytest.mark.asyncio
async def test_review_and_fix_loop_exhausts_iterations():
    """Verify loop returns best plan when max iterations reached."""
    responses = [
        LLMReviewResponse(overall_score=50, is_acceptable=False, issues=["issue A"]),
        LLMReviewResponse(overall_score=70, is_acceptable=False, issues=["issue B"]),
        LLMReviewResponse(overall_score=60, is_acceptable=False, issues=["issue C"]),
    ]
    fixed_plan = json.dumps(_sample_plan())
    llm = _make_mock_llm(responses, fix_response=fixed_plan)
    pipeline = ReviewPipeline(llm)

    result = await pipeline.review_and_fix(
        plan=_sample_plan(),
        city_name="Tokyo",
        pace="relaxed",
        day_count=1,
        candidates=[],
        max_iterations=3,
        min_score=80,
    )

    assert result.best_score == 70
    assert result.iterations_used == 3
    assert result.final_issues == ["issue C"]
    # 2 fix calls (after iter 1 and iter 2, not after iter 3)
    assert llm.generate.await_count == 2


@pytest.mark.asyncio
async def test_collect_used_ids():
    """Verify _collect_used_ids extracts place IDs from plan."""
    llm = AsyncMock()
    pipeline = ReviewPipeline(llm)

    plan = _sample_plan()
    used = pipeline._collect_used_ids(plan)
    assert used == {"gp_1", "gp_2"}

    # Also handles nested place dict
    plan2 = {
        "days": [
            {"activities": [{"place": {"google_place_id": "gp_x"}}]}
        ]
    }
    assert pipeline._collect_used_ids(plan2) == {"gp_x"}
