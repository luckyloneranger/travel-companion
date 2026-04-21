"""Smart refresh pipeline — detects changes in Google Places data."""

import logging
from uuid import UUID
from app.pipelines.discovery import DiscoveryPipeline
from app.db.repository import CityRepository, PlaceRepository, VariantRepository, JobRepository
from app.config.planning import REFRESH_CANDIDATE_TURNOVER_THRESHOLD

logger = logging.getLogger(__name__)


class RefreshResult:
    def __init__(self, city_id: UUID, changed: bool, jobs_queued: int, details: str = ""):
        self.city_id = city_id
        self.changed = changed
        self.jobs_queued = jobs_queued
        self.details = details


class RefreshPipeline:
    def __init__(
        self,
        discovery: DiscoveryPipeline,
        city_repo: CityRepository,
        place_repo: PlaceRepository,
        variant_repo: VariantRepository,
        job_repo: JobRepository,
    ):
        self.discovery = discovery
        self.city_repo = city_repo
        self.place_repo = place_repo
        self.variant_repo = variant_repo
        self.job_repo = job_repo

    async def check_city(self, city_id: UUID) -> RefreshResult:
        """Check a city for changes and queue regeneration if needed."""
        city = await self.city_repo.get(city_id)
        if not city:
            return RefreshResult(city_id, False, 0, "City not found")

        # Re-run discovery
        result = await self.discovery.discover(city.name)
        new_hash = result.data_hash

        if new_hash == city.data_hash:
            return RefreshResult(city_id, False, 0, "No changes detected")

        # Compute turnover
        existing_places = await self.place_repo.get_by_city(city_id)
        existing_ids = {p.google_place_id for p in existing_places}
        new_ids = {
            c.get("google_place_id") or c.get("place_id")
            for c in result.candidates + result.lodging_candidates
        }

        added = new_ids - existing_ids
        removed = existing_ids - new_ids
        turnover = (len(added) + len(removed)) / max(len(existing_ids), 1)

        if turnover >= REFRESH_CANDIDATE_TURNOVER_THRESHOLD:
            # Major change — queue regeneration for all variants
            variants = await self.variant_repo.list_by_city(city_id)
            jobs_queued = 0
            for v in variants:
                if v.status in ("published", "draft"):
                    await self.variant_repo.update_status(v.id, "stale")
                    await self.job_repo.create(
                        job_type="batch_generate",
                        city_id=city_id,
                        parameters={
                            "city_name": city.name,
                            "country": city.country,
                            "pace": v.pace,
                            "budget": v.budget,
                            "day_count": v.day_count,
                        },
                        priority=3,
                    )
                    jobs_queued += 1

            # Update city hash
            await self.city_repo.update(city_id, data_hash=new_hash)
            return RefreshResult(
                city_id, True, jobs_queued,
                f"Major change: {turnover:.0%} turnover, {jobs_queued} jobs queued",
            )
        else:
            # Minor change — update places in-place, no variant regeneration
            await self.city_repo.update(city_id, data_hash=new_hash)
            return RefreshResult(
                city_id, True, 0,
                f"Minor change: {turnover:.0%} turnover, places updated",
            )

    async def refresh_all(self) -> list[RefreshResult]:
        """Refresh all cities."""
        cities, _ = await self.city_repo.list(limit=1000)
        results = []
        for city in cities:
            try:
                result = await self.check_city(city.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Refresh failed for {city.name}: {e}")
                results.append(RefreshResult(city.id, False, 0, f"Error: {e}"))
        return results
