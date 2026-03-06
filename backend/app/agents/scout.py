"""Scout agent — generates an initial journey plan from a trip request via LLM.

The Scout uses pure LLM intelligence to generate a high-quality journey plan.
It suggests cities, creates a sensible route, and recommends transport modes.
"""

import logging

from app.config.regional_transport import get_transport_guidance
from app.models.journey import Accommodation, JourneyPlan
from app.models.trip import TripRequest
from app.prompts import journey_prompts
from app.services.llm.base import LLMService
from app.services.llm.exceptions import LLMValidationError

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
            travelers_description=request.travelers.summary,
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

        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_SCOUT_TEMPERATURE
        plan = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_SCOUT_TEMPERATURE,
        )

        self._validate_plan(plan)

        # Ensure total_days is set (LLM may omit it)
        if not plan.total_days:
            plan.total_days = request.total_days

        # Build route string
        plan.route = (
            " → ".join([request.origin] + [c.name for c in plan.cities])
            if request.origin
            else " → ".join(c.name for c in plan.cities)
        )

        logger.info(
            "[Scout] Generated plan with %d cities: %s",
            len(plan.cities),
            plan.route or "no route",
        )

        return plan

    def _validate_plan(self, plan: JourneyPlan) -> None:
        """Semantic validation of a journey plan.

        Args:
            plan: The JourneyPlan to validate.

        Raises:
            LLMValidationError: If semantic checks fail.
        """
        if not plan.cities:
            raise LLMValidationError("JourneyPlan", ["No cities in plan"], 1)
        for i, city in enumerate(plan.cities):
            if not city.name.strip():
                raise LLMValidationError("JourneyPlan", [f"City at index {i} has empty name"], 1)
        # Ensure every city has an accommodation
        for city in plan.cities:
            if not city.accommodation or not city.accommodation.name:
                logger.warning(
                    "[Scout] City %s has no accommodation — adding placeholder",
                    city.name,
                )
                city.accommodation = Accommodation(
                    name=f"Hotel in {city.name}",
                    estimated_nightly_usd=100,  # Safe default
                )

        # Collapse city-state / single-city multi-destination plans into one
        self._collapse_city_state_destinations(plan)

        expected_legs = len(plan.cities) - 1
        if expected_legs > 0 and len(plan.travel_legs) != expected_legs:
            raise LLMValidationError(
                "JourneyPlan",
                [f"Expected {expected_legs} travel legs for {len(plan.cities)} cities, got {len(plan.travel_legs)}"],
                1,
            )

    # City-states and single-city destinations that should never be split
    _CITY_STATES: set[str] = {
        "singapore", "hong kong", "macau", "macao", "monaco", "luxembourg",
        "bahrain", "qatar", "doha", "abu dhabi", "dubai",
    }

    @classmethod
    def _collapse_city_state_destinations(cls, plan: JourneyPlan) -> None:
        """Collapse multi-destination plans for city-states into a single destination.

        When the LLM splits a city-state (e.g., Singapore) into multiple
        sub-destinations (Marina Bay, Sentosa, Pulau Ubin), merge them into
        one destination with combined days and highlights.
        """
        if len(plan.cities) <= 1:
            return

        # Check if all cities share the same country AND that country is a city-state
        countries = {(c.country or "").lower().strip() for c in plan.cities}
        if len(countries) != 1:
            return
        country = countries.pop()

        # Also check city names for city-state matches
        all_names = " ".join(c.name.lower() for c in plan.cities)
        is_city_state = (
            country in cls._CITY_STATES
            or any(cs in all_names for cs in cls._CITY_STATES)
            or any(cs in country for cs in cls._CITY_STATES)
        )
        if not is_city_state:
            return

        logger.info(
            "[Scout] Collapsing %d sub-destinations in city-state %s into one",
            len(plan.cities), country,
        )

        # Merge all cities into one
        primary = plan.cities[0]
        primary.name = country.title() if len(country) > 3 else plan.cities[0].name.split(",")[0].split("(")[0].strip()
        primary.days = sum(c.days for c in plan.cities)

        # Merge highlights from all cities
        seen_highlights: set[str] = set()
        merged_highlights = []
        for city in plan.cities:
            for h in city.highlights:
                if h.name not in seen_highlights:
                    seen_highlights.add(h.name)
                    merged_highlights.append(h)
        primary.highlights = merged_highlights

        # Merge why_visit
        reasons = [c.why_visit for c in plan.cities if c.why_visit]
        if reasons:
            primary.why_visit = reasons[0]

        # Keep the best accommodation (highest nightly rate as proxy for quality)
        best_acc = max(
            (c.accommodation for c in plan.cities if c.accommodation),
            key=lambda a: a.estimated_nightly_usd or 0,
            default=primary.accommodation,
        )
        primary.accommodation = best_acc

        plan.cities = [primary]
        plan.travel_legs = []
