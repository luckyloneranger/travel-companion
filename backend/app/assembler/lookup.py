"""Variant lookup — finds pre-generated plans for cities."""

import logging
from uuid import UUID
from dataclasses import dataclass
from app.db.repository import CityRepository, VariantRepository

logger = logging.getLogger(__name__)


@dataclass
class LookupResult:
    city_id: UUID | None
    city_name: str
    variant_id: UUID | None
    variant: object | None  # PlanVariant
    needs_generation: bool
    day_count_mismatch: bool = False  # have variant but wrong day count


class VariantLookup:
    def __init__(self, city_repo: CityRepository, variant_repo: VariantRepository):
        self.city_repo = city_repo
        self.variant_repo = variant_repo

    async def find(
        self,
        city_name: str,
        country: str | None,
        pace: str,
        budget: str,
        day_count: int,
    ) -> LookupResult:
        """Find a published variant for a city.

        Tries exact match first. Falls back to closest day_count.
        """
        # Find city by name
        city = None
        if country:
            cities, _ = await self.city_repo.list(limit=100)
            for c in cities:
                if c.name.lower() == city_name.lower():
                    city = c
                    break

        if not city:
            return LookupResult(
                city_id=None, city_name=city_name,
                variant_id=None, variant=None,
                needs_generation=True,
            )

        # Exact lookup
        variant = await self.variant_repo.lookup(
            city_id=city.id, pace=pace, budget=budget,
            day_count=day_count, status="published",
        )
        if variant:
            return LookupResult(
                city_id=city.id, city_name=city_name,
                variant_id=variant.id, variant=variant,
                needs_generation=False,
            )

        # Try draft
        variant = await self.variant_repo.lookup(
            city_id=city.id, pace=pace, budget=budget,
            day_count=day_count, status="draft",
        )
        if variant:
            return LookupResult(
                city_id=city.id, city_name=city_name,
                variant_id=variant.id, variant=variant,
                needs_generation=False,
            )

        # No match at all
        return LookupResult(
            city_id=city.id, city_name=city_name,
            variant_id=None, variant=None,
            needs_generation=True,
        )
