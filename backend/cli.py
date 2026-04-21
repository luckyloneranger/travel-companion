"""CLI entrypoint for admin operations and worker."""

import asyncio
import click
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Travel Companion content platform CLI."""
    pass


@cli.command()
@click.option("--city", required=True, help="City name")
@click.option("--country", default="", help="Country name")
@click.option("--pace", default="moderate", type=click.Choice(["relaxed", "moderate", "packed"]))
@click.option("--budget", default="moderate", type=click.Choice(["budget", "moderate", "luxury"]))
@click.option("--days", default=3, type=int, help="Number of days")
def generate(city: str, country: str, pace: str, budget: str, days: int) -> None:
    """Queue a batch generation job for a city."""
    asyncio.run(_queue_generate(city, country, pace, budget, days))


@cli.command()
@click.option("--worker-id", default="worker-1", help="Worker identifier")
def worker(worker_id: str) -> None:
    """Start the job queue worker."""
    asyncio.run(_run_worker(worker_id))


async def _queue_generate(
    city_name: str, country: str, pace: str, budget: str, days: int
) -> None:
    from app.config.settings import get_settings
    from app.db.engine import get_session_factory

    settings = get_settings()
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        from app.db.repository import JobRepository

        job_repo = JobRepository(session)
        job = await job_repo.create(
            job_type="batch_generate",
            parameters={
                "city_name": city_name,
                "country": country,
                "pace": pace,
                "budget": budget,
                "day_count": days,
            },
            priority=5,
        )
        logger.info("Queued job %s for %s (%s/%s/%dd)", job.id, city_name, pace, budget, days)


async def _run_worker(worker_id: str) -> None:
    import sys
    from app.config.settings import get_settings
    from app.db.engine import get_session_factory
    from app.db.repository import (
        JobRepository, PlaceRepository, VariantRepository, DayPlanRepository,
    )
    from app.core.http import get_http_client
    from app.services.google.places import GooglePlacesService
    from app.services.google.routes import GoogleRoutesService
    from app.services.llm.factory import create_llm_service
    from app.pipelines.discovery import DiscoveryPipeline
    from app.pipelines.curation import CurationPipeline
    from app.pipelines.routing import RoutingPipeline
    from app.pipelines.scheduling import SchedulingPipeline
    from app.pipelines.review import ReviewPipeline
    from app.pipelines.costing import CostingPipeline
    from app.pipelines.batch import BatchPipeline
    from app.pipelines.draft import DraftPipeline
    from app.config.planning import JOB_POLL_INTERVAL_SECONDS, JOB_STALE_TIMEOUT_MINUTES

    settings = get_settings()
    http_client = await get_http_client()
    session_factory = get_session_factory(settings)

    # Build services (stateless, shared across jobs)
    places_service = GooglePlacesService(settings.google_places_api_key, http_client)
    routes_service = GoogleRoutesService(settings.google_routes_api_key, http_client)
    llm_service = create_llm_service(settings)

    discovery = DiscoveryPipeline(places_service)
    curation = CurationPipeline(llm_service)
    routing = RoutingPipeline(routes_service)
    scheduling = SchedulingPipeline()
    review = ReviewPipeline(llm_service)
    costing = CostingPipeline()

    logger.info("Worker %s starting with %s LLM provider", worker_id, settings.llm_provider)

    # Recover stale jobs on startup
    async with session_factory() as session:
        job_repo = JobRepository(session)
        recovered = await job_repo.recover_stale(JOB_STALE_TIMEOUT_MINUTES)
        if recovered:
            logger.info("Recovered %d stale jobs", recovered)

    # Main loop: fresh session per job
    while True:
        try:
            async with session_factory() as session:
                job_repo = JobRepository(session)
                job = await job_repo.pick_next(worker_id)

                if not job:
                    await asyncio.sleep(JOB_POLL_INTERVAL_SECONDS)
                    continue

                logger.info("Processing job %s (type=%s, city=%s)", job.id, job.job_type, (job.parameters or {}).get("city_name", "?"))

                # Fresh repos per job (same session)
                place_repo = PlaceRepository(session)
                variant_repo = VariantRepository(session)
                day_plan_repo = DayPlanRepository(session)

                batch = BatchPipeline(
                    discovery=discovery, curation=curation, routing=routing,
                    scheduling=scheduling, review=review, costing=costing,
                    place_repo=place_repo, variant_repo=variant_repo,
                    day_plan_repo=day_plan_repo,
                )

                try:
                    if job.job_type in ("batch_generate", "upgrade_draft"):
                        params = job.parameters or {}
                        result = await batch.generate(
                            city_id=job.city_id,
                            city_name=params.get("city_name", ""),
                            country=params.get("country", ""),
                            pace=params.get("pace", "moderate"),
                            budget=params.get("budget", "moderate"),
                            day_count=params.get("day_count", 3),
                            on_progress=lambda pct: job_repo.update_progress(job.id, pct),
                        )
                        await job_repo.complete(job.id, {"variant_id": str(result.variant_id), "status": result.status})
                        logger.info("Job %s completed: %s (score=%s)", job.id, result.status, result.quality_score)
                    else:
                        await job_repo.fail(job.id, f"Unknown job type: {job.job_type}")
                except Exception as e:
                    logger.error("Job %s failed: %s", job.id, e)
                    try:
                        await session.rollback()
                        await job_repo.fail(job.id, str(e)[:500])
                    except Exception:
                        logger.error("Failed to mark job as failed, will be recovered as stale")

        except Exception as e:
            logger.error("Worker loop error: %s", e)
            await asyncio.sleep(JOB_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    cli()
