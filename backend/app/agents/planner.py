import logging

from app.models.journey import (
    JourneyPlan,
    ReviewResult,
)
from app.models.trip import TripRequest
from app.services.llm.base import LLMService
from app.services.llm.exceptions import LLMValidationError
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def fix_plan(self, plan: JourneyPlan, review: ReviewResult, request: TripRequest) -> JourneyPlan:
        """Fix a journey plan based on reviewer feedback."""
        system_prompt = journey_prompts.load("planner_system")

        cities_detail = self._format_cities(plan)
        travel_detail = self._format_travel(plan)
        issues_text = self._format_issues(review)

        user_prompt = journey_prompts.load("planner_user").format(
            route=plan.route or "N/A",
            total_days=plan.total_days,
            issues=issues_text,
            origin=request.origin or "not specified",
            region=request.destination,
            interests=", ".join(request.interests) if request.interests else "general sightseeing",
            pace=request.pace.value,
            travel_dates=str(request.start_date),
            travelers_description=request.travelers.summary if hasattr(request, 'travelers') else "1 adult",
            budget_tier=request.budget.value if hasattr(request, 'budget') else "moderate",
            cities_detail=cities_detail,
            travel_detail=travel_detail,
        )

        from app.config.planning import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE
        fixed = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=LLM_DEFAULT_MAX_TOKENS,
            temperature=LLM_DEFAULT_TEMPERATURE,
        )

        self._validate_plan(fixed)

        # Ensure total_days is set (LLM may omit it)
        if not fixed.total_days:
            fixed.total_days = request.total_days

        fixed.route = (
            " → ".join([request.origin] + [c.name for c in fixed.cities])
            if request.origin
            else " → ".join(c.name for c in fixed.cities)
        )

        return fixed

    def _format_cities(self, plan: JourneyPlan) -> str:
        """Format city details for the prompt."""
        lines = []
        for i, city in enumerate(plan.cities):
            lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
            if city.highlights:
                lines.append(f"   Highlights: {', '.join(h.name for h in city.highlights)}")
            if city.accommodation:
                lines.append(f"   Hotel: {city.accommodation.name}")
        return "\n".join(lines) if lines else "No cities specified."

    def _format_travel(self, plan: JourneyPlan) -> str:
        """Format travel leg details for the prompt."""
        if not plan.travel_legs:
            return "No travel legs."
        lines = []
        for leg in plan.travel_legs:
            detail = f"{leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h"
            if leg.distance_km:
                detail += f", {leg.distance_km}km"
            lines.append(detail)
        return "\n".join(lines)

    def _format_issues(self, review: ReviewResult) -> str:
        """Format review issues and dimension scores for the planner."""
        lines = []
        if review.dimension_scores:
            lines.append("**Dimension Scores (focus on WEAK areas):**")
            for dim, score in review.dimension_scores.items():
                status = "WEAK" if score < 70 else ("OK" if score < 85 else "GOOD")
                lines.append(f"  - {dim}: {score}/100 [{status}]")
            lines.append("")
        if not review.issues:
            lines.append("No specific issues.")
            return "\n".join(lines)
        for issue in review.issues:
            lines.append(f"- [{issue.severity.upper()}] {issue.description}")
            if issue.suggested_fix:
                lines.append(f"  Suggested fix: {issue.suggested_fix}")
        return "\n".join(lines)

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
        expected_legs = len(plan.cities) - 1
        if expected_legs > 0 and len(plan.travel_legs) != expected_legs:
            raise LLMValidationError(
                "JourneyPlan",
                [f"Expected {expected_legs} travel legs for {len(plan.cities)} cities, got {len(plan.travel_legs)}"],
                1,
            )
