import logging

from app.models.journey import JourneyPlan, ReviewResult
from app.models.trip import TripRequest
from app.services.llm.base import LLMService
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class ReviewerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def review(self, plan: JourneyPlan, request: TripRequest, iteration: int = 1) -> ReviewResult:
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
            if city.highlights:
                lines.append("   Highlights:")
                total_hours = 0.0
                for h in city.highlights:
                    dur = f", {h.suggested_duration_hours}h" if h.suggested_duration_hours else ""
                    cat = f" ({h.category}{dur})" if h.category else ""
                    exc = f" [{h.excursion_type}]" if h.excursion_type else ""
                    exc_days = f" ({h.excursion_days} days)" if h.excursion_days else ""
                    lines.append(f"     - {h.name}{cat}{exc}{exc_days}")
                    if h.suggested_duration_hours:
                        total_hours += h.suggested_duration_hours
                available = city.days * 8
                pct = (total_hours / available * 100) if available > 0 else 0
                status = "OK" if pct <= 70 else "OVER 70% limit"
                lines.append(f"   Total highlight hours: {total_hours:.1f}h / {available}h ({pct:.0f}% — {status})")
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
        return "\n".join(lines)
