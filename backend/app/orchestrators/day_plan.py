"""Day plan orchestrator — generates detailed day plans for all cities in a journey.

Pipeline per city:
1. Discover places via Google Places API
2. AI Plan — LLM selects and groups into themed days
3. Optimize — TSP route optimization per day
4. Schedule — deterministic time-slot assignment
5. Bookend — add hotel departure/return if accommodation exists
6. Compute routes between consecutive activities via Routes API
"""

import logging
from collections.abc import AsyncGenerator
from datetime import timedelta

from app.agents.day_planner import DayPlannerAgent
from app.algorithms.scheduler import ScheduleBuilder
from app.algorithms.tsp import RouteOptimizer, haversine_distance
from app.models.common import Location, Pace
from app.models.day_plan import Activity, DayPlan, Place, Route
from app.models.internal import PlaceCandidate
from app.models.journey import JourneyPlan
from app.models.progress import ProgressEvent
from app.models.trip import TripRequest
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayPlanOrchestrator:
    """Orchestrates day plan generation for all cities in a journey.

    Combines LLM intelligence (place selection, theming) with deterministic
    layers (TSP optimization, schedule building, route computation).

    Parameters
    ----------
    llm:
        LLM service for the day planner agent.
    places:
        Google Places service for discovering candidate places.
    routes:
        Google Routes service for computing travel routes.
    """

    def __init__(
        self,
        llm: LLMService,
        places: GooglePlacesService,
        routes: GoogleRoutesService,
    ):
        self.day_planner = DayPlannerAgent(llm)
        self.places = places
        self.routes = routes
        self.optimizer = RouteOptimizer()
        self.scheduler = ScheduleBuilder()

    async def generate_stream(
        self,
        journey: JourneyPlan,
        request: TripRequest,
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Generate day plans for all cities in the journey.

        Yields ProgressEvents as each city is planned. The final event
        contains all day plans.

        Args:
            journey: The journey plan with cities and accommodation info.
            request: The original trip request with interests, pace, dates.

        Yields:
            ProgressEvent instances with phase, message, progress, and data.
        """
        all_plans: list[DayPlan] = []
        total_cities = len(journey.cities)
        day_offset = 0  # cumulative days across all cities for correct dates

        try:
            for city_idx, city in enumerate(journey.cities):
                city_name = city.name
                pct_start = int((city_idx / total_cities) * 100)
                pct_end = int(((city_idx + 1) / total_cities) * 100)

                yield ProgressEvent(
                    phase="city_start",
                    message=f"Planning {city_name}...",
                    progress=pct_start,
                    data={"city": city_name},
                )

                # ----------------------------------------------------------
                # 1. Discover places
                # ----------------------------------------------------------
                if city.location is None:
                    logger.warning(
                        "[DayPlanOrchestrator] City %s has no location, skipping",
                        city_name,
                    )
                    day_offset += city.days
                    continue

                try:
                    candidates = await self.places.discover_places(
                        location=city.location,
                        interests=request.interests,
                    )
                except Exception as exc:
                    logger.error(
                        "[DayPlanOrchestrator] Place discovery failed for %s: %s",
                        city_name,
                        exc,
                    )
                    day_offset += city.days
                    yield ProgressEvent(
                        phase="city_complete",
                        message=f"{city_name}: place discovery failed",
                        progress=pct_end,
                        data={"city": city_name, "day_plans": []},
                    )
                    continue

                if not candidates:
                    logger.warning(
                        "[DayPlanOrchestrator] No candidates found for %s, skipping",
                        city_name,
                    )
                    day_offset += city.days
                    yield ProgressEvent(
                        phase="city_complete",
                        message=f"{city_name}: no places found",
                        progress=pct_end,
                        data={"city": city_name, "day_plans": []},
                    )
                    continue

                # ----------------------------------------------------------
                # 2. AI Plan — LLM selects + groups into themed days
                # ----------------------------------------------------------
                try:
                    ai_plan = await self.day_planner.plan_days(
                        candidates=candidates,
                        city_name=city_name,
                        num_days=city.days,
                        interests=request.interests,
                        pace=request.pace.value,
                    )
                except Exception as exc:
                    logger.error(
                        "[DayPlanOrchestrator] AI planning failed for %s: %s",
                        city_name,
                        exc,
                    )
                    day_offset += city.days
                    yield ProgressEvent(
                        phase="city_complete",
                        message=f"{city_name}: AI planning failed",
                        progress=pct_end,
                        data={"city": city_name, "day_plans": []},
                    )
                    continue

                # Build a lookup of candidates by place_id
                candidate_map: dict[str, PlaceCandidate] = {
                    c.place_id: c for c in candidates
                }

                # Determine start location (hotel if available)
                start_location: Location | None = None
                if (
                    city.accommodation
                    and city.accommodation.location
                ):
                    start_location = city.accommodation.location

                # ----------------------------------------------------------
                # 3. Process each day group
                # ----------------------------------------------------------
                city_plans: list[DayPlan] = []

                for day_idx, group in enumerate(ai_plan.day_groups):
                    # a. Filter candidates to selected places for this day
                    day_candidates = [
                        candidate_map[pid]
                        for pid in group.place_ids
                        if pid in candidate_map
                    ]

                    if not day_candidates:
                        logger.warning(
                            "[DayPlanOrchestrator] No valid candidates for %s day %d, skipping",
                            city_name,
                            day_idx + 1,
                        )
                        city_plans.append(
                            DayPlan(
                                date=str(
                                    request.start_date
                                    + timedelta(days=day_offset + day_idx)
                                ),
                                day_number=day_offset + day_idx + 1,
                                theme=group.theme,
                                activities=[],
                                city_name=city_name,
                            )
                        )
                        continue

                    # b. Optimize — TSP route optimization
                    optimized = self.optimizer.optimize_day(
                        activities=day_candidates,
                        distance_fn=haversine_distance,
                        start_location=start_location,
                        preserve_order=True,
                    )

                    # c. Schedule — deterministic time slot assignment
                    schedule_date = request.start_date + timedelta(
                        days=day_offset + day_idx
                    )
                    activities = self.scheduler.build_schedule(
                        places=optimized,
                        pace=request.pace,
                        durations=ai_plan.durations,
                        start_location=start_location,
                        schedule_date=schedule_date,
                    )

                    # d. Bookend — add hotel departure/return
                    if start_location is not None and city.accommodation:
                        activities = self._bookend_with_hotel(
                            activities=activities,
                            accommodation_name=city.accommodation.name,
                            accommodation_location=start_location,
                            accommodation_place_id=city.accommodation.place_id,
                        )

                    # e. Compute routes between consecutive activities
                    activities = await self._compute_activity_routes(
                        activities, request.travel_mode
                    )

                    city_plans.append(
                        DayPlan(
                            date=str(schedule_date),
                            day_number=day_offset + day_idx + 1,
                            theme=group.theme,
                            activities=activities,
                            city_name=city_name,
                        )
                    )

                all_plans.extend(city_plans)
                day_offset += city.days

                yield ProgressEvent(
                    phase="city_complete",
                    message=f"{city_name} planned",
                    progress=pct_end,
                    data={
                        "city": city_name,
                        "day_plans": [dp.model_dump() for dp in city_plans],
                    },
                )

            # Final event with all day plans
            yield ProgressEvent(
                phase="complete",
                message="All day plans generated",
                progress=100,
                data={
                    "day_plans": [dp.model_dump() for dp in all_plans],
                },
            )

        except Exception as exc:
            logger.error(
                "[DayPlanOrchestrator] Unexpected error: %s", exc, exc_info=True
            )
            yield ProgressEvent(
                phase="error",
                message=f"Day plan generation failed: {exc}",
                progress=0,
                data=None,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _bookend_with_hotel(
        self,
        activities: list[Activity],
        accommodation_name: str,
        accommodation_location: Location,
        accommodation_place_id: str | None = None,
    ) -> list[Activity]:
        """Add zero-duration accommodation activities at start and end of day.

        Args:
            activities: The day's scheduled activities.
            accommodation_name: Hotel/accommodation name.
            accommodation_location: Hotel location.
            accommodation_place_id: Optional place ID for the accommodation.

        Returns:
            Activities list with hotel departure prepended and hotel return
            appended.
        """
        if not activities:
            return activities

        hotel_place = Place(
            place_id=accommodation_place_id or "accommodation",
            name=accommodation_name,
            address="",
            location=accommodation_location,
            category="lodging",
        )

        # Departure: starts at day start time, zero duration
        first_start = activities[0].time_start
        departure = Activity(
            time_start=first_start,
            time_end=first_start,
            duration_minutes=0,
            place=hotel_place,
            notes="Depart from hotel",
        )

        # Return: starts at last activity end, zero duration
        last_end = activities[-1].time_end
        arrival = Activity(
            time_start=last_end,
            time_end=last_end,
            duration_minutes=0,
            place=hotel_place,
            notes="Return to hotel",
        )

        return [departure] + activities + [arrival]

    async def _compute_activity_routes(
        self,
        activities: list[Activity],
        travel_mode,
    ) -> list[Activity]:
        """Compute routes between consecutive activities via the Routes API.

        Adds ``route_to_next`` to each activity except the last one.

        Args:
            activities: Ordered list of activities for a day.
            travel_mode: Travel mode (WALK, DRIVE, TRANSIT).

        Returns:
            The same activities list with route_to_next populated.
        """
        if len(activities) < 2:
            return activities

        # Build origin-destination pairs
        pairs: list[tuple[Location, Location]] = []
        for i in range(len(activities) - 1):
            origin = activities[i].place.location
            destination = activities[i + 1].place.location
            pairs.append((origin, destination))

        try:
            routes = await self.routes.compute_routes_batch(
                pairs=pairs,
                mode=travel_mode,
            )

            for i, route in enumerate(routes):
                activities[i].route_to_next = route

        except Exception as exc:
            logger.warning(
                "[DayPlanOrchestrator] Route computation failed: %s", exc
            )
            # Activities remain without route_to_next — non-fatal

        return activities
