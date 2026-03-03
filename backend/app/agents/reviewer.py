import logging

from app.models.journey import JourneyPlan, ReviewResult, ReviewIssue
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
            cities_detail=cities_detail,
            travel_detail=travel_detail,
        )

        data = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ReviewResult,
            max_tokens=4000,
            temperature=0.3,
        )

        return self._parse_result(data, iteration)

    def _format_cities(self, plan: JourneyPlan) -> str:
        """Format city details for the prompt."""
        lines = []
        for i, city in enumerate(plan.cities):
            lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
            if city.why_visit:
                lines.append(f"   Why: {city.why_visit}")
            if city.highlights:
                lines.append(f"   Highlights: {', '.join(h.name for h in city.highlights)}")
            if city.accommodation:
                lines.append(f"   Hotel: {city.accommodation.name}")
            if city.location:
                lines.append(f"   Location: ({city.location.lat}, {city.location.lng})")
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
            if leg.notes:
                lines.append(f"   Notes: {leg.notes}")
        return "\n".join(lines)

    def _parse_result(self, data: dict, iteration: int) -> ReviewResult:
        """Parse LLM response into ReviewResult."""
        issues = []
        for issue_data in data.get("issues", []):
            issues.append(ReviewIssue(
                severity=issue_data.get("severity", "minor"),
                category=issue_data.get("category", "general"),
                description=issue_data.get("description", ""),
                affected_leg=issue_data.get("affected_leg"),
                affected_city=issue_data.get("affected_city"),
                suggested_fix=issue_data.get("suggestion", issue_data.get("suggested_fix", "")),
            ))

        score = data.get("score", 70)
        return ReviewResult(
            is_acceptable=score >= 70,
            score=min(max(score, 0), 100),
            issues=issues,
            summary=data.get("summary", ""),
            iteration=iteration,
        )
