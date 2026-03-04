"""Scout agent — generates an initial journey plan from a trip request via LLM.

The Scout uses pure LLM intelligence to generate a high-quality journey plan.
It suggests cities, creates a sensible route, and recommends transport modes.
"""

import logging

from app.config.regional_transport import get_transport_guidance
from app.models.common import TransportMode
from app.models.journey import (
    Accommodation,
    CityHighlight,
    CityStop,
    JourneyPlan,
    TravelLeg,
)
from app.models.trip import TripRequest
from app.prompts import journey_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class ScoutAgent:
    """Generates initial journey plan using LLM intelligence.

    Uses centralized prompts and an injected LLM service for consistent behavior.

    Parameters
    ----------
    llm:
        Any ``LLMService`` implementation (Azure OpenAI, Anthropic, etc.).
    """

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def generate_plan(self, request: TripRequest) -> JourneyPlan:
        """Generate initial journey plan from user request.

        The Scout decides the optimal number of cities based on total days,
        pace preference, and regional distances.

        Args:
            request: Unified trip request with destination, interests, pace, etc.

        Returns:
            JourneyPlan with cities and travel legs (not yet enriched with
            real API data).
        """
        transport_guidance = get_transport_guidance(
            origin=request.origin or "",
            region=request.destination,
        )

        system_prompt = journey_prompts.load("scout_system").format(
            region=request.destination,
            total_days=request.total_days,
            pace=request.pace.value,
            travel_dates=str(request.start_date),
        )

        user_prompt = journey_prompts.load("scout_user").format(
            region=request.destination,
            origin=request.origin or "not specified",
            total_days=request.total_days,
            travel_dates=str(request.start_date),
            interests=(
                ", ".join(request.interests) if request.interests else "general sightseeing"
            ),
            pace=request.pace.value,
            must_include=(
                ", ".join(request.must_include) if request.must_include else "none"
            ),
            avoid=", ".join(request.avoid) if request.avoid else "none",
            transport_guidance=transport_guidance,
        )

        logger.info(
            "[Scout] Generating %d-day journey for %s",
            request.total_days,
            request.destination,
        )

        data = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=8000,
            temperature=0.8,
        )

        plan = self._parse_plan(data, request)

        # Validate travel legs count: should be N-1 for N cities.
        expected_legs = len(plan.cities) - 1
        if plan.travel_legs and len(plan.travel_legs) != expected_legs and expected_legs > 0:
            logger.warning(
                "[Scout] Travel legs mismatch: got %d, expected %d for %d cities",
                len(plan.travel_legs),
                expected_legs,
                len(plan.cities),
            )

        logger.info(
            "[Scout] Generated plan with %d cities: %s",
            len(plan.cities),
            plan.route or "no route",
        )

        return plan

    def _parse_plan(self, data: dict, request: TripRequest) -> JourneyPlan:
        """Parse LLM response dict into a JourneyPlan model.

        Args:
            data: Raw dict from the LLM structured output.
            request: Original trip request for fallback values.

        Returns:
            Validated JourneyPlan instance.
        """
        cities = []
        for city_data in data.get("cities", []):
            highlights = [
                CityHighlight(
                    name=h.get("name", ""),
                    description=h.get("description", ""),
                    category=h.get("category", ""),
                    suggested_duration_hours=h.get("suggested_duration_hours"),
                )
                for h in city_data.get("highlights", [])
            ]

            accommodation = None
            acc_data = city_data.get("accommodation")
            if acc_data and isinstance(acc_data, dict) and acc_data.get("name"):
                accommodation = Accommodation(
                    name=acc_data["name"],
                    estimated_nightly_usd=acc_data.get("estimated_nightly_usd"),
                )

            cities.append(
                CityStop(
                    name=city_data.get("name", ""),
                    country=city_data.get("country", ""),
                    days=city_data.get("days", 1),
                    highlights=highlights,
                    why_visit=city_data.get("why_visit", ""),
                    best_time_to_visit=city_data.get("best_time_to_visit", ""),
                    accommodation=accommodation,
                )
            )

        travel_legs = []
        for leg_data in data.get("travel_legs", []):
            mode_str = leg_data.get("mode", "drive").lower()
            try:
                mode = TransportMode(mode_str)
            except ValueError:
                mode = TransportMode.DRIVE

            travel_legs.append(
                TravelLeg(
                    from_city=leg_data.get("from_city", ""),
                    to_city=leg_data.get("to_city", ""),
                    mode=mode,
                    duration_hours=leg_data.get("duration_hours", 0),
                    distance_km=leg_data.get("distance_km"),
                    notes=leg_data.get("notes", ""),
                    fare=leg_data.get("estimated_cost") or leg_data.get("fare"),
                    fare_usd=leg_data.get("fare_usd"),
                    booking_tip=leg_data.get("booking_tip"),
                )
            )

        route = (
            " \u2192 ".join([request.origin] + [c.name for c in cities])
            if request.origin
            else " \u2192 ".join(c.name for c in cities)
        )

        return JourneyPlan(
            theme=data.get("theme", "Journey of Discovery"),
            summary=data.get("summary", ""),
            origin=data.get("origin", request.origin),
            cities=cities,
            travel_legs=travel_legs,
            total_days=data.get("total_days", request.total_days),
            route=route,
        )
