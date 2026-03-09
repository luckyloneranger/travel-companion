import logging

from app.models.journey import JourneyPlan, ReviewResult
from app.models.trip import TripRequest
from app.services.llm.base import LLMService
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class ReviewerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def review(self, plan: JourneyPlan, request: TripRequest, iteration: int = 1, landmarks_context: str = "", must_see_context: str = "") -> ReviewResult:
        """Review a journey plan for feasibility and quality."""
        system_prompt = journey_prompts.load("reviewer_system")

        cities_detail = self._format_cities(plan)
        travel_detail = self._format_travel(plan)

        user_prompt = journey_prompts.load("reviewer_user").format(
            total_days=plan.total_days,
            travel_dates=str(request.start_date),
            route=plan.route or "N/A",
            origin=request.origin or "not specified",
            region=request.destination,
            interests=", ".join(request.interests) if request.interests else "general sightseeing",
            pace=request.pace.value,
            travelers_description=request.travelers.summary if hasattr(request, 'travelers') else "1 adult",
            budget_tier=request.budget.value if hasattr(request, 'budget') else "moderate",
            must_include=", ".join(request.must_include) if request.must_include else "none",
            avoid=", ".join(request.avoid) if request.avoid else "none",
            travel_mode=request.travel_mode.value if hasattr(request, 'travel_mode') else "any",
            cities_detail=cities_detail,
            travel_detail=travel_detail,
            landmarks_context=landmarks_context,
            must_see_context=must_see_context,
        )

        from app.config.planning import LLM_REVIEWER_MAX_TOKENS, LLM_REVIEWER_TEMPERATURE
        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ReviewResult,
            max_tokens=LLM_REVIEWER_MAX_TOKENS,
            temperature=LLM_REVIEWER_TEMPERATURE,
        )

        result.iteration = iteration
        return result

    def _format_cities(self, plan: JourneyPlan) -> str:
        """Format city details with full highlight info for the reviewer."""
        lines = []
        for i, city in enumerate(plan.cities):
            lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
            if city.why_visit:
                lines.append(f"   Why: {city.why_visit}")
            if city.experience_themes:
                lines.append("   Experience themes:")
                for et in city.experience_themes:
                    exc = f" [{et.excursion_type}]" if et.excursion_type else ""
                    dist = f" ({et.distance_from_city_km:.0f}km from city)" if et.distance_from_city_km else ""
                    days = f" ({et.excursion_days} days)" if et.excursion_days else ""
                    lines.append(f"     - {et.theme} ({et.category}){exc}{days}{dist}")
                    if et.why:
                        lines.append(f"       → {et.why}")
                theme_count = len(city.experience_themes)
                lines.append(f"   Theme coverage: {theme_count} themes for {city.days} days")
            else:
                lines.append("   No experience themes")
            if city.accommodation:
                price = f" (${city.accommodation.estimated_nightly_usd}/night)" if city.accommodation.estimated_nightly_usd else ""
                lines.append(f"   Hotel: {city.accommodation.name}{price}")
            if city.best_time_to_visit:
                lines.append(f"   Best time: {city.best_time_to_visit}")
            if city.seasonal_notes:
                lines.append(f"   Seasonal: {city.seasonal_notes}")
            if city.altitude_meters and city.altitude_meters > 1000:
                lines.append(f"   Altitude: {city.altitude_meters:.0f}m")
            if city.safety_notes:
                lines.append(f"   Safety: {city.safety_notes}")
            if city.visa_notes:
                lines.append(f"   Visa: {city.visa_notes}")
            if city.location:
                lines.append(f"   Location: ({city.location.lat:.4f}, {city.location.lng:.4f})")
        return "\n".join(lines) if lines else "No cities specified."

    def _format_travel(self, plan: JourneyPlan) -> str:
        """Format travel leg details with booking and visa info."""
        if not plan.travel_legs:
            return "No travel legs."
        lines = []
        for leg in plan.travel_legs:
            detail = f"{leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h"
            if leg.distance_km:
                detail += f", {leg.distance_km}km"
            lines.append(detail)
            if leg.notes:
                lines.append(f"   Notes: {leg.notes}")
            if leg.booking_tip:
                lines.append(f"   Booking: {leg.booking_tip}")
            if leg.visa_requirement:
                lines.append(f"   Visa: {leg.visa_requirement}")
            if leg.segments:
                for seg in leg.segments:
                    grounded = " [grounded]" if seg.is_grounded else ""
                    lines.append(f"     {seg.mode}: {seg.from_place} → {seg.to_place} ({seg.duration_hours}h){grounded}")
        return "\n".join(lines)
