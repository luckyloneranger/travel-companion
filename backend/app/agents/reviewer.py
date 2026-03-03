import logging

from app.models.journey import JourneyPlan, ReviewResult, ReviewIssue
from app.services.llm.base import LLMService
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class ReviewerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def review(self, plan: JourneyPlan, iteration: int = 1) -> ReviewResult:
        """Review a journey plan for feasibility and quality."""
        system_prompt = journey_prompts.load("reviewer_system")

        # Format plan data for the reviewer prompt
        plan_text = self._format_plan_for_review(plan)
        user_prompt = journey_prompts.load("reviewer_user").format(
            journey_plan=plan_text,
            iteration=iteration,
        )

        data = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ReviewResult,
            max_tokens=4000,
            temperature=0.3,
        )

        return self._parse_result(data, iteration)

    def _format_plan_for_review(self, plan: JourneyPlan) -> str:
        """Format journey plan as text for the reviewer prompt."""
        lines = [
            f"Theme: {plan.theme}",
            f"Summary: {plan.summary}",
            f"Total Days: {plan.total_days}",
            f"Route: {plan.route or 'N/A'}",
            "",
            "## Cities:",
        ]
        for i, city in enumerate(plan.cities):
            lines.append(f"\n### {i+1}. {city.name}, {city.country} ({city.days} days)")
            if city.why_visit:
                lines.append(f"   Why: {city.why_visit}")
            if city.highlights:
                lines.append(f"   Highlights: {', '.join(h.name for h in city.highlights)}")
            if city.accommodation:
                lines.append(f"   Hotel: {city.accommodation.name}")
            if city.location:
                lines.append(f"   Location: ({city.location.lat}, {city.location.lng})")

        if plan.travel_legs:
            lines.append("\n## Travel Legs:")
            for leg in plan.travel_legs:
                lines.append(f"   {leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h")
                if leg.distance_km:
                    lines.append(f"      Distance: {leg.distance_km} km")
                if leg.notes:
                    lines.append(f"      Notes: {leg.notes}")

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
