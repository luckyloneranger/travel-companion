"""V6 Planner Agent - Fixes issues in journey plans.

The Planner takes a plan that failed review and fixes the identified issues
while maintaining the overall journey structure.

Uses centralized prompts from app.prompts and service from app.services.external.
"""

import logging

from app.generators.journey_plan.request import JourneyRequest
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    CityStop,
    CityHighlight,
    TravelLeg,
    TransportMode,
    ReviewResult,
)
from app.prompts.loader import journey_prompts
from app.services.external import AzureOpenAIService

logger = logging.getLogger(__name__)


class Planner:
    """Fixes issues in journey plans based on review feedback.
    
    Uses centralized prompts and OpenAI service for consistent behavior.
    """
    
    def __init__(self):
        """Initialize the Planner with centralized service."""
        self._service = AzureOpenAIService()
        self._system_prompt = journey_prompts.load("planner_system")
        self._user_prompt_template = journey_prompts.load("planner_user")
    
    async def revise_plan(
        self,
        plan: JourneyPlan,
        review: ReviewResult,
        request: JourneyRequest,
    ) -> JourneyPlan:
        """
        Revise a journey plan to fix identified issues.
        
        Args:
            plan: The journey plan to revise
            review: Review result with issues to fix
            request: Original journey request for context
            
        Returns:
            Revised JourneyPlan with issues addressed
        """
        # Build issues summary
        issues_text = "\n".join([
            f"- [{issue.severity.upper()}] {issue.description}"
            f"\n  Suggestion: {issue.suggested_fix}"
            for issue in review.issues
        ])
        
        # Build cities detail
        cities_detail = "\n".join([
            f"- {c.name} ({c.days} days): {c.why_visit}"
            for c in plan.cities
        ])
        
        # Build travel detail
        travel_detail = "\n".join([
            f"- {leg.from_city} → {leg.to_city}: {leg.mode.value} ({leg.duration_hours}h)"
            for leg in plan.travel_legs
        ])
        
        # Format system prompt with total days
        system_prompt = self._system_prompt.format(
            total_days=plan.total_days,
        )
        
        user_prompt = self._user_prompt_template.format(
            route=plan.route_string,
            total_days=plan.total_days,
            issues=issues_text,
            origin=request.origin,
            region=request.region or "unknown",
            interests=", ".join(request.interests) if request.interests else "general",
            pace=request.pace or "moderate",
            cities_detail=cities_detail,
            travel_detail=travel_detail,
            travel_dates=str(request.start_date) if request.start_date else "Flexible dates",
        )
        
        logger.info(f"[Planner] Revising plan to fix {len(review.issues)} issues")
        
        data = await self._service.chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        # Parse cities
        cities = []
        for c in data.get("cities", []):
            highlights = []
            for h in c.get("highlights", []):
                highlights.append(CityHighlight(
                    name=h.get("name", ""),
                    description=h.get("description", ""),
                    category=h.get("category", "culture"),
                    suggested_duration_hours=h.get("suggested_duration_hours", 2.0),
                ))
            
            cities.append(CityStop(
                name=c.get("name", ""),
                country=c.get("country", ""),
                days=c.get("days", 1),
                highlights=highlights,
                why_visit=c.get("why_visit", ""),
                best_time_to_visit=c.get("best_time_to_visit", ""),
            ))
        
        # Parse travel legs
        travel_legs = []
        for leg in data.get("travel_legs", []):
            mode_str = leg.get("mode", "drive").lower()
            try:
                mode = TransportMode(mode_str)
            except ValueError:
                mode = TransportMode.DRIVE
            
            travel_legs.append(TravelLeg(
                from_city=leg.get("from_city", ""),
                to_city=leg.get("to_city", ""),
                mode=mode,
                duration_hours=leg.get("duration_hours", 0),
                distance_km=leg.get("distance_km"),
                notes=leg.get("notes", ""),
                estimated_cost=leg.get("estimated_cost"),
                booking_tip=leg.get("booking_tip"),
            ))
        
        revised_plan = JourneyPlan(
            theme=data.get("theme", plan.theme),
            summary=data.get("summary", ""),
            cities=cities,
            travel_legs=travel_legs,
            total_days=plan.total_days,
            origin=request.origin,
            region=request.region,
        )
        
        logger.info(f"[Planner] Revised plan: {revised_plan.route_string}")
        
        return revised_plan
