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
    accommodation: CuratedAccommodation | None = None
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

        # Call LLM — try structured first, fall back to raw JSON parsing
        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                result = await self.llm.generate_structured(
                    system, user, schema=CurationOutput
                )
                self._validate_place_ids(result, valid_ids)
                return result
            except ValueError as e:
                last_error = e
                logger.warning(
                    "Curation validation failed (attempt %d/%d): %s",
                    attempt + 1, max_attempts, e,
                )
            except Exception as e:
                # Pydantic validation failed — try raw JSON parsing
                last_error = e
                logger.warning(
                    "Curation structured output failed (attempt %d/%d): %s",
                    attempt + 1, max_attempts, str(e)[:200],
                )
                # Try raw generation + manual parse
                try:
                    raw = await self.llm.generate(system, user)
                    result = self._parse_raw_output(raw)
                    self._validate_place_ids(result, valid_ids)
                    return result
                except Exception as inner_e:
                    last_error = inner_e
                    logger.warning("Raw parse also failed: %s", str(inner_e)[:200])

        raise ValueError(f"CurationOutput validation failed after {max_attempts} attempt(s): {last_error}")

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

        if result.accommodation and result.accommodation.google_place_id not in valid_ids:
            unknown.append(result.accommodation.google_place_id)

        for alt in result.accommodation_alternatives:
            if alt.google_place_id not in valid_ids:
                unknown.append(alt.google_place_id)

        if unknown:
            raise ValueError(
                f"LLM returned {len(unknown)} unknown place ID(s): {unknown[:5]}"
            )

    def _parse_raw_output(self, raw: str) -> CurationOutput:
        """Try to parse raw LLM text into CurationOutput, handling common wrapper keys."""
        # Extract JSON from markdown code blocks if present
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)

        # Normalize: extract days from various LLM output shapes
        if "days" not in data or not isinstance(data.get("days"), list):
            found = False
            # Check top-level list keys
            for key in ["itinerary", "day_plans", "schedule"]:
                if key in data and isinstance(data[key], list):
                    data["days"] = data[key]
                    found = True
                    break
            # Check nested dict keys
            if not found:
                for key in ["city", "plan", "trip"]:
                    if key in data and isinstance(data[key], dict):
                        nested = data[key]
                        for sub in ["days", "itinerary", "day_plans", "schedule"]:
                            if sub in nested and isinstance(nested[sub], list):
                                data["days"] = nested[sub]
                                found = True
                                break
                        if found:
                            break
            # Deep search: find any list of dicts that look like days
            if not found:
                for key, val in data.items():
                    if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                        if any(k in val[0] for k in ["activities", "theme", "day_number", "places"]):
                            data["days"] = val
                            found = True
                            break

        # Normalize accommodation from various keys
        if "accommodation" not in data or data["accommodation"] is None:
            for key in ["hotel_options", "hotels", "lodging", "primary_hotel"]:
                val = data.get(key)
                if val and isinstance(val, dict):
                    if key == "primary_hotel":
                        # Top-level primary hotel
                        data["accommodation"] = {
                            "google_place_id": val.get("google_place_id", ""),
                            "estimated_nightly_usd": val.get("estimated_nightly_usd") or val.get("estimated_nightly_cost_usd", 100),
                        }
                    else:
                        primary = val.get("primary") or val.get("main")
                        if primary:
                            data["accommodation"] = {
                                "google_place_id": primary.get("google_place_id", ""),
                                "estimated_nightly_usd": primary.get("estimated_nightly_usd") or primary.get("estimated_nightly_cost_usd", 100),
                            }
                    alts = val.get("alternatives", [])
                    if alts and "accommodation_alternatives" not in data:
                        data["accommodation_alternatives"] = [
                            {"google_place_id": a.get("google_place_id", ""),
                             "estimated_nightly_usd": a.get("estimated_nightly_usd") or a.get("estimated_nightly_cost_usd", 80)}
                            for a in alts
                        ]
                    break
            # Also check top-level hotel_alternatives
            if "accommodation_alternatives" not in data and "hotel_alternatives" in data:
                data["accommodation_alternatives"] = [
                    {"google_place_id": a.get("google_place_id", ""),
                     "estimated_nightly_usd": a.get("estimated_nightly_usd") or a.get("estimated_nightly_cost_usd", 80)}
                    for a in data["hotel_alternatives"]
                ]

        # Normalize day entries — ensure day_number and activities exist
        if "days" in data and isinstance(data["days"], list):
            for i, day in enumerate(data["days"]):
                if isinstance(day, dict):
                    if "day_number" not in day:
                        day["day_number"] = day.get("day", i + 1)
                    if "theme" not in day:
                        day["theme"] = day.get("title", day.get("name", f"Day {i + 1}"))
                    if "activities" not in day:
                        day["activities"] = day.get("places", day.get("items", []))

        return CurationOutput.model_validate(data)
