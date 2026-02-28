"""V6 Reviewer Agent - Evaluates journey plan feasibility.

The Reviewer checks if a journey plan is practical and identifies
issues that need to be fixed by the Planner.

Uses centralized prompts from app.prompts and service from app.services.external.
"""

import logging
from typing import Optional

from app.generators.journey_plan.request import JourneyRequest
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    ReviewResult,
    ReviewIssue,
)
from app.prompts.loader import journey_prompts
from app.services.external import AzureOpenAIService

logger = logging.getLogger(__name__)


class Reviewer:
    """Evaluates journey plans for feasibility and quality.
    
    Uses centralized prompts and OpenAI service for consistent behavior.
    """
    
    def __init__(self):
        """Initialize the Reviewer with centralized service."""
        self._service = AzureOpenAIService()
        self._system_prompt = journey_prompts.load("reviewer_system")
        self._user_prompt_template = journey_prompts.load("reviewer_user")
    
    async def review(
        self,
        plan: JourneyPlan,
        request: JourneyRequest,
        iteration: int = 1,
    ) -> ReviewResult:
        """
        Review a journey plan for feasibility.
        
        Args:
            plan: The journey plan to review
            request: Original journey request for context
            iteration: Current iteration number
            
        Returns:
            ReviewResult with score, issues, and acceptability
        """
        # Build cities detail with highlight count
        cities_detail = "\n".join([
            f"- {c.name} ({c.days} days, {len(c.highlights)} highlights): {c.why_visit}"
            for c in plan.cities
        ])

        # Build travel detail with enriched data
        travel_parts = []
        for leg in plan.travel_legs:
            detail = f"- {leg.from_city} → {leg.to_city}: {leg.mode.value} ({leg.duration_hours}h"
            if leg.distance_km:
                detail += f", {leg.distance_km}km"
            detail += ")"
            extras = []
            if leg.fare:
                extras.append(f"fare: {leg.fare}")
            if leg.num_transfers > 0:
                extras.append(f"{leg.num_transfers} transfer(s)")
            if leg.departure_time and leg.arrival_time:
                extras.append(f"{leg.departure_time} → {leg.arrival_time}")
            if extras:
                detail += f" [{', '.join(extras)}]"
            travel_parts.append(detail)
        travel_detail = "\n".join(travel_parts)
        
        user_prompt = self._user_prompt_template.format(
            total_days=plan.total_days,
            route=plan.route_string,
            origin=request.origin,
            region=request.region or "unknown",
            interests=", ".join(request.interests) if request.interests else "general",
            cities_detail=cities_detail,
            travel_detail=travel_detail,
            travel_dates=str(request.start_date) if request.start_date else "Flexible dates",
            pace=request.pace or "moderate",
        )
        
        logger.info(f"[Reviewer] Reviewing plan (iteration {iteration}): {plan.route_string}")
        
        data = await self._service.chat_completion_json(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        
        # Parse issues
        issues = []
        for issue in data.get("issues", []):
            severity_str = issue.get("severity", "minor").lower()
            
            issues.append(ReviewIssue(
                severity=severity_str,
                category=issue.get("category", "general"),
                description=issue.get("description", ""),
                suggested_fix=issue.get("suggestion", ""),
            ))
        
        result = ReviewResult(
            is_acceptable=data.get("is_acceptable", False),
            score=data.get("score", 0),
            issues=issues,
            summary=data.get("summary", ""),
            iteration=iteration,
        )
        
        logger.info(
            f"[Reviewer] Review complete: score={result.score}, "
            f"acceptable={result.is_acceptable}, "
            f"critical_issues={len(result.critical_issues)}"
        )
        
        return result
