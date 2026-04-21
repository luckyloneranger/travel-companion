"""Curation pipeline — LLM selects activities from Google-grounded candidates.

The curator receives verified place candidates and builds themed day plans,
selecting ONLY from provided candidates (no invention). Place IDs are
validated post-LLM to ensure grounding.
"""

import json
import logging

from pydantic import BaseModel

from app.algorithms.scheduler import ScheduleConfig
from app.prompts.loader import PromptLoader
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas for structured LLM output
# ---------------------------------------------------------------------------


class CuratedActivity(BaseModel):
    """A single activity selected from candidates."""

    google_place_id: str
    category: str  # cultural, dining, nature, shopping, etc.
    description: str
    duration_minutes: int = 60
    is_meal: bool = False
    meal_type: str | None = None  # breakfast / lunch / dinner
    estimated_cost_usd: float = 0.0


class CuratedDay(BaseModel):
    """A themed day plan."""

    day_number: int
    theme: str
    theme_description: str | None = None
    activities: list[CuratedActivity]


class CuratedAccommodation(BaseModel):
    """A selected hotel from lodging candidates."""

    google_place_id: str
    estimated_nightly_usd: float


class CurationOutput(BaseModel):
    """Full curation result for a city."""

    days: list[CuratedDay]
    accommodation: CuratedAccommodation
    accommodation_alternatives: list[CuratedAccommodation] = []
    booking_hint: str | None = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class CurationPipeline:
    """Curates multi-day itineraries from Google-grounded candidates via LLM."""

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.prompts = PromptLoader("curation")

    async def curate(
        self,
        city_name: str,
        country: str,
        candidates: list[dict],
        lodging_candidates: list[dict],
        pace: str = "moderate",
        budget: str = "moderate",
        day_count: int = 3,
    ) -> CurationOutput:
        """Run the curation pipeline for a single city.

        Args:
            city_name: City name (e.g., "Tokyo").
            country: Country name (e.g., "Japan").
            candidates: Activity candidate dicts with google_place_id/place_id.
            lodging_candidates: Lodging candidate dicts with google_place_id/place_id.
            pace: Trip pace — relaxed, moderate, or packed.
            budget: Budget tier — budget, moderate, expensive, or luxury.
            day_count: Number of days to plan.

        Returns:
            CurationOutput with validated place IDs.

        Raises:
            ValueError: If LLM returns place IDs not in candidates (after retry).
        """
        # Build valid ID set
        valid_ids = {
            c.get("google_place_id") or c.get("place_id")
            for c in candidates + lodging_candidates
        }
        valid_ids.discard(None)

        # Format candidates compactly
        candidates_json = self._format_candidates(candidates)
        lodging_json = self._format_candidates(lodging_candidates)

        # Get meal guidance
        meal_guidance = self._get_meal_guidance(country)

        # Load and format prompts
        system = self.prompts.load("curator_system")
        user = self.prompts.load("curator_user").format(
            city_name=city_name,
            country=country,
            day_count=day_count,
            pace=pace,
            budget=budget,
            meal_time_guidance=meal_guidance,
            candidate_count=len(candidates),
            candidates_json=candidates_json,
            lodging_count=len(lodging_candidates),
            lodging_json=lodging_json,
        )

        # Call LLM with one retry on validation failure
        max_retries = 1
        last_error: ValueError | None = None

        for attempt in range(max_retries + 1):
            result = await self.llm.generate_structured(
                system, user, schema=CurationOutput
            )
            try:
                self._validate_place_ids(result, valid_ids)
                return result
            except ValueError as e:
                last_error = e
                logger.warning(
                    "Curation validation failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    e,
                )

        raise last_error  # type: ignore[misc]

    def _format_candidates(self, candidates: list[dict]) -> str:
        """Format candidates as compact JSON for the prompt."""
        compact = []
        for c in candidates:
            entry: dict = {
                "id": c.get("google_place_id") or c.get("place_id", ""),
                "name": c.get("name", ""),
                "types": c.get("types", []),
            }
            if c.get("rating"):
                entry["rating"] = c["rating"]
            if c.get("opening_hours"):
                entry["hours"] = c["opening_hours"]
            compact.append(entry)
        return json.dumps(compact, indent=None, ensure_ascii=False)

    def _get_meal_guidance(self, country: str) -> str:
        """Generate meal time guidance from regional schedule config."""
        config = ScheduleConfig.for_region(country)
        return (
            f"## Meal Time Guidance for {country}\n"
            f"- Lunch window: {config.lunch_window_start.strftime('%H:%M')} - "
            f"{config.lunch_window_end.strftime('%H:%M')}\n"
            f"- Dinner window: {config.dinner_window_start.strftime('%H:%M')} - "
            f"{config.dinner_window_end.strftime('%H:%M')}"
        )

    def _validate_place_ids(
        self, result: CurationOutput, valid_ids: set[str]
    ) -> None:
        """Validate that all place IDs in the result exist in candidates.

        Raises:
            ValueError: If any unknown place IDs are found.
        """
        unknown: list[str] = []

        for day in result.days:
            for activity in day.activities:
                if activity.google_place_id not in valid_ids:
                    unknown.append(activity.google_place_id)

        if result.accommodation.google_place_id not in valid_ids:
            unknown.append(result.accommodation.google_place_id)

        for alt in result.accommodation_alternatives:
            if alt.google_place_id not in valid_ids:
                unknown.append(alt.google_place_id)

        if unknown:
            raise ValueError(
                f"LLM returned {len(unknown)} unknown place ID(s): {unknown[:5]}"
            )
