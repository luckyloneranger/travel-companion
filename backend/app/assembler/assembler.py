"""Journey assembler — stitches city plans into multi-city journeys."""

import asyncio
import logging
from datetime import date, timedelta
from uuid import UUID
from app.assembler.allocator import CityAllocator
from app.assembler.lookup import VariantLookup, LookupResult
from app.assembler.connector import CityConnector
from app.services.google.weather import GoogleWeatherService
from app.models.common import Location
from app.db.repository import JourneyRepository, JobRepository, VariantRepository

logger = logging.getLogger(__name__)


class JourneyAssembler:
    def __init__(
        self,
        allocator: CityAllocator,
        lookup: VariantLookup,
        connector: CityConnector,
        weather: GoogleWeatherService,
        journey_repo: JourneyRepository,
        job_repo: JobRepository,
        variant_repo: VariantRepository,
    ):
        self.allocator = allocator
        self.lookup = lookup
        self.connector = connector
        self.weather = weather
        self.journey_repo = journey_repo
        self.job_repo = job_repo
        self.variant_repo = variant_repo

    async def assemble(
        self,
        user_id: UUID,
        destination: str,
        origin: str | None,
        start_date: date,
        total_days: int,
        pace: str,
        budget: str,
        travelers: dict | None = None,
    ) -> dict:
        """Assemble a journey from pre-generated city plans."""
        # Step 1: Allocate cities
        city_allocations = await self.allocator.allocate(destination, total_days, pace, budget)

        # Step 2: Lookup variants (parallel)
        lookup_tasks = [
            self.lookup.find(
                city_name=city.get("name", ""),
                country=city.get("country"),
                pace=pace, budget=budget,
                day_count=city.get("day_count", 3),
            )
            for city in city_allocations
        ]
        lookup_results: list[LookupResult] = await asyncio.gather(*lookup_tasks)

        # Check if any cities need generation
        needs_gen = [lr for lr in lookup_results if lr.needs_generation]
        job_ids = []
        if needs_gen:
            for lr in needs_gen:
                alloc = next((c for c in city_allocations if c.get("name", "").lower() == lr.city_name.lower()), {})
                job = await self.job_repo.create(
                    job_type="on_demand",
                    city_id=lr.city_id,
                    parameters={
                        "city_name": lr.city_name,
                        "country": alloc.get("country", ""),
                        "pace": pace, "budget": budget,
                        "day_count": alloc.get("day_count", 3),
                    },
                    priority=10,
                )
                job_ids.append(str(job.id))

        # Build city sequence
        city_sequence = []
        current_day = 1
        for i, alloc in enumerate(city_allocations):
            lr = lookup_results[i]
            city_sequence.append({
                "city_name": alloc.get("name", ""),
                "city_id": str(lr.city_id) if lr.city_id else None,
                "day_count": alloc.get("day_count", 3),
                "variant_id": str(lr.variant_id) if lr.variant_id else None,
                "start_day": current_day,
                "location": None,  # TODO: get from city record
            })
            current_day += alloc.get("day_count", 3)

        status = "complete" if not needs_gen else "generating"

        # Step 3: Connect cities (only if we have all locations)
        transport_legs = None
        if not needs_gen and len(city_sequence) >= 2:
            # Get locations from city records for connector
            for cs in city_sequence:
                if cs.get("city_id"):
                    # Would need city repo lookup here
                    pass
            # transport_legs = await self.connector.connect(city_sequence)

        # Step 4: Weather (only for complete journeys)
        weather_forecasts = None

        # Step 5: Save journey
        journey = await self.journey_repo.create(
            user_id=str(user_id),
            destination=destination,
            start_date=start_date,
            total_days=total_days,
            pace=pace,
            budget=budget,
            city_sequence=city_sequence,
            origin=origin,
            travelers=travelers,
            transport_legs=transport_legs,
            weather_forecasts=weather_forecasts,
            status=status,
        )

        return {
            "id": str(journey.id),
            "status": status,
            "destination": destination,
            "start_date": start_date.isoformat(),
            "total_days": total_days,
            "city_sequence": city_sequence,
            "transport_legs": transport_legs,
            "weather_forecasts": weather_forecasts,
            "job_ids": job_ids if job_ids else None,
        }
