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
    logger.info("Worker %s would start here — full wiring needed", worker_id)


if __name__ == "__main__":
    cli()
