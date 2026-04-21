"""Journey orchestrator — drives the Scout-Enrich-Review-Planner loop.

Yields ``ProgressEvent`` objects as an async generator so that callers
(SSE endpoints, websocket handlers, etc.) can stream incremental status
updates to the client.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

from app.agents.enricher import EnricherAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.scout import ScoutAgent
from app.models.journey import JourneyPlan, MustSeeAttractions, ReviewResult
from app.models.progress import ProgressEvent
from app.models.trip import TripRequest
from app.services.google.directions import GoogleDirectionsService
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.llm.base import LLMService
from app.services.llm.exceptions import LLMContentFilterError

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
        self.llm = llm
        self.places = places
        self.scout = ScoutAgent(llm)
        self.enricher = EnricherAgent(places, routes, directions)
        self.reviewer = ReviewerAgent(llm)
        self.planner = PlannerAgent(llm)
        self._landmarks_context = ""
        self._must_see_context = ""

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
            # ── Step 0: Discover destination landscape + must-see icons ──
            landscape_context = ""
            must_see_context = ""
            try:
                landscape_result, must_see_result = await asyncio.gather(
                    self.places.discover_destination_landscape(request.destination),
                    self._identify_must_see_attractions(request),
                    return_exceptions=True,
                )

                if isinstance(landscape_result, Exception):
                    logger.warning("[Orchestrator] Landscape discovery failed: %s", landscape_result)
                else:
                    landscape_context = landscape_result or ""
                    if landscape_context:
                        logger.info(
                            "[Orchestrator] Landscape discovered for %s",
                            request.destination,
                        )

                must_see_raw: MustSeeAttractions | None = None
                if isinstance(must_see_result, Exception):
                    logger.warning("[Orchestrator] Must-see identification failed: %s", must_see_result)
                    if request.must_include:
                        must_see_context = self._format_user_must_include_only(request.must_include)
                else:
                    must_see_context, must_see_raw = must_see_result if must_see_result else ("", None)
                    if must_see_context:
                        logger.info(
                            "[Orchestrator] Must-see attractions identified for %s",
                            request.destination,
                        )
            except Exception as exc:
                logger.warning("[Orchestrator] Step 0 failed: %s", exc)

            self._landmarks_context = landscape_context
            self._must_see_context = must_see_context

            # ── Step 0.5: Build geographic context from must-see cities ──
            geographic_context = ""
            if must_see_raw:
                try:
                    geographic_context = await self._build_geographic_context(
                        must_see_raw, request.origin
                    )
                except Exception as exc:
                    logger.warning("[Orchestrator] Geographic context failed: %s", exc)

            # ── Step 1: Scout ────────────────────────────────────────
            yield ProgressEvent(
                phase="scouting",
                message="Creating your journey...",
                progress=10,
            )
            logger.info("[Orchestrator] Scouting plan for %s", request.destination)
            plan: JourneyPlan = await self.scout.generate_plan(
                request,
                landmarks_context=self._landmarks_context,
                geographic_context=geographic_context,
            )
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
                review = await self.reviewer.review(plan, request, iteration, landmarks_context=self._landmarks_context, must_see_context=self._must_see_context)
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

                if (review.is_acceptable and review.score >= self.MIN_SCORE) or iteration == self.MAX_ITERATIONS:
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
                try:
                    plan = await self.planner.fix_plan(plan, review, request, landmarks_context=self._landmarks_context, must_see_context=self._must_see_context)
                except LLMContentFilterError:
                    logger.warning(
                        "[Orchestrator] Content filter blocked Planner (iteration %d) — using best plan so far (score %d)",
                        iteration, best_score,
                    )
                    break
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

    async def _identify_must_see_attractions(self, request: TripRequest) -> tuple[str, MustSeeAttractions | None]:
        """Identify globally iconic must-see attractions via a fast LLM call.

        Returns a formatted string for injection into Reviewer/Planner prompts.
        Merges LLM-identified attractions with user-specified must_include items.
        Returns empty string on failure (graceful degradation).
        """
        from app.config.planning import LLM_MUST_SEE_MAX_TOKENS, LLM_MUST_SEE_TEMPERATURE
        from app.prompts import journey_prompts

        try:
            system_prompt = journey_prompts.load("must_see_system")
            user_prompt = journey_prompts.load("must_see_user").format(
                destination=request.destination,
                total_days=request.total_days,
                interests=", ".join(request.interests) if request.interests else "general sightseeing",
            )

            from app.config.planning import should_use_search_grounding
            if should_use_search_grounding("full"):
                result, _citations = await self.llm.generate_structured_with_search(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=MustSeeAttractions,
                    max_tokens=LLM_MUST_SEE_MAX_TOKENS,
                    temperature=LLM_MUST_SEE_TEMPERATURE,
                )
            else:
                result = await self.llm.generate_structured(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=MustSeeAttractions,
                    max_tokens=LLM_MUST_SEE_MAX_TOKENS,
                    temperature=LLM_MUST_SEE_TEMPERATURE,
                )

            return (self._format_must_see_context(result, request.must_include), result)

        except Exception as exc:
            logger.warning("[Orchestrator] Must-see identification failed: %s", exc)
            if request.must_include:
                return (self._format_user_must_include_only(request.must_include), None)
            return ("", None)

    def _format_must_see_context(
        self, result: MustSeeAttractions, user_must_include: list[str]
    ) -> str:
        """Format must-see attractions as a prompt-ready string."""
        lines = [
            "## Must-See Iconic Attractions",
            "The following are globally iconic attractions for this destination.",
            "Check that the plan's experience themes would naturally lead travelers to these places:",
            "",
        ]

        llm_names_lower = set()
        for i, a in enumerate(result.attractions, 1):
            lines.append(
                f"{i}. **{a.name}** ({a.city_or_region}) — {a.why_iconic}"
            )
            llm_names_lower.add(a.name.lower())

        # Merge user-specified must_include, skipping duplicates
        if user_must_include:
            user_unique = [
                m for m in user_must_include
                if m.lower() not in llm_names_lower
            ]
            if user_unique:
                lines.append("")
                lines.append("**Traveler-specified must-sees (highest priority):**")
                for m in user_unique:
                    lines.append(f"- {m}")

        return "\n".join(lines)

    @staticmethod
    def _format_user_must_include_only(user_must_include: list[str]) -> str:
        """Format user must_include when LLM call fails."""
        lines = [
            "## Must-See Attractions",
            "**Traveler-specified must-sees (highest priority):**",
        ]
        for m in user_must_include:
            lines.append(f"- {m}")
        return "\n".join(lines)

    async def _build_geographic_context(
        self,
        must_see: MustSeeAttractions,
        origin: str,
    ) -> str:
        """Build geographic distance context from must-see city coordinates.

        Geocodes unique cities from must-see attractions plus the origin,
        computes pairwise haversine distances, and returns a nearest-neighbor
        ordering to help the Scout prevent backtracking routes.

        Returns empty string when insufficient cities are geocoded (< 3)
        or on any failure (graceful degradation).
        """
        from app.config.planning import compute_haversine_fallback

        # Extract unique city names, preserving order
        seen: set[str] = set()
        cities: list[str] = []
        if origin:
            cities.append(origin)
            seen.add(origin.lower())
        for a in must_see.attractions:
            key = a.city_or_region.lower()
            if key not in seen:
                cities.append(a.city_or_region)
                seen.add(key)

        if len(cities) < 3:
            return ""

        # Geocode all cities in parallel
        geocode_results = await asyncio.gather(
            *(self.places.geocode(city) for city in cities),
            return_exceptions=True,
        )

        # Build city→coords map, skip failures
        city_coords: dict[str, tuple[float, float]] = {}
        for city_name, result in zip(cities, geocode_results):
            if isinstance(result, Exception):
                logger.warning(
                    "[Orchestrator] Geocode failed for %r: %s", city_name, result
                )
                continue
            lat = result.get("lat", 0.0)
            lng = result.get("lng", 0.0)
            if lat and lng:
                city_coords[city_name] = (lat, lng)

        if len(city_coords) < 3:
            return ""

        # Compute pairwise distances (meters → km)
        city_names = list(city_coords.keys())
        distances: dict[tuple[str, str], float] = {}
        for i, c1 in enumerate(city_names):
            for c2 in city_names[i + 1 :]:
                lat1, lng1 = city_coords[c1]
                lat2, lng2 = city_coords[c2]
                dist_m, _ = compute_haversine_fallback(lat1, lng1, lat2, lng2)
                dist_km = dist_m / 1000
                distances[(c1, c2)] = dist_km
                distances[(c2, c1)] = dist_km

        # Nearest-neighbor ordering from origin (or first city)
        start = origin if origin in city_coords else city_names[0]
        ordered: list[str] = [start]
        remaining = set(city_names) - {start}
        while remaining:
            current = ordered[-1]
            nearest = min(
                remaining,
                key=lambda c: distances.get((current, c), float("inf")),
            )
            ordered.append(nearest)
            remaining.remove(nearest)

        # Format as compact context
        lines = [
            "## GEOGRAPHIC CONTEXT (from real coordinates)",
            "Approximate straight-line distances between key destinations in this region:",
            "",
            "**Efficient geographic flow** (minimizes total distance):",
        ]

        flow_parts = []
        total_km = 0.0
        for i in range(len(ordered) - 1):
            dist = distances.get((ordered[i], ordered[i + 1]), 0)
            total_km += dist
            flow_parts.append(f"{ordered[i]} →({dist:.0f}km)→ {ordered[i + 1]}")
        lines.append(" ".join(flow_parts))
        lines.append(f"Total: ~{total_km:.0f}km")
        lines.append("")

        lines.append("**Key distances:**")
        for i in range(len(ordered) - 1):
            c1, c2 = ordered[i], ordered[i + 1]
            dist = distances.get((c1, c2), 0)
            lines.append(f"- {c1} → {c2}: ~{dist:.0f}km")
        lines.append("")

        lines.append(
            "Follow this geographic flow to PREVENT backtracking. "
            "You may select different cities, but they should fit within "
            "this directional corridor (e.g., north-to-south, coastal sweep). "
            "Adding a city that forces doubling back is a routing error."
        )

        logger.info(
            "[Orchestrator] Geographic context: %s (total ~%.0fkm)",
            " → ".join(ordered),
            total_km,
        )

        return "\n".join(lines)
