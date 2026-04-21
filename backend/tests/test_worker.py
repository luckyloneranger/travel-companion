"""Tests for the job queue worker."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.worker.runner import Worker
from app.pipelines.batch import BatchResult
from app.pipelines.draft import DraftResult


def _make_job(job_type="batch_generate", city_id=None):
    job = MagicMock()
    job.id = uuid.uuid4()
    job.job_type = job_type
    job.city_id = city_id or uuid.uuid4()
    job.parameters = {
        "city_name": "Tokyo", "country": "Japan",
        "pace": "moderate", "budget": "moderate", "day_count": 3,
    }
    return job


@pytest.mark.asyncio
async def test_worker_picks_and_executes():
    """Worker picks a job and calls batch pipeline."""
    job = _make_job()

    job_repo = AsyncMock()
    job_repo.pick_next = AsyncMock(return_value=job)
    job_repo.complete = AsyncMock()
    job_repo.update_progress = AsyncMock()

    batch = AsyncMock()
    batch.generate = AsyncMock(return_value=BatchResult(
        variant_id=uuid.uuid4(), status="published", quality_score=85, iterations_used=2,
    ))

    draft = AsyncMock()

    worker = Worker(job_repo=job_repo, batch_pipeline=batch, draft_pipeline=draft)
    processed = await worker.process_one()

    assert processed is True
    batch.generate.assert_awaited_once()
    job_repo.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_handles_failure():
    """Worker marks job as failed when pipeline raises."""
    job = _make_job()

    job_repo = AsyncMock()
    job_repo.pick_next = AsyncMock(return_value=job)
    job_repo.fail = AsyncMock()
    job_repo.update_progress = AsyncMock()

    batch = AsyncMock()
    batch.generate = AsyncMock(side_effect=RuntimeError("LLM timeout"))

    draft = AsyncMock()

    worker = Worker(job_repo=job_repo, batch_pipeline=batch, draft_pipeline=draft)
    processed = await worker.process_one()

    assert processed is True
    job_repo.fail.assert_awaited_once()
    assert "LLM timeout" in job_repo.fail.call_args.args[1]


@pytest.mark.asyncio
async def test_worker_returns_false_when_no_jobs():
    """Worker returns False when queue is empty."""
    job_repo = AsyncMock()
    job_repo.pick_next = AsyncMock(return_value=None)

    worker = Worker(
        job_repo=job_repo,
        batch_pipeline=AsyncMock(),
        draft_pipeline=AsyncMock(),
    )
    processed = await worker.process_one()

    assert processed is False


@pytest.mark.asyncio
async def test_worker_dispatches_on_demand_to_draft():
    """Worker dispatches on_demand jobs to draft pipeline."""
    job = _make_job(job_type="on_demand")

    job_repo = AsyncMock()
    job_repo.pick_next = AsyncMock(return_value=job)
    job_repo.complete = AsyncMock()

    batch = AsyncMock()
    draft = AsyncMock()
    draft.generate = AsyncMock(return_value=DraftResult(
        variant_id=uuid.uuid4(), status="draft", upgrade_job_id=uuid.uuid4(),
    ))

    worker = Worker(job_repo=job_repo, batch_pipeline=batch, draft_pipeline=draft)
    processed = await worker.process_one()

    assert processed is True
    draft.generate.assert_awaited_once()
    batch.generate.assert_not_awaited()
    job_repo.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_unknown_job_type():
    """Worker fails unknown job types gracefully."""
    job = _make_job(job_type="unknown_type")

    job_repo = AsyncMock()
    job_repo.pick_next = AsyncMock(return_value=job)
    job_repo.fail = AsyncMock()

    worker = Worker(
        job_repo=job_repo,
        batch_pipeline=AsyncMock(),
        draft_pipeline=AsyncMock(),
    )
    processed = await worker.process_one()

    assert processed is True
    job_repo.fail.assert_awaited_once()
    assert "Unknown job type" in job_repo.fail.call_args.args[1]
