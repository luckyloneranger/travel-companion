"""Fast itinerary generator - the main orchestrator for FAST mode.

This is the FAST mode generator that creates itineraries quickly using
a single-pass AI approach. For higher quality itineraries with iterative
refinement, see the PristineItineraryGenerator in app.agents.orchestrator.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional, Self
from uuid import uuid4

from app.config.tuning import FAST_MODE, DISCOVERY
from app.core import services
from app.models import (
    Activity,
    DayPlan,
    Destination,
    ItineraryRequest,
    ItineraryResponse,
    Place,
    PlaceCandidate,
    Route,
    Summary,
    TravelMode,
    TripDates,
)
from app.generators.day_plan.fast.ai_service import FastAIService
from app.services.internal.route_optimizer import RouteOptimizer
from app.services.internal.schedule_builder import ScheduleBuilder

logger = logging.getLogger(__name__)

# Type alias for async progress callback
ProgressCallback = Callable[[str, str, int, Optional[dict]], Awaitable[None]]


class FastItineraryGenerator:
    """Fast mode itinerary generator service.
    
    Combines AI and deterministic services to generate itineraries quickly
    in a single pass. For iterative refinement, use PristineItineraryGenerator.
    
    Configuration is loaded from app.config.tuning.FAST_MODE.
    Uses shared services from core.services registry.
    """

    def __init__(self):
        """Initialize the generator with shared services."""
        self.ai = FastAIService()
        self.places = services.get_places()
        self.routes = services.get_routes()
        self.optimizer = RouteOptimizer(self.routes)
        self.scheduler = ScheduleBuilder()

        # Cache for place details
        self._place_cache: dict[str, PlaceCandidate] = {}
        
        # Configuration
        self.config = FAST_MODE

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # No-op: services.close_all() handles cleanup at app shutdown
        pass

    async def close(self) -> None:
        """Close method for backward compatibility.
        
        Note: Actual cleanup handled by services.close_all() at app shutdown.
        """
        pass

    async def generate(
        self, 
        request: ItineraryRequest, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> ItineraryResponse:
        """
        Generate a complete itinerary following the hybrid AI + deterministic approach.

        Phases:
        1. Data Gathering (Deterministic) - Google Places
        2. AI Selection & Grouping (Creative) - Azure OpenAI
        3. Route Optimization (Deterministic) - TSP Algorithm
        4. Schedule Building (Deterministic) - Time slots
        
        Note: Tips are generated on-demand via separate /tips endpoint.
        """
        logger.info(f"[FAST] Generating itinerary for {request.destination}")
        
        async def report_progress(phase: str, message: str, progress: int, data: Optional[dict] = None):
            """Helper to report progress if callback exists."""
            if progress_callback:
                await progress_callback(phase, message, progress, data)

        # ═══════════════════════════════════════════════════════════
        # PHASE 1: DATA GATHERING (Deterministic)
        # ═══════════════════════════════════════════════════════════

        # 1. Geocode destination
        await report_progress("geocoding", f"Finding {request.destination} on the map...", 5)
        logger.info("Phase 1: Geocoding destination...")
        destination = await self.places.geocode(request.destination)
        logger.info(f"Destination: {destination.name} at {destination.location}")
        await report_progress("geocoding", f"Found {destination.name}", 10, {"destination": destination.name})

        # 2. Discover candidate places
        await report_progress("discovery", "Discovering interesting places nearby...", 15)
        logger.info("Phase 1: Discovering candidate places...")
        candidates = await self.places.discover_places(
            location=destination.location,
            interests=request.interests,
            radius_km=DISCOVERY.default_radius_km,
        )
        logger.info(f"Found {len(candidates)} candidate places")
        await report_progress("discovery", f"Found {len(candidates)} places to consider", 25, {"places_found": len(candidates)})

        # Cache candidates for later lookup
        for c in candidates:
            self._place_cache[c.place_id] = c

        # ═══════════════════════════════════════════════════════════
        # PHASE 2: AI SELECTION & GROUPING (Creative)
        # ═══════════════════════════════════════════════════════════

        num_days = (request.end_date - request.start_date).days + 1
        await report_progress("planning", f"AI is crafting your {num_days}-day adventure...", 30)
        logger.info(f"Phase 2: AI planning for {num_days} days...")

        # Build context strings for prompt enrichment
        destination_name = destination.name
        travel_dates_str = f"{request.start_date} to {request.end_date}"

        ai_plan = await self.ai.select_and_group_places(
            candidates=candidates,
            interests=request.interests,
            num_days=num_days,
            pace=request.pace,
            destination=destination_name,
            travel_dates=travel_dates_str,
        )
        logger.info(
            f"AI selected {len(ai_plan.selected_place_ids)} places in {len(ai_plan.day_groups)} days"
        )
        await report_progress("planning", f"Selected {len(ai_plan.selected_place_ids)} amazing places", 45)

        # ═══════════════════════════════════════════════════════════
        # PHASE 2.5: AI VALIDATION & REFINEMENT (Quality Check)
        # Only run if enabled in config
        # ═══════════════════════════════════════════════════════════
        
        if self.config.enable_validation_pass:
            try:
                await report_progress("validation", "Reviewing and optimizing the plan...", 50)
                logger.info("Phase 2.5: AI validation and refinement...")
                refined_plan = await self.ai.validate_and_refine_plan(
                    plan=ai_plan,
                    candidates=candidates,
                    num_days=num_days,
                    destination=destination_name,
                    interests=", ".join(request.interests),
                    pace=request.pace.value if hasattr(request.pace, 'value') else str(request.pace),
                    travel_dates=travel_dates_str,
                )
                # Only use refined plan if it has valid day_groups
                if refined_plan.day_groups and all(g.place_ids for g in refined_plan.day_groups):
                    ai_plan = refined_plan
                    logger.info(f"Using refined plan: {len(ai_plan.selected_place_ids)} places")
                    await report_progress("validation", "Plan optimized for the best experience", 55)
                else:
                    logger.info("Refined plan invalid, keeping original")
            except Exception as e:
                logger.warning(f"Validation skipped: {e}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 3 & 4: ROUTE OPTIMIZATION + SCHEDULE BUILDING
        # ═══════════════════════════════════════════════════════════

        # Apply LLM-estimated durations to cached places
        if ai_plan.durations:
            for place_id, duration in ai_plan.durations.items():
                if place_id in self._place_cache:
                    self._place_cache[place_id].suggested_duration_minutes = duration
            logger.info(f"Applied {len(ai_plan.durations)} LLM duration estimates to places")

        await report_progress("routing", "Calculating optimal routes between places...", 60)
        
        days = []
        total_distance = 0
        total_activities = 0
        num_total_days = len(ai_plan.day_groups)

        for day_idx, day_group in enumerate(ai_plan.day_groups):
            current_date = request.start_date + timedelta(days=day_idx)
            logger.info(f"Phase 3-4: Processing Day {day_idx + 1} ({current_date})...")
            
            # Calculate progress within routing phase (60-80%)
            routing_progress = 60 + int((day_idx / num_total_days) * 20)
            await report_progress(
                "routing", 
                f"Building Day {day_idx + 1} schedule...", 
                routing_progress,
                {"day": day_idx + 1, "total_days": num_total_days}
            )

            # Get places for this day
            day_places = [
                self._place_cache[pid]
                for pid in day_group.place_ids
                if pid in self._place_cache
            ]

            if not day_places:
                logger.warning(f"No valid places for day {day_idx + 1}")
                continue

            # Calculate route metrics (preserving AI's logical order)
            # The AI validation step has already ordered places appropriately
            logger.info(f"  Calculating routes for {len(day_places)} places...")
            optimization = await self.optimizer.optimize_day(
                day_places, 
                preserve_order=self.config.preserve_ai_order,
            )
            optimized_places = optimization.places
            total_distance += optimization.total_distance_meters

            # Calculate routes between consecutive places
            logger.info("  Calculating routes...")
            routes = await self.routes.compute_routes_batch(
                [p.location for p in optimized_places],
                mode=request.travel_mode,
            )

            # Build time-slotted schedule
            logger.info("  Building schedule...")
            scheduled = self.scheduler.build_schedule(
                places=optimized_places,
                routes=routes,
                schedule_date=current_date,
                pace=request.pace,
            )

            # Convert to Activity objects
            activities = []
            for i, item in enumerate(scheduled):
                route_to_next = routes[i] if i < len(routes) else None

                activities.append(
                    Activity(
                        id=str(uuid4()),
                        time_start=item.start_time,
                        time_end=item.end_time,
                        duration_minutes=item.duration_minutes,
                        place=self._candidate_to_place(item.place),
                        notes="",  # Tips generated on-demand
                        route_to_next=route_to_next,
                    )
                )

            total_activities += len(activities)

            days.append(
                DayPlan(
                    date=current_date,
                    day_number=day_idx + 1,
                    theme=day_group.theme,
                    activities=activities,
                )
            )

        # ═══════════════════════════════════════════════════════════
        # ASSEMBLE FINAL RESPONSE
        # ═══════════════════════════════════════════════════════════
        
        await report_progress("finalizing", "Putting it all together...", 95)
        logger.info("Assembling final response...")

        return ItineraryResponse(
            id=str(uuid4()),
            destination=destination,
            trip_dates=TripDates(
                start=request.start_date,
                end=request.end_date,
                duration_days=num_days,
            ),
            days=days,
            summary=Summary(
                total_activities=total_activities,
                total_distance_km=round(total_distance / 1000, 1),
                interests_covered=request.interests,
                estimated_cost_range=self._estimate_cost(days),
            ),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _candidate_to_place(self, candidate: PlaceCandidate) -> Place:
        """Convert a PlaceCandidate to a finalized Place."""
        # Get primary category from types
        category = "attraction"
        priority_types = [
            "museum",
            "art_gallery",
            "restaurant",
            "cafe",
            "park",
            "church",
            "bar",
            "shopping_mall",
            "tourist_attraction",
        ]
        for ptype in priority_types:
            if ptype in candidate.types:
                category = ptype
                break

        # Generate photo URL if available
        photo_url = None
        if candidate.photo_reference:
            photo_url = self.places.get_photo_url(candidate.photo_reference)

        # Format opening hours as strings
        opening_hours_str = None
        if candidate.opening_hours:
            days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            opening_hours_str = [
                f"{days[h.day]}: {h.open_time} - {h.close_time}"
                for h in candidate.opening_hours
            ]

        return Place(
            place_id=candidate.place_id,
            name=candidate.name,
            address=candidate.address,
            location=candidate.location,
            category=category,
            rating=candidate.rating,
            photo_url=photo_url,
            opening_hours=opening_hours_str,
        )

    def _estimate_cost(self, days: list[DayPlan]) -> str:
        """Estimate cost range based on activities."""
        # Simple heuristic based on number of activities
        total = sum(len(day.activities) for day in days)
        num_days = len(days)

        # Rough estimates per day
        low = num_days * 50 + total * 10  # Budget traveler
        high = num_days * 150 + total * 30  # Moderate spender

        return f"${low}-${high}"
