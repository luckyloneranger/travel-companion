"""V6 Journey Orchestrator - LLM-First with Iterative Refinement.

V6 Architecture:
1. Scout: LLM generates initial journey (cities + travel)
2. Enrich: Google APIs ground with real data
3. Review: Evaluate feasibility
4. IF NOT acceptable:
   - Planner: Fix issues
   - Enrich: Update with new data
   - Review: Re-evaluate
5. REPEAT until acceptable or max iterations

This approach uses LLM intelligence for what it's good at (creative planning,
geographic knowledge) and APIs for what they're good at (real-time data).
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional

from app.generators.journey_plan.request import JourneyRequest
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    EnrichedPlan,
    ReviewResult,
    V6Progress,
)
from app.generators.journey_plan.v6.scout import Scout
from app.generators.journey_plan.v6.enricher import Enricher
from app.generators.journey_plan.v6.reviewer import Reviewer
from app.generators.journey_plan.v6.planner import Planner

logger = logging.getLogger(__name__)


class V6Orchestrator:
    """Orchestrates V6 journey planning with iterative refinement."""
    
    MAX_ITERATIONS = 3  # Prevent infinite loops
    MIN_ACCEPTABLE_SCORE = 70
    
    def __init__(self):
        self.scout = Scout()
        self.enricher = Enricher()
        self.reviewer = Reviewer()
        self.planner = Planner()
    
    async def plan_journey(
        self,
        request: JourneyRequest,
    ) -> EnrichedPlan:
        """
        Plan a journey with iterative refinement.
        
        Args:
            request: Journey request
            
        Returns:
            Final EnrichedPlan that passed review
        """
        # Phase 1: Scout generates initial plan
        logger.info(f"[V6] Starting journey planning: {request.origin} → {request.region}")
        
        plan = await self.scout.generate_plan(request)
        
        # Phase 2: Enrich with real data
        enriched = await self.enricher.enrich_plan(plan)
        
        # Phase 3: Iterative review-fix loop
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            # Review
            review = await self.reviewer.review(enriched.plan, request, iteration)
            
            if review.is_acceptable and review.score >= self.MIN_ACCEPTABLE_SCORE:
                logger.info(f"[V6] Plan accepted on iteration {iteration} (score: {review.score})")
                return enriched
            
            if iteration == self.MAX_ITERATIONS:
                logger.warning(f"[V6] Max iterations reached, returning best effort")
                return enriched
            
            # Fix issues
            logger.info(f"[V6] Iteration {iteration} rejected (score: {review.score}), fixing...")
            revised_plan = await self.planner.revise_plan(enriched.plan, review, request)
            
            # Re-enrich
            enriched = await self.enricher.enrich_plan(revised_plan)
        
        return enriched
    
    async def plan_journey_stream(
        self,
        request: JourneyRequest,
    ) -> AsyncGenerator[V6Progress, None]:
        """
        Plan a journey with streaming progress updates.
        
        Yields V6Progress objects for each phase.
        """
        try:
            # Phase 1: Scout
            yield V6Progress(
                phase="scout",
                step="start",
                message="Scout is generating initial journey plan...",
                progress=5,
            )
            
            plan = await self.scout.generate_plan(request)
            
            yield V6Progress(
                phase="scout",
                step="complete",
                message=f"Scout generated: {plan.route_string}",
                progress=20,
                data={
                    "route": plan.route_string,
                    "cities": plan.city_names,
                    "theme": plan.theme,
                },
            )
            
            # Phase 2: Initial Enrich
            yield V6Progress(
                phase="enrich",
                step="start",
                message="Enriching plan with real transport data...",
                progress=25,
            )
            
            enriched = await self.enricher.enrich_plan(plan)
            
            yield V6Progress(
                phase="enrich",
                step="complete",
                message=f"Enriched: {enriched.total_travel_hours:.1f}h total travel",
                progress=35,
                data={
                    "total_travel_hours": enriched.total_travel_hours,
                    "total_distance_km": enriched.total_distance_km,
                },
            )
            
            # Phase 3: Iterative review-fix loop
            for iteration in range(1, self.MAX_ITERATIONS + 1):
                base_progress = 35 + (iteration - 1) * 20
                
                # Review
                yield V6Progress(
                    phase="review",
                    step="start",
                    message=f"Reviewing plan (iteration {iteration})...",
                    progress=base_progress + 5,
                    iteration=iteration,
                )
                
                review = await self.reviewer.review(enriched.plan, request, iteration)
                
                yield V6Progress(
                    phase="review",
                    step="complete",
                    message=f"Review score: {review.score}/100 - {'✅ Accepted' if review.is_acceptable else '⚠️ Needs fixes'}",
                    progress=base_progress + 10,
                    iteration=iteration,
                    data={
                        "score": review.score,
                        "is_acceptable": review.is_acceptable,
                        "summary": review.summary,
                        "critical_issues": len(review.critical_issues),
                        "warnings": len(review.warnings),
                    },
                )
                
                if review.is_acceptable and review.score >= self.MIN_ACCEPTABLE_SCORE:
                    yield V6Progress(
                        phase="complete",
                        step="success",
                        message=f"Journey plan finalized! Score: {review.score}/100",
                        progress=100,
                        iteration=iteration,
                        data=self._format_final_result(enriched, review),
                    )
                    return
                
                if iteration == self.MAX_ITERATIONS:
                    yield V6Progress(
                        phase="complete",
                        step="max_iterations",
                        message=f"Best effort after {iteration} iterations (score: {review.score})",
                        progress=100,
                        iteration=iteration,
                        data=self._format_final_result(enriched, review),
                    )
                    return
                
                # Fix issues
                yield V6Progress(
                    phase="planner",
                    step="start",
                    message=f"Fixing {len(review.critical_issues)} critical issues...",
                    progress=base_progress + 12,
                    iteration=iteration,
                )
                
                revised_plan = await self.planner.revise_plan(enriched.plan, review, request)
                
                yield V6Progress(
                    phase="planner",
                    step="complete",
                    message=f"Revised: {revised_plan.route_string}",
                    progress=base_progress + 15,
                    iteration=iteration,
                    data={
                        "route": revised_plan.route_string,
                        "cities": revised_plan.city_names,
                    },
                )
                
                # Re-enrich
                yield V6Progress(
                    phase="enrich",
                    step="start",
                    message="Re-enriching revised plan...",
                    progress=base_progress + 17,
                    iteration=iteration,
                )
                
                enriched = await self.enricher.enrich_plan(revised_plan)
                
                yield V6Progress(
                    phase="enrich",
                    step="complete",
                    message=f"Enriched: {enriched.total_travel_hours:.1f}h total travel",
                    progress=base_progress + 20,
                    iteration=iteration,
                )
                
        except Exception as e:
            logger.error(f"[V6] Orchestration error: {e}", exc_info=True)
            yield V6Progress(
                phase="error",
                step="failed",
                message=f"Error: {str(e)}",
                progress=0,
                data={"error": str(e)},
            )
    
    def _format_final_result(self, enriched: EnrichedPlan, review: ReviewResult) -> dict:
        """Format final result for streaming."""
        plan = enriched.plan
        
        return {
            "theme": plan.theme,
            "summary": plan.summary,
            "route": plan.route_string,
            "total_days": plan.total_days,
            "total_travel_hours": enriched.total_travel_hours,
            "total_distance_km": enriched.total_distance_km,
            "review_score": review.score,
            "cities": [
                {
                    "name": city.name,
                    "country": city.country,
                    "days": city.days,
                    "why_visit": city.why_visit,
                    "highlights": [
                        {
                            "name": h.name,
                            "description": h.description,
                            "category": h.category,
                            "suggested_duration_hours": h.suggested_duration_hours,
                        }
                        for h in city.highlights
                    ],
                    "latitude": city.latitude,
                    "longitude": city.longitude,
                }
                for city in plan.cities
            ],
            "travel_legs": [
                {
                    "from_city": leg.from_city,
                    "to_city": leg.to_city,
                    "mode": leg.mode.value,
                    "duration_hours": leg.duration_hours,
                    "distance_km": leg.distance_km,
                    "notes": leg.notes,
                    "booking_tip": leg.booking_tip,
                }
                for leg in plan.travel_legs
            ],
        }
