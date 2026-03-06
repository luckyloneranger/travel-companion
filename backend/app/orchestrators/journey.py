"""Journey orchestrator — drives the Scout-Enrich-Review-Planner loop.

Yields ``ProgressEvent`` objects as an async generator so that callers
(SSE endpoints, websocket handlers, etc.) can stream incremental status
updates to the client.
"""

import logging
from collections.abc import AsyncGenerator

from app.agents.enricher import EnricherAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.scout import ScoutAgent
from app.models.journey import JourneyPlan, ReviewResult
from app.models.progress import ProgressEvent
from app.models.trip import TripRequest
from app.services.google.directions import GoogleDirectionsService
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class JourneyOrchestrator:
    """Orchestrates multi-city journey planning via an iterative loop.

    The pipeline follows:
        Scout (LLM) -> Enrich (Google APIs) -> Review (LLM)
        -> [Planner (LLM) -> Enrich -> Review] (repeat until acceptable)

    Parameters
    ----------
    llm:
        LLM service used by Scout, Reviewer, and Planner agents.
    places:
        Google Places service for geocoding and accommodation lookup.
    routes:
        Google Routes service for driving route computation.
    directions:
        Google Directions service for transit/ferry/driving routing.
    """

    MAX_ITERATIONS = 3
    MIN_SCORE = 70

    def __init__(
        self,
        llm: LLMService,
        places: GooglePlacesService,
        routes: GoogleRoutesService,
        directions: GoogleDirectionsService,
    ):
        from app.config.planning import MAX_JOURNEY_ITERATIONS, MIN_JOURNEY_SCORE
        self.MAX_ITERATIONS = MAX_JOURNEY_ITERATIONS
        self.MIN_SCORE = MIN_JOURNEY_SCORE
        self.places = places
        self.scout = ScoutAgent(llm)
        self.enricher = EnricherAgent(places, routes, directions)
        self.reviewer = ReviewerAgent(llm)
        self.planner = PlannerAgent(llm)
        self._landmarks_context = ""

    async def plan_stream(
        self, request: TripRequest
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Run the full journey-planning pipeline as an async generator.

        Yields ``ProgressEvent`` objects at each stage so the caller can
        relay progress to the client.  The final event has
        ``phase="complete"`` and carries the serialised ``JourneyPlan``
        in its ``data`` field.

        Args:
            request: Unified trip request describing destination, dates,
                     interests, pace, etc.

        Yields:
            ProgressEvent for scouting, enriching, reviewing, improving,
            complete, or error phases.
        """
        try:
            # ── Step 0: Discover landmarks ────────────────────────
            landmarks_section = ""
            try:
                landmarks = await self.places.discover_landmarks(request.destination)
                if landmarks:
                    lines = [
                        "## DESTINATION'S MOST POPULAR ATTRACTIONS (from Google, by visitor reviews)",
                        "You MUST consider including the top-ranked attractions in your highlights.",
                        "If you exclude a top-5 attraction, explain why in why_visit.\n",
                    ]
                    for i, lm in enumerate(landmarks):
                        reviews = lm.get("user_ratings_total", 0)
                        rating = lm.get("rating", 0)
                        name = lm.get("name", "")
                        lines.append(f"{i+1}. {name} ({rating}★, {reviews:,} reviews)")
                    landmarks_section = "\n".join(lines)
                    logger.info(
                        "[Orchestrator] Discovered %d landmarks for %s",
                        len(landmarks), request.destination,
                    )
            except Exception as exc:
                logger.warning("[Orchestrator] Landmark discovery failed: %s", exc)
            self._landmarks_context = landmarks_section

            # ── Step 1: Scout ────────────────────────────────────────
            yield ProgressEvent(
                phase="scouting",
                message="Creating your journey...",
                progress=10,
            )
            logger.info("[Orchestrator] Scouting plan for %s", request.destination)
            plan: JourneyPlan = await self.scout.generate_plan(request, landmarks_context=landmarks_section)
            yield ProgressEvent(
                phase="scouting",
                message=f"Planned {len(plan.cities)} cities",
                progress=20,
            )
            logger.info(
                "[Orchestrator] Scout produced %d cities: %s",
                len(plan.cities),
                plan.route or "no route",
            )

            # ── Step 2-4: Enrich-Review-[Fix] loop ──────────────────
            iteration = 1
            review: ReviewResult | None = None
            best_plan: JourneyPlan = plan
            best_score: int = 0

            while iteration <= self.MAX_ITERATIONS:
                # Enrich
                yield ProgressEvent(
                    phase="enriching",
                    message="Validating with real data...",
                    progress=30 + (iteration - 1) * 15,
                )
                logger.info(
                    "[Orchestrator] Enriching plan (iteration %d)", iteration
                )
                plan = await self.enricher.enrich_plan(
                    plan, budget_tier=request.budget.value
                )

                # Review
                yield ProgressEvent(
                    phase="reviewing",
                    message=f"Quality check (iteration {iteration})...",
                    progress=50 + (iteration - 1) * 15,
                )
                logger.info(
                    "[Orchestrator] Reviewing plan (iteration %d)", iteration
                )
                review = await self.reviewer.review(plan, request, iteration, landmarks_context=self._landmarks_context)
                plan.review_score = review.score
                logger.info(
                    "[Orchestrator] Review score: %d (acceptable=%s, iteration=%d)",
                    review.score,
                    review.is_acceptable,
                    iteration,
                )

                # Track best plan across all iterations
                if review.score >= best_score:
                    best_score = review.score
                    best_plan = plan

                if review.is_acceptable or iteration == self.MAX_ITERATIONS:
                    break

                # Fix with Planner
                yield ProgressEvent(
                    phase="improving",
                    message=f"Improving plan (score: {review.score})...",
                    progress=60 + (iteration - 1) * 15,
                )
                logger.info(
                    "[Orchestrator] Planner fixing plan (score %d, iteration %d)",
                    review.score,
                    iteration,
                )
                plan = await self.planner.fix_plan(plan, review, request, landmarks_context=self._landmarks_context)
                iteration += 1

            # Use the best plan seen across all iterations
            plan = best_plan

            # ── Complete ─────────────────────────────────────────────
            score_display = plan.review_score if plan.review_score is not None else "N/A"
            yield ProgressEvent(
                phase="complete",
                message=f"Journey planned! Score: {score_display}",
                progress=100,
                data=plan.model_dump(),
            )
            logger.info(
                "[Orchestrator] Journey planning complete — score: %s",
                score_display,
            )

        except Exception as exc:
            logger.exception("[Orchestrator] Journey planning failed: %s", exc)
            yield ProgressEvent(
                phase="error",
                message=str(exc),
                progress=0,
            )
