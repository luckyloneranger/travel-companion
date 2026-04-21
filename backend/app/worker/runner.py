"""Job queue worker — polls for jobs and dispatches to pipelines."""

import asyncio
import logging

from app.db.repository import JobRepository
from app.pipelines.batch import BatchPipeline
from app.pipelines.draft import DraftPipeline
from app.config.planning import JOB_POLL_INTERVAL_SECONDS, JOB_STALE_TIMEOUT_MINUTES

logger = logging.getLogger(__name__)


class Worker:
    """Polls the job queue and dispatches to batch/draft pipelines."""

    def __init__(
        self,
        job_repo: JobRepository,
        batch_pipeline: BatchPipeline,
        draft_pipeline: DraftPipeline,
        worker_id: str = "worker-1",
    ):
        self.job_repo = job_repo
        self.batch = batch_pipeline
        self.draft = draft_pipeline
        self.worker_id = worker_id

    async def process_one(self) -> bool:
        """Pick and process one job. Returns True if a job was processed."""
        job = await self.job_repo.pick_next(self.worker_id)
        if not job:
            return False

        logger.info("Processing job %s (type=%s)", job.id, job.job_type)
        try:
            if job.job_type in ("batch_generate", "upgrade_draft"):
                params = job.parameters or {}
                result = await self.batch.generate(
                    city_id=job.city_id,
                    city_name=params.get("city_name", ""),
                    country=params.get("country", ""),
                    pace=params.get("pace", "moderate"),
                    budget=params.get("budget", "moderate"),
                    day_count=params.get("day_count", 3),
                    on_progress=lambda pct: self.job_repo.update_progress(job.id, pct),
                )
                await self.job_repo.complete(
                    job.id,
                    {"variant_id": str(result.variant_id), "status": result.status},
                )

            elif job.job_type == "on_demand":
                params = job.parameters or {}
                result = await self.draft.generate(
                    city_id=job.city_id,
                    city_name=params.get("city_name", ""),
                    country=params.get("country", ""),
                    pace=params.get("pace", "moderate"),
                    budget=params.get("budget", "moderate"),
                    day_count=params.get("day_count", 3),
                )
                await self.job_repo.complete(
                    job.id, {"variant_id": str(result.variant_id)}
                )

            else:
                logger.warning("Unknown job type: %s", job.job_type)
                await self.job_repo.fail(job.id, f"Unknown job type: {job.job_type}")

        except Exception as e:
            logger.error("Job %s failed: %s", job.id, e)
            await self.job_repo.fail(job.id, str(e))

        return True

    async def run_loop(self) -> None:
        """Main worker loop — poll for jobs, process, repeat."""
        logger.info("Worker %s starting...", self.worker_id)
        # Recover stale jobs on startup
        recovered = await self.job_repo.recover_stale(JOB_STALE_TIMEOUT_MINUTES)
        if recovered:
            logger.info("Recovered %d stale jobs", recovered)

        while True:
            try:
                processed = await self.process_one()
                if not processed:
                    await asyncio.sleep(JOB_POLL_INTERVAL_SECONDS)
            except Exception as e:
                logger.error("Worker error: %s", e)
                await asyncio.sleep(JOB_POLL_INTERVAL_SECONDS)
