import logging

from app.models.common import TransportMode
from app.models.journey import (
    JourneyPlan,
    CityStop,
    CityHighlight,
    TravelLeg,
    Accommodation,
    ReviewResult,
)
from app.services.llm.base import LLMService
from app.prompts import journey_prompts

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def fix_plan(self, plan: JourneyPlan, review: ReviewResult) -> JourneyPlan:
        """Fix a journey plan based on reviewer feedback."""
        system_prompt = journey_prompts.load("planner_system")

        # Format current plan and issues
        plan_text = self._format_plan(plan)
        issues_text = self._format_issues(review)

        user_prompt = journey_prompts.load("planner_user").format(
            journey_plan=plan_text,
            review_score=review.score,
            review_summary=review.summary,
            issues=issues_text,
        )

        data = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=JourneyPlan,
            max_tokens=8000,
            temperature=0.7,
        )

        return self._parse_plan(data, plan)

    def _format_plan(self, plan: JourneyPlan) -> str:
        """Format plan for the planner prompt."""
        # Same format as reviewer
        lines = [f"Theme: {plan.theme}", f"Total Days: {plan.total_days}", f"Route: {plan.route}", ""]
        for i, city in enumerate(plan.cities):
            lines.append(f"{i+1}. {city.name}, {city.country} ({city.days} days)")
        for leg in plan.travel_legs:
            lines.append(f"   {leg.from_city} → {leg.to_city}: {leg.mode.value}, {leg.duration_hours}h")
        return "\n".join(lines)

    def _format_issues(self, review: ReviewResult) -> str:
        """Format review issues for the planner."""
        if not review.issues:
            return "No specific issues."
        lines = []
        for issue in review.issues:
            lines.append(f"- [{issue.severity.upper()}] {issue.description}")
            if issue.suggested_fix:
                lines.append(f"  Suggested fix: {issue.suggested_fix}")
        return "\n".join(lines)

    def _parse_plan(self, data: dict, original: JourneyPlan) -> JourneyPlan:
        """Parse fixed plan from LLM response. Falls back to original on parse errors."""
        try:
            cities = []
            for city_data in data.get("cities", []):
                highlights = [
                    CityHighlight(
                        name=h.get("name", ""),
                        description=h.get("description", ""),
                        category=h.get("category", ""),
                    )
                    for h in city_data.get("highlights", [])
                ]
                accommodation = None
                acc = city_data.get("accommodation")
                if acc and isinstance(acc, dict):
                    accommodation = Accommodation(name=acc.get("name", ""))
                cities.append(CityStop(
                    name=city_data.get("name", ""),
                    country=city_data.get("country", ""),
                    days=city_data.get("days", 1),
                    highlights=highlights,
                    why_visit=city_data.get("why_visit", ""),
                    accommodation=accommodation,
                ))

            travel_legs = []
            for leg_data in data.get("travel_legs", []):
                try:
                    mode = TransportMode(leg_data.get("mode", "drive").lower())
                except ValueError:
                    mode = TransportMode.DRIVE
                travel_legs.append(TravelLeg(
                    from_city=leg_data.get("from_city", ""),
                    to_city=leg_data.get("to_city", ""),
                    mode=mode,
                    duration_hours=leg_data.get("duration_hours", 0),
                    notes=leg_data.get("notes", ""),
                ))

            return JourneyPlan(
                theme=data.get("theme", original.theme),
                summary=data.get("summary", original.summary),
                origin=data.get("origin", original.origin),
                cities=cities if cities else original.cities,
                travel_legs=travel_legs if travel_legs else original.travel_legs,
                total_days=data.get("total_days", original.total_days),
                route=" → ".join([original.origin] + [c.name for c in cities]) if cities else original.route,
            )
        except Exception as e:
            logger.error(f"Failed to parse fixed plan, returning original: {e}")
            return original
