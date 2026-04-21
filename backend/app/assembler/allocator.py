"""City allocator — splits a destination into cities with day counts."""

import logging
from pydantic import BaseModel
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class CityAllocationOutput(BaseModel):
    cities: list[dict]  # [{name, country, day_count, order}]


class CityAllocator:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def allocate(
        self,
        destination: str,
        total_days: int,
        pace: str = "moderate",
        budget: str = "moderate",
    ) -> list[dict]:
        """Split destination into cities with day allocation.

        Returns list of {name, country, day_count, order}.
        """
        system = (
            "You are a travel planner. Given a destination and total days, "
            "allocate days across cities. Each city needs at least 2 days. "
            "Order cities geographically to minimize backtracking. "
            "Return a JSON object with a 'cities' array."
        )
        user = (
            f"Destination: {destination}\n"
            f"Total days: {total_days}\n"
            f"Pace: {pace}\n"
            f"Budget: {budget}\n\n"
            f"Split into cities with day counts. Each city needs at least 2 days."
        )
        result = await self.llm.generate_structured(system, user, schema=CityAllocationOutput)

        # Validate total days
        allocated = sum(c.get("day_count", 0) for c in result.cities)
        if allocated != total_days:
            logger.warning(f"Allocated {allocated} days but requested {total_days}, adjusting last city")
            if result.cities:
                diff = total_days - allocated
                result.cities[-1]["day_count"] = max(2, result.cities[-1].get("day_count", 2) + diff)

        return result.cities
