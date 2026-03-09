"""Day plan orchestrator — generates detailed day plans for all cities in a journey.

Pipeline per city:
1. Discover places via Google Places API
2. AI Plan — LLM selects and groups into themed days
3. Optimize — TSP route optimization per day
4. Schedule — deterministic time-slot assignment
5. Bookend — add hotel departure/return if accommodation exists
6. Compute routes between consecutive activities via Routes API
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import time, timedelta

from app.agents.day_fixer import DayFixerAgent
from app.agents.day_planner import DayPlannerAgent
from app.agents.day_reviewer import DayReviewerAgent
from app.agents.day_scout import DayScoutAgent
from app.algorithms.scheduler import ScheduleBuilder, ScheduleConfig
from app.algorithms.tsp import RouteOptimizer, haversine_distance
from app.models.common import Location, Pace, TravelMode
from app.models.day_plan import Activity, DayPlan, Place, Route, Weather
from app.models.internal import PlaceCandidate
from app.models.journey import CityHighlight, JourneyPlan
from app.models.progress import ProgressEvent
from app.models.trip import TripRequest
from app.services.google.directions import GoogleDirectionsService
from app.services.google.places import GooglePlacesService
from app.services.google.routes import GoogleRoutesService
from app.services.google.weather import GoogleWeatherService, WeatherForecast
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
        directions: GoogleDirectionsService | None = None,
        weather: GoogleWeatherService | None = None,
        day_scout: DayScoutAgent | None = None,
        day_reviewer: DayReviewerAgent | None = None,
        day_fixer: DayFixerAgent | None = None,
    ):
        self.day_planner = DayPlannerAgent(llm)
        self.day_scout = day_scout or DayScoutAgent(llm)
        self.day_reviewer = day_reviewer or DayReviewerAgent(llm)
        self.day_fixer = day_fixer or DayFixerAgent(llm)
        self.places = places
        self.routes = routes
        self.directions = directions
        self.weather = weather
        self.optimizer = RouteOptimizer()
        self.scheduler = ScheduleBuilder()
        self._route_cache: dict[tuple, Route] = {}
        self._landmark_cache: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # Excursion scheduling helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_excursions(
        highlights: list[CityHighlight],
        experience_themes: list | None = None,
    ) -> list[CityHighlight]:
        """Extract excursion items from experience_themes (preferred) or highlights."""
        if experience_themes:
            excursions = []
            for et in experience_themes:
                if et.excursion_type:
                    excursions.append(CityHighlight(
                        name=et.theme,
                        description=et.why,
                        category=et.category,
                        destination_name=et.destination_name,
                        excursion_type=et.excursion_type,
                        excursion_days=et.excursion_days,
                    ))
            return excursions
        return [h for h in highlights if h.excursion_type is not None]

    @staticmethod
    def _build_excursion_day_plan(
        excursion: CityHighlight,
        date_str: str,
        day_number: int,
        city_name: str,
        day_label: str = "",
    ) -> DayPlan:
        """Build a pre-built DayPlan for an excursion day.

        Args:
            excursion: The CityHighlight representing the excursion.
            date_str: ISO date string for this day.
            day_number: 1-based day number across the entire trip.
            city_name: Name of the city this excursion belongs to.
            day_label: Optional label like "Day 1 of 2" for multi-day excursions.

        Returns:
            A DayPlan with is_excursion=True and a single all-day activity.
        """
        excursion_name = (
            f"{excursion.name} — {day_label}" if day_label else excursion.name
        )

        place = Place(
            place_id=f"excursion-{excursion.name.lower().replace(' ', '-')}",
            name=excursion.name,
            location=Location(lat=0, lng=0),
            category=excursion.category or "excursion",
        )

        notes = excursion.description or "Full-day experience"
        notes += " — explore at your own pace, no rigid schedule needed."

        activity = Activity(
            time_start="09:00",
            time_end="18:00",
            duration_minutes=540,
            place=place,
            notes=notes,
        )

        return DayPlan(
            date=date_str,
            day_number=day_number,
            theme=excursion.name,
            activities=[activity],
            city_name=city_name,
            is_excursion=True,
            excursion_name=excursion_name,
        )

    async def _plan_excursion_days(
        self,
        excursions_by_day: dict[int, CityHighlight],
        city: "CityStop",
        request: "TripRequest",
        day_offset: int,
    ) -> list["DayPlan"]:
        """Plan excursion days in parallel."""
        # Group excursions by name (multi-day -> single group)
        exc_groups: dict[str, tuple[CityHighlight, list[int]]] = {}
        for day_idx, exc in sorted(excursions_by_day.items()):
            key = exc.name
            if key not in exc_groups:
                exc_groups[key] = (exc, [])
            exc_groups[key][1].append(day_idx)

        # Process all excursion groups in parallel
        tasks = [
            self._plan_single_excursion(exc, days, city, request, day_offset)
            for exc, days in exc_groups.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results, build fallback stubs for failures
        planned: list[DayPlan] = []
        group_items = list(exc_groups.values())
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                exc, days = group_items[i]
                logger.error(
                    "[DayPlanOrchestrator] Excursion %r failed: %s", exc.name, r,
                )
                for di in days:
                    schedule_date = request.start_date + timedelta(days=day_offset + di)
                    planned.append(self._build_excursion_day_plan(
                        excursion=exc,
                        date_str=str(schedule_date),
                        day_number=day_offset + di + 1,
                        city_name=city.name,
                    ))
            else:
                planned.extend(r)

        return planned

    async def _plan_single_excursion(
        self,
        exc: CityHighlight,
        exc_day_indices: list[int],
        city: "CityStop",
        request: "TripRequest",
        day_offset: int,
    ) -> list["DayPlan"]:
        """Plan a single excursion group (one or more days for the same destination).

        This is the per-excursion body extracted from _plan_excursion_days for
        parallel execution via asyncio.gather().

        Args:
            exc: The excursion CityHighlight.
            exc_day_indices: Day indices within the city stay for this excursion.
            city: The CityStop this excursion belongs to.
            request: Original TripRequest for interests, pace, dates, etc.
            day_offset: Cumulative day offset across all cities.

        Returns:
            List of DayPlan objects for this excursion group.
        """
        from app.config.planning import (
            MAX_DAY_PLAN_ITERATIONS, MIN_DAY_PLAN_SCORE,
        )
        from app.agents.day_planner import _build_meal_time_guidance
        from app.models.internal import AIPlan

        result: list[DayPlan] = []

        # 1. Geocode the excursion destination
        geocode_name = exc.destination_name or exc.name
        try:
            geo = await self.places.geocode(f"{geocode_name}, {city.country or ''}")
            exc_location = Location(lat=geo["lat"], lng=geo["lng"])
            logger.info(
                "[DayPlanOrchestrator] Geocoded excursion %r -> %.4f, %.4f",
                geocode_name, geo["lat"], geo["lng"],
            )
        except Exception as e:
            logger.warning(
                "[DayPlanOrchestrator] Geocoding failed for excursion %r: %s — "
                "falling back to placeholder", exc.name, e,
            )
            for di in exc_day_indices:
                schedule_date = request.start_date + timedelta(days=day_offset + di)
                if exc.excursion_type == "multi_day":
                    multi_pos = exc_day_indices.index(di) + 1
                    day_label = f"Day {multi_pos} of {len(exc_day_indices)}"
                else:
                    day_label = ""
                result.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                    day_label=day_label,
                ))
            return result

        # 2. Discover places at the excursion destination
        try:
            exc_candidates = await self.places.discover_places(
                location=exc_location,
                interests=request.interests,
            )
        except Exception as e:
            logger.warning(
                "[DayPlanOrchestrator] Place discovery failed for excursion %r: %s",
                exc.name, e,
            )
            exc_candidates = []

        # 3. Discover landmarks at the excursion destination
        exc_landmarks: list[dict] = []
        try:
            exc_landmarks = await self.places.discover_landmarks(geocode_name)
            # Merge landmark PlaceCandidates into candidates
            if exc_landmarks:
                existing_ids = {c.place_id for c in exc_candidates}
                valid_landmarks = [lm for lm in exc_landmarks[:7] if lm.get("name")]

                async def _search_exc_lm(lm_name: str):
                    try:
                        return await self.places.text_search_places(
                            query=f"{lm_name} {geocode_name}",
                            location=exc_location,
                            max_results=1,
                        )
                    except Exception:
                        return []

                exc_lm_results = await asyncio.gather(
                    *(_search_exc_lm(lm["name"]) for lm in valid_landmarks)
                )
                for lm_results in exc_lm_results:
                    for lc in lm_results:
                        if lc.place_id not in existing_ids:
                            exc_candidates.append(lc)
                            existing_ids.add(lc.place_id)
        except Exception as e:
            logger.warning(
                "[DayPlanOrchestrator] Landmark discovery failed for excursion %r: %s",
                exc.name, e,
            )

        if not exc_candidates:
            logger.warning(
                "[DayPlanOrchestrator] No candidates for excursion %r, using placeholder",
                exc.name,
            )
            for di in exc_day_indices:
                schedule_date = request.start_date + timedelta(days=day_offset + di)
                if exc.excursion_type == "multi_day":
                    multi_pos = exc_day_indices.index(di) + 1
                    day_label = f"Day {multi_pos} of {len(exc_day_indices)}"
                else:
                    day_label = ""
                result.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                    day_label=day_label,
                ))
            return result

        # Resolve photo references
        for c in exc_candidates:
            if c.photo_references:
                c.photo_references = [
                    self.places.get_photo_url(ref) for ref in c.photo_references
                ]
            if c.photo_reference:
                c.photo_reference = self.places.get_photo_url(c.photo_reference)

        # 4. Estimate transit time from distance_from_city_km
        transit_hours_one_way = 1.0  # default 1h
        dist_km = getattr(exc, 'distance_from_city_km', None)
        if dist_km:
            transit_hours_one_way = max(0.5, dist_km / 50)

        # 5. Build experience theme for the batch
        from app.models.journey import ExperienceTheme
        exc_theme = ExperienceTheme(
            theme=exc.name,
            category=exc.category or "excursion",
            why=exc.description or f"Day trip to {exc.name}",
        )

        # 6. Run Day Scout for each excursion day
        meal_guidance = _build_meal_time_guidance(city.country or "")

        # Format landmarks for prompts
        landmarks_section = ""
        if exc_landmarks:
            lines = ["TOP LANDMARKS by visitor reviews (include at least one per batch):"]
            for lm in exc_landmarks[:5]:
                lines.append(f"- {lm.get('name')} ({lm.get('user_ratings_total', 0):,} reviews)")
            landmarks_section = "\n".join(lines)

        batch_themes = {
            exc_day_indices[i] + 1: [exc_theme]
            for i in range(len(exc_day_indices))
        }

        try:
            batch_plan = await self.day_scout.plan_batch(
                candidates=exc_candidates,
                batch_themes=batch_themes,
                destination=exc.name,
                pace=request.pace.value,
                landmarks=exc_landmarks if exc_landmarks else None,
                already_used=set(),
                meal_time_guidance=meal_guidance,
                travelers_description=request.travelers.summary,
            )
        except Exception as e:
            logger.error(
                "[DayPlanOrchestrator] Day Scout failed for excursion %r: %s",
                exc.name, e,
            )
            for di in exc_day_indices:
                schedule_date = request.start_date + timedelta(days=day_offset + di)
                result.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                ))
            return result

        # 7. Quality loop: Day Reviewer -> Day Fixer
        themes_text = ""
        for d, themes in sorted(batch_themes.items()):
            theme_names = ", ".join(t.theme for t in themes)
            themes_text += f"Day {d}: {theme_names}\n"

        for iteration in range(MAX_DAY_PLAN_ITERATIONS):
            plan_detail = ""
            batch_day_nums = sorted(batch_themes.keys())
            for i, group in enumerate(batch_plan.day_groups):
                day_num = batch_day_nums[i] if i < len(batch_day_nums) else i + 1
                place_names = []
                for pid in group.place_ids:
                    name = next(
                        (c.name for c in exc_candidates if c.place_id == pid),
                        pid,
                    )
                    dur = batch_plan.durations.get(pid, "?")
                    place_names.append(f"{name} ({dur}min)")
                plan_detail += f"Day {day_num} ({group.theme}): {', '.join(place_names)}\n"

            try:
                review = await self.day_reviewer.review_batch(
                    day_plans_detail=plan_detail,
                    batch_themes=themes_text,
                    landmarks_section=landmarks_section,
                    destination=exc.name,
                )
            except Exception:
                break

            logger.info(
                "[DayPlanOrchestrator] Excursion %r review score: %d (acceptable=%s, iter=%d)",
                exc.name, review.score, review.is_acceptable, iteration + 1,
            )

            if review.is_acceptable and review.score >= MIN_DAY_PLAN_SCORE:
                break

            try:
                batch_plan = await self.day_fixer.fix_batch(
                    current_plan=batch_plan,
                    issues=review.issues,
                    candidates=exc_candidates,
                    destination=exc.name,
                    already_used=set(),
                )
            except Exception:
                break

        # 8. Convert AIPlan to DayPlan objects (TSP, schedule, routes, weather)
        candidate_map = {c.place_id: c for c in exc_candidates}

        # Weather for excursion location
        exc_weather: dict[str, object] = {}
        if self.weather and exc_location:
            try:
                forecasts = await self.weather.get_daily_forecast(exc_location, days=10)
                exc_weather = {str(f.date): f for f in forecasts}
            except Exception:
                pass

        for i, group in enumerate(batch_plan.day_groups):
            if i >= len(exc_day_indices):
                break
            di = exc_day_indices[i]
            schedule_date = request.start_date + timedelta(days=day_offset + di)

            day_candidates = [
                candidate_map[pid]
                for pid in group.place_ids
                if pid in candidate_map
            ]

            if not day_candidates:
                result.append(self._build_excursion_day_plan(
                    excursion=exc,
                    date_str=str(schedule_date),
                    day_number=day_offset + di + 1,
                    city_name=city.name,
                ))
                continue

            # TSP optimize
            optimized = self.optimizer.optimize_day(
                activities=day_candidates,
                distance_fn=haversine_distance,
                start_location=exc_location,
                preserve_order=True,
            )

            # Schedule with adjusted times for transit
            transit_minutes = int(transit_hours_one_way * 60)
            base_start_hour = 9
            adjusted_start_minutes = (base_start_hour * 60) + transit_minutes
            adjusted_end_minutes = (21 * 60) - transit_minutes

            from datetime import time as dt_time
            day_start_time = dt_time(
                hour=min(adjusted_start_minutes // 60, 23),
                minute=adjusted_start_minutes % 60,
            )
            day_end_time = dt_time(
                hour=min(adjusted_end_minutes // 60, 23),
                minute=adjusted_end_minutes % 60,
            )

            activities = self.scheduler.build_schedule(
                places=optimized,
                pace=request.pace,
                durations=batch_plan.durations,
                start_location=exc_location,
                schedule_date=schedule_date,
                day_start_time=day_start_time,
                day_end_time=day_end_time,
                cost_estimates=batch_plan.cost_estimates,
                country=city.country,
            )

            # No hotel bookends for excursion days — traveler is in transit

            # Compute routes
            activities = await self._compute_routes_via_matrix(
                activities, pace=request.pace,
            )

            # Weather
            day_weather = None
            forecast = exc_weather.get(str(schedule_date))
            if forecast:
                day_weather = Weather(
                    temperature_high_c=forecast.temperature_high_c,
                    temperature_low_c=forecast.temperature_low_c,
                    condition=forecast.condition,
                    precipitation_chance_percent=forecast.precipitation_chance_percent,
                    wind_speed_kmh=forecast.wind_speed_kmh,
                    humidity_percent=forecast.humidity_percent,
                    uv_index=forecast.uv_index,
                )
                activities = self._add_weather_warnings(activities, forecast)

            daily_cost = sum(
                a.estimated_cost_usd for a in activities
                if a.estimated_cost_usd is not None
            )

            result.append(DayPlan(
                date=str(schedule_date),
                day_number=day_offset + di + 1,
                theme=group.theme,
                activities=activities,
                city_name=city.name,
                weather=day_weather,
                daily_cost_usd=daily_cost if daily_cost > 0 else None,
                is_excursion=True,
                excursion_name=exc.name,
            ))

        return result

    @staticmethod
    def _compute_excursion_schedule(
        excursions: list[CityHighlight],
        num_days: int,
    ) -> tuple[dict[int, CityHighlight], dict[int, CityHighlight]]:
        """Compute which days are blocked or partially blocked by excursions.

        Multi-day excursions are placed at the END of the city stay.
        Full-day excursions are placed at the end of remaining days.
        Half-day and evening excursions are placed on the earliest free days.

        Args:
            excursions: List of excursion CityHighlights.
            num_days: Total number of days in this city stay.

        Returns:
            A tuple of (blocked, partial) where both map day_index to the
            excursion CityHighlight occupying that day.
        """
        blocked: dict[int, CityHighlight] = {}
        partial: dict[int, CityHighlight] = {}

        # First pass: multi-day (placed at end)
        next_blocked_from_end = num_days - 1
        for exc in excursions:
            if exc.excursion_type == "multi_day":
                days_needed = exc.excursion_days or 2
                for d in range(days_needed):
                    idx = next_blocked_from_end - (days_needed - 1 - d)
                    if 0 <= idx < num_days:
                        blocked[idx] = exc
                next_blocked_from_end -= days_needed

        # Second pass: full-day (placed at end of remaining)
        for exc in excursions:
            if exc.excursion_type == "full_day":
                while next_blocked_from_end in blocked and next_blocked_from_end >= 0:
                    next_blocked_from_end -= 1
                if next_blocked_from_end >= 0:
                    blocked[next_blocked_from_end] = exc
                    next_blocked_from_end -= 1

        # Third pass: half-day/evening on earliest free days
        free_days = sorted(i for i in range(num_days) if i not in blocked)
        partial_excs = [
            e
            for e in excursions
            if e.excursion_type in ("half_day_morning", "half_day_afternoon", "evening")
        ]
        for exc, day_idx in zip(partial_excs, free_days):
            partial[day_idx] = exc

        return blocked, partial

    async def generate_stream(
        self,
        journey: JourneyPlan,
        request: TripRequest,
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Generate day plans for all cities in the journey, processing cities in parallel.

        Cities are processed concurrently (bounded by MAX_CONCURRENT_CITIES).
        Each city pushes SSE events to a shared queue for real-time streaming.
        Failed cities retry once; if still failing, emit city_error event.

        Args:
            journey: The journey plan with cities and accommodation info.
            request: The original trip request with interests, pace, dates.

        Yields:
            ProgressEvent instances with phase, message, progress, and data.
        """
        from app.config.settings import get_settings

        event_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        total_cities = len(journey.cities)
        max_concurrent = get_settings().max_concurrent_cities

        async def _run_all_cities():
            sem = asyncio.Semaphore(max_concurrent)

            async def _bounded_city(city_idx: int, city):
                async with sem:
                    return await self._process_city(
                        city_idx, city, journey, request,
                        event_queue, total_cities,
                    )

            results = await asyncio.gather(
                *(_bounded_city(i, c) for i, c in enumerate(journey.cities)),
                return_exceptions=True,
            )
            await event_queue.put(None)  # Sentinel
            return results

        try:
            producer = asyncio.create_task(_run_all_cities())

            # Stream events in real-time as cities produce them
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event

            # Collect results, retry failures once
            results = await producer
            all_plans: list[DayPlan] = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    city = journey.cities[i]
                    logger.error(
                        "[DayPlanOrchestrator] City %s failed: %s",
                        city.name, r,
                    )
                    # Retry once
                    try:
                        retry_plans = await self._process_city(
                            i, city, journey, request,
                            event_queue, total_cities,
                        )
                        all_plans.extend(retry_plans)
                    except Exception as e2:
                        logger.error(
                            "[DayPlanOrchestrator] City %s retry failed: %s",
                            city.name, e2,
                        )
                        yield ProgressEvent(
                            phase="city_error",
                            message=f"Failed to plan {city.name}. You can regenerate day plans to try again.",
                            data={"city": city.name},
                        )
                else:
                    all_plans.extend(r)

            # Drain any retry progress events
            while not event_queue.empty():
                event = await event_queue.get()
                if event is not None:
                    yield event

            all_plans.sort(key=lambda dp: dp.day_number)

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

    async def _process_city(
        self,
        city_idx: int,
        city,
        journey: JourneyPlan,
        request: TripRequest,
        event_queue: asyncio.Queue,
        total_cities: int,
    ) -> list[DayPlan]:
        """Process a single city's day plan generation.

        Extracted from the generate_stream loop body to enable parallel
        city processing. All progress events are pushed to event_queue
        instead of being yielded directly.

        Args:
            city_idx: Index of this city in journey.cities.
            city: The CityStop to process.
            journey: The full journey plan.
            request: The original trip request.
            event_queue: Queue for pushing ProgressEvent instances.
            total_cities: Total number of cities (for progress calculation).

        Returns:
            List of DayPlan instances for this city.
        """
        # Compute day_offset locally (no shared state)
        day_offset = sum(journey.cities[i].days for i in range(city_idx))

        # Clear route cache for each new city
        self._route_cache.clear()

        city_name = city.name
        pct_start = int((city_idx / total_cities) * 100)
        pct_end = int(((city_idx + 1) / total_cities) * 100)
        city_plans: list[DayPlan] = []

        await event_queue.put(ProgressEvent(
            phase="city_start",
            message=f"Planning {city_name}...",
            progress=pct_start,
            data={"city": city_name},
        ))

        # ----------------------------------------------------------
        # 0. Handle excursions
        # ----------------------------------------------------------
        excursions = self._extract_excursions(
            city.highlights,
            experience_themes=city.experience_themes if city.experience_themes else None,
        )
        blocked_days: dict[int, CityHighlight] = {}
        partial_days: dict[int, CityHighlight] = {}
        excursion_plans: list[DayPlan] = []

        if excursions:
            blocked_days, partial_days = self._compute_excursion_schedule(
                excursions, city.days,
            )
            await event_queue.put(ProgressEvent(
                phase="city_progress",
                message=f"Planning excursions from {city_name}...",
                progress=pct_start,
                data={"city": city_name},
            ))
            excursion_plans = await self._plan_excursion_days(
                excursions_by_day=blocked_days,
                city=city,
                request=request,
                day_offset=day_offset,
            )
            logger.info(
                "[DayPlanOrchestrator] %s: %d excursion days planned (%d partial)",
                city_name, len(blocked_days), len(partial_days),
            )

        free_day_count = city.days - len(blocked_days)

        # If ALL days are excursions, skip discovery + planning
        if free_day_count <= 0:
            city_plans = sorted(excursion_plans, key=lambda dp: dp.day_number)
            await event_queue.put(ProgressEvent(
                phase="city_complete",
                message=f"{city_name} planned (excursions only)",
                progress=pct_end,
                data={
                    "city": city_name,
                    "day_plans": [dp.model_dump() for dp in excursion_plans],
                },
            ))
            return city_plans

        # ----------------------------------------------------------
        # 1. Discover places
        # ----------------------------------------------------------
        if city.location is None or (abs(city.location.lat) < 0.01 and abs(city.location.lng) < 0.01):
            logger.warning(
                "[DayPlanOrchestrator] City %s has no valid location, skipping",
                city_name,
            )
            await event_queue.put(ProgressEvent(
                phase="city_complete",
                message=f"{city_name}: could not locate on map — try a different spelling or check the city name",
                progress=pct_end,
                data={"city": city_name, "day_plans": []},
            ))
            return city_plans

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
            await event_queue.put(ProgressEvent(
                phase="city_complete",
                message=f"{city_name}: place discovery failed",
                progress=pct_end,
                data={"city": city_name, "day_plans": []},
            ))
            return city_plans

        # Supplement with text searches for journey highlights
        if city.highlights:
            highlight_candidates = await self._discover_highlights(
                city.highlights, city_name, city.location
            )
            if highlight_candidates:
                # Merge, deduplicating by place_id
                existing_ids = {c.place_id for c in candidates}
                for hc in highlight_candidates:
                    if hc.place_id not in existing_ids:
                        candidates.append(hc)
                        existing_ids.add(hc.place_id)

        # Per-city landmark discovery (top attractions by review count)
        try:
            if city_name in self._landmark_cache:
                city_landmarks = self._landmark_cache[city_name]
            else:
                city_landmarks = await self.places.discover_landmarks(city_name)
                self._landmark_cache[city_name] = city_landmarks
            if city_landmarks:
                existing_ids = {c.place_id for c in candidates}

                async def _search_lm(lm_name: str):
                    try:
                        return await self.places.text_search_places(
                            query=f"{lm_name} {city_name}",
                            location=city.location,
                            max_results=1,
                        )
                    except Exception:
                        return []

                lm_results_all = await asyncio.gather(
                    *(_search_lm(lm["name"]) for lm in city_landmarks)
                )
                for lm_results in lm_results_all:
                    for lc in lm_results:
                        if lc.place_id not in existing_ids:
                            candidates.append(lc)
                            existing_ids.add(lc.place_id)
                logger.info(
                    "[DayPlanOrchestrator] Added landmark candidates for %s",
                    city_name,
                )
        except Exception as exc:
            logger.warning("[DayPlanOrchestrator] Landmark discovery failed for %s: %s", city_name, exc)

        # Theme-based discovery for far excursions
        if city.experience_themes:
            existing_ids = {c.place_id for c in candidates}
            far_themes = [
                et for et in city.experience_themes
                if et.distance_from_city_km and et.distance_from_city_km > 20
            ]
            if far_themes:
                async def _search_theme(theme_name: str):
                    try:
                        return await self.places.text_search_places(
                            query=f"{theme_name} near {city_name}",
                            location=city.location,
                            max_results=3,
                        )
                    except Exception:
                        return []

                theme_results_all = await asyncio.gather(
                    *(_search_theme(et.theme) for et in far_themes)
                )
                for theme_results in theme_results_all:
                    for tr in theme_results:
                        if tr.place_id not in existing_ids:
                            candidates.append(tr)
                            existing_ids.add(tr.place_id)

        # Resolve photo references to full URLs
        for c in candidates:
            if c.photo_references:
                c.photo_references = [
                    self.places.get_photo_url(ref) for ref in c.photo_references
                ]
            if c.photo_reference:
                c.photo_reference = self.places.get_photo_url(c.photo_reference)

        if not candidates:
            logger.warning(
                "[DayPlanOrchestrator] No candidates found for %s, skipping",
                city_name,
            )
            await event_queue.put(ProgressEvent(
                phase="city_complete",
                message=f"{city_name}: no suitable places found — try adjusting interests or pace",
                progress=pct_end,
                data={"city": city_name, "day_plans": []},
            ))
            return city_plans

        await event_queue.put(ProgressEvent(
            phase="city_progress",
            message=f"Discovered {len(candidates)} places in {city_name}",
            progress=pct_start + (pct_end - pct_start) // 4,
            data={"city": city_name},
        ))

        # ----------------------------------------------------------
        # 2. AI Plan — LLM selects + groups into themed days
        # ----------------------------------------------------------
        # Compute time constraints for arrival/departure days
        time_constraints: list[dict] = []
        for d_idx in range(city.days):
            day_start, day_end = self._get_day_time_bounds(
                journey, city_idx, d_idx, city.days
            )
            if day_start or day_end:
                start_h = day_start.hour + day_start.minute / 60 if day_start else 9.0
                end_h = day_end.hour + day_end.minute / 60 if day_end else 21.0
                available = end_h - start_h
                reason = ""
                if day_start and day_start.hour > 9:
                    reason = "arrival day — sightseeing starts later"
                if day_end and day_end.hour < 21:
                    reason = "departure day — need to leave early"
                if reason:
                    time_constraints.append({
                        "day_num": d_idx + 1,
                        "reason": reason,
                        "available_hours": available,
                    })

        # Add time constraints from partial excursions (half-day/evening)
        for d_idx, exc in partial_days.items():
            if exc.excursion_type == "half_day_morning":
                time_constraints.append({
                    "day_num": d_idx + 1,
                    "reason": f"{exc.name} (morning excursion)",
                    "available_hours": 5,
                })
            elif exc.excursion_type == "half_day_afternoon":
                time_constraints.append({
                    "day_num": d_idx + 1,
                    "reason": f"{exc.name} (afternoon excursion)",
                    "available_hours": 4,
                })
            elif exc.excursion_type == "evening":
                time_constraints.append({
                    "day_num": d_idx + 1,
                    "reason": f"{exc.name} (evening excursion)",
                    "available_hours": 8,
                })

        ai_plan = None

        # -- Batched pipeline (when experience_themes available) --
        if city.experience_themes:
            try:
                # Per-city landmark data for batch prompts (candidates already merged above)
                city_landmarks: list[dict] = []
                try:
                    if city_name in self._landmark_cache:
                        city_landmarks = self._landmark_cache[city_name]
                    else:
                        city_landmarks = await self.places.discover_landmarks(city_name)
                        self._landmark_cache[city_name] = city_landmarks
                except Exception:
                    pass

                ai_plan = await self._plan_city_batched(
                    city=city,
                    candidates=candidates,
                    free_day_count=free_day_count,
                    blocked_days=blocked_days,
                    request=request,
                    landmarks=city_landmarks,
                    city_name=city_name,
                    time_constraints=time_constraints,
                )
            except Exception as exc:
                logger.error(
                    "[DayPlanOrchestrator] Batched planning failed for %s, "
                    "falling back to single-shot: %s",
                    city_name, exc,
                )
                ai_plan = None  # fall through to single-shot

        # -- Single-shot planning (fallback / no experience_themes) --
        if ai_plan is None:
            from app.services.llm.exceptions import LLMValidationError
            try:
                ai_plan = await self.day_planner.plan_days(
                    candidates=candidates,
                    city_name=city_name,
                    num_days=free_day_count,
                    interests=request.interests,
                    pace=request.pace.value,
                    budget=request.budget.value if hasattr(request, 'budget') else "moderate",
                    daily_budget_usd=(request.budget_usd / request.total_days) if request.budget_usd else None,
                    must_include=request.must_include if request.must_include else None,
                    time_constraints=time_constraints if time_constraints else None,
                    travelers_description=request.travelers.summary,
                    country=city.country or "",
                    highlights=city.highlights if city.highlights else None,
                    best_time_to_visit=city.best_time_to_visit or "",
                    hotel_location=city.accommodation.location if city.accommodation and city.accommodation.location else None,
                    experience_themes=city.experience_themes if city.experience_themes else None,
                )
            except LLMValidationError:
                logger.warning(
                    "[DayPlanOrchestrator] Validation failed for %s, retrying...",
                    city_name,
                )
                try:
                    ai_plan = await self.day_planner.plan_days(
                        candidates=candidates,
                        city_name=city_name,
                        num_days=free_day_count,
                        interests=request.interests,
                        pace=request.pace.value,
                        budget=request.budget.value if hasattr(request, 'budget') else "moderate",
                        daily_budget_usd=(request.budget_usd / request.total_days) if request.budget_usd else None,
                        must_include=request.must_include if request.must_include else None,
                        time_constraints=time_constraints if time_constraints else None,
                        travelers_description=request.travelers.summary,
                        country=city.country or "",
                        highlights=city.highlights if city.highlights else None,
                        best_time_to_visit=city.best_time_to_visit or "",
                        hotel_location=city.accommodation.location if city.accommodation and city.accommodation.location else None,
                        experience_themes=city.experience_themes if city.experience_themes else None,
                    )
                except (LLMValidationError, Exception) as exc:
                    logger.error(
                        "[DayPlanOrchestrator] AI planning failed for %s after retry: %s",
                        city_name, exc,
                    )
                    await event_queue.put(ProgressEvent(
                        phase="city_complete",
                        message=f"{city_name}: AI planning failed",
                        progress=pct_end,
                        data={"city": city_name, "day_plans": []},
                    ))
                    return city_plans
            except Exception as exc:
                logger.error(
                    "[DayPlanOrchestrator] AI planning failed for %s: %s",
                    city_name, exc,
                )
                await event_queue.put(ProgressEvent(
                    phase="city_complete",
                    message=f"{city_name}: AI planning failed",
                    progress=pct_end,
                    data={"city": city_name, "day_plans": []},
                ))
                return city_plans

        await event_queue.put(ProgressEvent(
            phase="city_progress",
            message=f"Building itinerary for {city_name}...",
            progress=pct_start + (pct_end - pct_start) // 2,
            data={"city": city_name},
        ))

        # Build a lookup of candidates by place_id
        candidate_map: dict[str, PlaceCandidate] = {
            c.place_id: c for c in candidates
        }

        # Determine start location (hotel if available, fallback to city center)
        start_location: Location | None = None
        if (
            city.accommodation
            and city.accommodation.location
        ):
            start_location = city.accommodation.location
        elif city.accommodation and city.location:
            # Accommodation exists but wasn't geocoded — use city center
            logger.info(
                "[DayPlanOrchestrator] %s: accommodation has no location, "
                "falling back to city center for bookends",
                city_name,
            )
            start_location = city.location

        # ----------------------------------------------------------
        # 3. Fetch weather forecast for this city
        # ----------------------------------------------------------
        city_weather: dict[str, WeatherForecast] = {}
        if self.weather and city.location:
            try:
                forecasts = await self.weather.get_daily_forecast(
                    city.location, days=10
                )
                city_weather = {str(f.date): f for f in forecasts}
                if city_weather and len(city_weather) < city.days:
                    logger.info(
                        "[DayPlanOrchestrator] Weather covers %d/%d days for %s (API limit)",
                        len(city_weather), city.days, city_name,
                    )
            except Exception as exc:
                logger.warning(
                    "[DayPlanOrchestrator] Weather fetch failed for %s: %s",
                    city_name,
                    exc,
                )

        # ----------------------------------------------------------
        # 4. Process each day group
        # ----------------------------------------------------------

        for day_idx, group in enumerate(ai_plan.day_groups):
            # Determine arrival/departure time adjustments
            day_start_time, day_end_time = self._get_day_time_bounds(
                journey, city_idx, day_idx, city.days
            )

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
                day_start_time=day_start_time,
                day_end_time=day_end_time,
                cost_estimates=ai_plan.cost_estimates,
                country=city.country,
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
            activities = await self._compute_routes_via_matrix(
                activities, pace=request.pace,
            )

            # f. Attach weather and add warnings to outdoor activities
            day_weather: Weather | None = None
            forecast = city_weather.get(str(schedule_date))
            if forecast:
                day_weather = Weather(
                    temperature_high_c=forecast.temperature_high_c,
                    temperature_low_c=forecast.temperature_low_c,
                    condition=forecast.condition,
                    precipitation_chance_percent=forecast.precipitation_chance_percent,
                    wind_speed_kmh=forecast.wind_speed_kmh,
                    humidity_percent=forecast.humidity_percent,
                    uv_index=forecast.uv_index,
                )
                activities = self._add_weather_warnings(activities, forecast)

            # g. Aggregate daily cost
            daily_cost = sum(
                a.estimated_cost_usd for a in activities
                if a.estimated_cost_usd is not None
            )

            # Budget warning
            if request.budget_usd and request.total_days:
                daily_budget = request.budget_usd / request.total_days
                if daily_cost > 0 and daily_cost > daily_budget * 1.2:
                    logger.warning(
                        "[DayPlanOrchestrator] %s day %d: estimated cost $%.0f exceeds "
                        "daily budget $%.0f by %.0f%%",
                        city_name, day_idx + 1, daily_cost, daily_budget,
                        ((daily_cost / daily_budget) - 1) * 100,
                    )

            city_plans.append(
                DayPlan(
                    date=str(schedule_date),
                    day_number=day_offset + day_idx + 1,
                    theme=group.theme,
                    activities=activities,
                    city_name=city_name,
                    weather=day_weather,
                    daily_cost_usd=daily_cost if daily_cost > 0 else None,
                )
            )

        await event_queue.put(ProgressEvent(
            phase="city_progress",
            message=f"Finalizing routes for {city_name}...",
            progress=pct_start + 3 * (pct_end - pct_start) // 4,
            data={"city": city_name},
        ))

        # Merge excursion plans with city plans
        if excursion_plans:
            city_plans.extend(excursion_plans)
            city_plans.sort(key=lambda dp: dp.day_number)

        await event_queue.put(ProgressEvent(
            phase="city_complete",
            message=f"{city_name} planned",
            progress=pct_end,
            data={
                "city": city_name,
                "day_plans": [dp.model_dump() for dp in city_plans],
            },
        ))

        return city_plans

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_day_time_bounds(
        self,
        journey: JourneyPlan,
        city_idx: int,
        day_idx: int,
        city_days: int,
    ) -> tuple[time | None, time | None]:
        """Determine custom start/end times for arrival and departure days.

        For the first day in a city (except the first city), if
        there's an incoming travel leg with significant duration, the
        schedule starts later to account for travel.

        For the last day in a city (except the last city), if there's
        an outgoing travel leg, the schedule ends earlier to allow
        packing, checkout, and transit to the station/airport.

        Returns:
            (day_start_time, day_end_time) — None means use default.
        """
        day_start_time: time | None = None
        day_end_time: time | None = None

        # --- Arrival day: first day in this city (not the first city) ---
        if day_idx == 0 and city_idx > 0:
            incoming_leg = self._find_incoming_leg(journey, city_idx)
            if incoming_leg and incoming_leg.duration_hours >= 2:
                # Parse explicit arrival_time if available
                if incoming_leg.arrival_time:
                    try:
                        parts = incoming_leg.arrival_time.split(":")
                        arr_hour = int(parts[0])
                        arr_min = int(parts[1]) if len(parts) > 1 else 0
                        # Add 1 hour buffer for settling in
                        settle_hour = min(arr_hour + 1, 20)
                        day_start_time = time(settle_hour, arr_min)
                    except (ValueError, IndexError):
                        pass

                # Fallback: estimate arrival from 9:00 departure + duration
                if day_start_time is None:
                    estimated_arrival_hour = 9 + incoming_leg.duration_hours + 1  # +1h settle
                    estimated_arrival_hour = min(estimated_arrival_hour, 20)
                    day_start_time = time(int(estimated_arrival_hour), 0)

                logger.info(
                    "[DayPlanOrchestrator] Arrival day for %s: "
                    "schedule starts at %s (travel: %.1fh)",
                    journey.cities[city_idx].name,
                    day_start_time.strftime("%H:%M"),
                    incoming_leg.duration_hours,
                )

        # --- Departure day: last day in this city (not the last city) ---
        if day_idx == city_days - 1 and city_idx < len(journey.cities) - 1:
            outgoing_leg = self._find_outgoing_leg(journey, city_idx)
            if outgoing_leg and outgoing_leg.duration_hours >= 2:
                # If departure_time is explicit, end 2 hours before
                if outgoing_leg.departure_time:
                    try:
                        parts = outgoing_leg.departure_time.split(":")
                        dep_hour = int(parts[0])
                        dep_min = int(parts[1]) if len(parts) > 1 else 0
                        end_hour = max(dep_hour - 2, 12)
                        day_end_time = time(end_hour, dep_min)
                    except (ValueError, IndexError):
                        pass

                # Fallback: end at 16:00 to allow afternoon departure
                if day_end_time is None:
                    day_end_time = time(16, 0)

                logger.info(
                    "[DayPlanOrchestrator] Departure day from %s: "
                    "schedule ends at %s (travel: %.1fh)",
                    journey.cities[city_idx].name,
                    day_end_time.strftime("%H:%M"),
                    outgoing_leg.duration_hours,
                )

        # Guard: if both set and start >= end (e.g. single-day intermediate
        # city), reset to defaults to avoid empty schedules.
        if day_start_time and day_end_time and day_start_time >= day_end_time:
            logger.warning(
                "[DayPlanOrchestrator] start %s >= end %s for city_idx=%d "
                "day=%d, resetting to defaults",
                day_start_time, day_end_time, city_idx, day_idx,
            )
            return None, None

        return day_start_time, day_end_time

    @staticmethod
    def _find_incoming_leg(
        journey: JourneyPlan, city_idx: int
    ):
        """Find the travel leg arriving at the given city."""
        city_name = journey.cities[city_idx].name.lower()
        for leg in journey.travel_legs:
            if leg.to_city.lower() == city_name:
                return leg
        return None

    @staticmethod
    def _find_outgoing_leg(
        journey: JourneyPlan, city_idx: int
    ):
        """Find the travel leg departing from the given city."""
        city_name = journey.cities[city_idx].name.lower()
        for leg in journey.travel_legs:
            if leg.from_city.lower() == city_name:
                return leg
        return None

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
        pace: Pace = Pace.MODERATE,
    ) -> list[Activity]:
        """Compute routes between consecutive activities.

        For each leg, queries WALK and DRIVE via the Routes API (and TRANSIT
        via the Directions API when available) in parallel, then picks the
        best mode based on actual travel times from Google:

        - Walk <= 20 min → walk (short, pleasant, no parking)
        - Walk <= 1.5× the fastest alternative → walk
        - Otherwise → whichever of drive/transit is fastest

        Args:
            activities: Ordered list of activities for a day.

        Returns:
            The same activities list with route_to_next populated.
        """
        if len(activities) < 2:
            return activities

        tasks = [
            self._compute_best_route_for_leg(
                activities[i].place.location,
                activities[i + 1].place.location,
                pace=pace,
            )
            for i in range(len(activities) - 1)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        "[DayPlanOrchestrator] Route computation failed for leg %d: %s",
                        i, result,
                    )
                else:
                    activities[i].route_to_next = result
        except Exception as exc:
            logger.warning(
                "[DayPlanOrchestrator] Route computation failed: %s", exc
            )

        return activities

    async def _compute_routes_via_matrix(
        self,
        activities: list[Activity],
        pace: Pace = Pace.MODERATE,
    ) -> list[Activity]:
        """Compute routes using distance matrix for mode selection + individual calls for polylines.

        Phase 1: 3 matrix calls (WALK, DRIVE, TRANSIT) to get distance/duration for all legs.
        Phase 2: Pick best mode per leg, then fetch polyline with 1 compute_route call per leg.

        This uses ~8 API calls per day instead of ~15 (47% reduction).
        """
        if len(activities) < 2:
            return activities

        locations = [a.place.location for a in activities]
        origins = locations[:-1]
        destinations = locations[1:]
        n_legs = len(origins)

        # Phase 1: 3 matrix calls in parallel
        matrices = await asyncio.gather(
            self.routes.get_distance_matrix(origins, destinations, TravelMode.WALK),
            self.routes.get_distance_matrix(origins, destinations, TravelMode.DRIVE),
            self.routes.get_distance_matrix(origins, destinations, TravelMode.TRANSIT),
            return_exceptions=True,
        )

        # Phase 2: Pick best mode per leg, fetch polyline for selected mode only
        tasks: list[asyncio.Task | None] = []
        selected_modes: list[TravelMode] = []

        for i in range(n_legs):
            cache_key = (
                round(origins[i].lat, 5), round(origins[i].lng, 5),
                round(destinations[i].lat, 5), round(destinations[i].lng, 5),
            )
            if cache_key in self._route_cache:
                tasks.append(None)
                selected_modes.append(TravelMode.WALK)  # placeholder, won't be used
            else:
                best_mode = self._pick_best_mode_from_matrix(matrices, i, pace=pace)
                selected_modes.append(best_mode)
                tasks.append(
                    asyncio.ensure_future(
                        self.routes.compute_route(origins[i], destinations[i], best_mode)
                    )
                )

        # Gather polyline fetches
        actual_tasks = [t for t in tasks if t is not None]
        if actual_tasks:
            fetched = await asyncio.gather(*actual_tasks, return_exceptions=True)
        else:
            fetched = []

        fetch_idx = 0
        for i in range(n_legs):
            cache_key = (
                round(origins[i].lat, 5), round(origins[i].lng, 5),
                round(destinations[i].lat, 5), round(destinations[i].lng, 5),
            )
            if cache_key in self._route_cache:
                activities[i].route_to_next = self._route_cache[cache_key]
            else:
                if fetch_idx < len(fetched):
                    result = fetched[fetch_idx]
                    fetch_idx += 1
                    if isinstance(result, Exception):
                        logger.warning(
                            "[DayPlanOrchestrator] Route fetch failed for leg %d: %s",
                            i, result,
                        )
                        activities[i].route_to_next = self.routes._fallback_route(TravelMode.WALK)
                    else:
                        self._route_cache[cache_key] = result
                        activities[i].route_to_next = result

        return activities

    async def _compute_best_route_for_leg(
        self,
        origin: Location,
        destination: Location,
        pace: Pace = Pace.MODERATE,
    ) -> Route:
        """Query WALK, DRIVE, and TRANSIT via Routes API in parallel, pick the best."""
        # Check route cache
        cache_key = (
            round(origin.lat, 5), round(origin.lng, 5),
            round(destination.lat, 5), round(destination.lng, 5),
        )
        if cache_key in self._route_cache:
            return self._route_cache[cache_key]

        walk_task = self.routes.compute_route(origin, destination, TravelMode.WALK)
        drive_task = self.routes.compute_route(origin, destination, TravelMode.DRIVE)
        transit_task = self.routes.compute_route(origin, destination, TravelMode.TRANSIT)

        results = await asyncio.gather(
            walk_task, drive_task, transit_task, return_exceptions=True
        )

        # Collect successful routes
        candidates: list[Route] = []
        for r in results:
            if not isinstance(r, Exception):
                candidates.append(r)

        if not candidates:
            return self.routes._fallback_route(TravelMode.WALK)

        result = self._pick_best_route(candidates, pace=pace)
        self._route_cache[cache_key] = result
        return result

    @staticmethod
    def _walk_threshold_seconds(pace: Pace) -> int:
        """Return walk preference threshold based on pace.

        Relaxed travelers are happy to walk further; packed pace users
        prefer faster transport to maximize sightseeing time.
        """
        return {
            Pace.RELAXED: 1500,   # 25 min
            Pace.MODERATE: 1200,  # 20 min
            Pace.PACKED: 900,     # 15 min
        }.get(pace, 1200)

    @staticmethod
    def _walk_multiplier(pace: Pace) -> float:
        """Return walk-vs-transit acceptance multiplier based on pace.

        Higher multiplier means more willingness to walk even if transit
        is faster. Relaxed travelers tolerate 2x transit time walking.
        """
        return {
            Pace.RELAXED: 2.0,
            Pace.MODERATE: 1.5,
            Pace.PACKED: 1.2,
        }.get(pace, 1.5)

    @classmethod
    def _pick_best_route(cls, candidates: list[Route], pace: Pace = Pace.MODERATE) -> Route:
        """Pick the best route from candidates using actual Google travel times.

        Priority:
        1. Walk if <= 20 min (short, pleasant, no waiting/parking)
        2. Walk if <= 1.5× the fastest alternative (close enough)
        3. Otherwise the fastest option (transit or drive)
        """
        walk = next((r for r in candidates if r.travel_mode == TravelMode.WALK), None)
        others = [r for r in candidates if r.travel_mode != TravelMode.WALK]
        fastest_other = min(others, key=lambda r: r.duration_seconds) if others else None

        if walk:
            threshold = cls._walk_threshold_seconds(pace)
            multiplier = cls._walk_multiplier(pace)
            # Short walk — always prefer
            if walk.duration_seconds <= threshold:
                return walk
            # Walk is only slightly slower than fastest alternative
            if fastest_other and walk.duration_seconds <= fastest_other.duration_seconds * multiplier:
                return walk

        # Return the fastest overall
        return min(candidates, key=lambda r: r.duration_seconds)

    @classmethod
    def _pick_best_mode_from_matrix(
        cls,
        matrices: list,
        leg_index: int,
        pace: Pace = Pace.MODERATE,
    ) -> TravelMode:
        """Pick best travel mode for a leg using matrix distance/duration data.

        Uses same heuristics as _pick_best_route: prefer walk if short or
        close to fastest alternative.
        """
        modes = [TravelMode.WALK, TravelMode.DRIVE, TravelMode.TRANSIT]
        candidates: list[tuple[TravelMode, int]] = []

        for mode, matrix_result in zip(modes, matrices):
            if isinstance(matrix_result, Exception):
                continue
            try:
                rows = matrix_result.get("rows", [])
                if leg_index < len(rows):
                    elements = rows[leg_index].get("elements", [])
                    if elements and leg_index < len(elements):
                        elem = elements[leg_index]  # diagonal: origin[i] -> destination[i]
                        dur = elem.get("duration_seconds", 99999)
                        candidates.append((mode, dur))
            except (KeyError, IndexError, TypeError):
                continue

        if not candidates:
            return TravelMode.WALK

        # Same logic as _pick_best_route
        walk = next(((m, d) for m, d in candidates if m == TravelMode.WALK), None)
        others = [(m, d) for m, d in candidates if m != TravelMode.WALK]
        fastest_other = min(others, key=lambda x: x[1]) if others else None

        if walk:
            threshold = cls._walk_threshold_seconds(pace)
            multiplier = cls._walk_multiplier(pace)
            if walk[1] <= threshold:
                return TravelMode.WALK
            if fastest_other and walk[1] <= fastest_other[1] * multiplier:
                return TravelMode.WALK

        return min(candidates, key=lambda x: x[1])[0]

    # ── Weather warnings ─────────────────────────────────────────────

    _OUTDOOR_CATEGORIES: set[str] = {
        "park", "garden", "nature", "beach", "national_park", "campground",
        "zoo", "scenic_spot", "viewpoint", "trail", "hiking_area",
        "amusement_park", "tourist_attraction", "stadium",
        "marina", "waterfall", "lake", "mountain", "plaza",
    }

    _OUTDOOR_NAME_HINTS: set[str] = {
        "park", "garden", "beach", "trail", "lake", "river",
        "mountain", "forest", "waterfall", "promenade", "boardwalk",
        "pier", "harbour", "harbor", "marina", "viewpoint", "lookout",
        "plaza", "square", "terrace", "rooftop",
    }

    @classmethod
    def _add_weather_warnings(
        cls,
        activities: list[Activity],
        forecast: WeatherForecast,
    ) -> list[Activity]:
        """Tag outdoor activities with weather warnings based on forecast data."""
        for activity in activities:
            category = activity.place.category.lower() if activity.place.category else ""
            name_lower = activity.place.name.lower()

            is_outdoor = (
                category in cls._OUTDOOR_CATEGORIES
                or any(kw in name_lower for kw in cls._OUTDOOR_NAME_HINTS)
            )
            if not is_outdoor:
                continue

            warnings: list[str] = []
            # Graduated precipitation warnings
            precip = forecast.precipitation_chance_percent
            if precip >= 80:
                warnings.append(f"High rain chance ({precip}%) — strongly consider indoor alternative")
            elif precip >= 60:
                warnings.append(f"Rain likely ({precip}%) — bring umbrella or consider indoor alternative")
            elif precip >= 40:
                warnings.append(f"Possible rain ({precip}%) — have a backup plan")

            # Graduated temperature warnings
            temp = forecast.temperature_high_c
            if temp >= 38:
                warnings.append(f"Extreme heat ({temp:.0f}°C) — limit outdoor exposure, stay hydrated")
            elif temp >= 35:
                warnings.append(f"Very hot ({temp:.0f}°C) — stay hydrated, wear sunscreen")
            elif temp >= 32:
                warnings.append(f"Hot weather ({temp:.0f}°C) — bring water and sun protection")

            if forecast.uv_index is not None and forecast.uv_index >= 8:
                warnings.append(
                    f"Very high UV ({forecast.uv_index}) — wear sun protection"
                )
            if forecast.wind_speed_kmh >= 40:
                warnings.append(
                    f"Strong winds ({forecast.wind_speed_kmh:.0f} km/h) — exercise caution"
                )

            # Evening activities: check nighttime forecast
            if is_outdoor and activity.time_start >= "18:00":
                night_precip = forecast.night_precipitation_chance_percent
                if night_precip >= 80:
                    warnings.append(f"Evening rain very likely ({night_precip}%) — consider indoor alternative")
                elif night_precip >= 60:
                    warnings.append(f"Evening rain likely ({night_precip}%) — consider indoor alternative")
                elif night_precip >= 40:
                    warnings.append(f"Possible evening rain ({night_precip}%) — have a backup plan")

            if warnings:
                activity.weather_warning = " | ".join(warnings)

        return activities

    async def _discover_highlights(
        self,
        highlights: list[CityHighlight],
        city_name: str,
        location: Location,
    ) -> list[PlaceCandidate]:
        """Search for specific journey highlights by name via text search.

        The nearby-by-type discovery may miss unique attractions like
        "Coffee Plantation Walk" or "Coracle Ride on the Tungabhadra".
        This supplements with targeted text searches.
        """
        tasks = [
            self.places.text_search_places(
                query=f"{h.name} {city_name}",
                location=location,
                max_results=2,
            )
            for h in highlights
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_candidates: list[PlaceCandidate] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "[DayPlanOrchestrator] Highlight search failed for %r: %s",
                    highlights[i].name,
                    result,
                )
                continue
            all_candidates.extend(result)

        logger.info(
            "[DayPlanOrchestrator] Found %d candidates from %d highlight searches in %s",
            len(all_candidates),
            len(highlights),
            city_name,
        )
        return all_candidates

    async def _plan_city_batched(
        self,
        city,
        candidates: list,
        free_day_count: int,
        blocked_days: dict,
        request,
        landmarks: list[dict] | None = None,
        city_name: str = "",
        time_constraints: list[dict] | None = None,
    ) -> "AIPlan":
        """Plan a city's free days using Day Scout -> Day Reviewer -> Day Fixer loop.

        Processes all free days in a single pass. Cities are already parallelized
        at the orchestrator level, so no intra-city batching is needed.

        Args:
            city: The CityStop being planned.
            candidates: Pre-vetted PlaceCandidates from Google Places API.
            free_day_count: Number of non-excursion days to plan.
            blocked_days: Mapping of day index to excursion CityHighlight.
            request: The original TripRequest.
            landmarks: Optional top landmarks by visitor reviews.
            city_name: Name of the city being planned.

        Returns:
            AIPlan with activities for all free days.
        """
        from app.config.planning import (
            map_themes_to_days, MAX_DAY_PLAN_ITERATIONS,
            MIN_DAY_PLAN_SCORE,
        )
        from app.agents.day_planner import _build_meal_time_guidance
        from app.models.internal import AIPlan

        # Pre-map themes to day numbers
        theme_map = map_themes_to_days(
            city.experience_themes,
            free_day_count + len(blocked_days),
            blocked_days,
        )

        # Get free day numbers (not blocked by excursions)
        free_day_nums = sorted(
            d for d in range(1, free_day_count + len(blocked_days) + 1)
            if d not in blocked_days
        )

        meal_guidance = _build_meal_time_guidance(city.country or "")

        # Format landmarks for prompts
        landmarks_section = ""
        if landmarks:
            lines = ["TOP LANDMARKS by visitor reviews (include these across the stay):"]
            for lm in landmarks[:5]:
                lines.append(f"- {lm.get('name')} ({lm.get('user_ratings_total', 0):,} reviews)")
            landmarks_section = "\n".join(lines)

        all_themes = {d: theme_map.get(d, []) for d in free_day_nums}

        logger.info(
            "[DayPlanOrchestrator] Planning days %s in %s",
            free_day_nums, city_name,
        )

        # Day Scout: plan all free days at once
        try:
            city_plan = await self.day_scout.plan_batch(
                candidates=candidates,
                batch_themes=all_themes,
                destination=city_name,
                pace=request.pace.value,
                landmarks=landmarks,
                already_used=set(),
                meal_time_guidance=meal_guidance,
                travelers_description=request.travelers.summary,
                time_constraints=time_constraints,
            )
        except Exception as exc:
            logger.error(
                "[DayPlanOrchestrator] Day Scout failed for %s: %s",
                city_name, exc,
            )
            return AIPlan(
                selected_place_ids=[],
                day_groups=[],
                durations={},
                cost_estimates={},
            )

        # Quality loop: Day Reviewer -> Day Fixer
        for iteration in range(MAX_DAY_PLAN_ITERATIONS):
            # Format plan for reviewer
            themes_text = ""
            for d, themes in sorted(all_themes.items()):
                theme_names = ", ".join(
                    t.theme for t in themes
                ) if themes else "general"
                themes_text += f"Day {d}: {theme_names}\n"

            plan_detail = ""
            for i, group in enumerate(city_plan.day_groups):
                day_num = free_day_nums[i] if i < len(free_day_nums) else i + 1
                place_names = []
                for pid in group.place_ids:
                    name = next(
                        (c.name for c in candidates if c.place_id == pid),
                        pid,
                    )
                    dur = city_plan.durations.get(pid, "?")
                    place_names.append(f"{name} ({dur}min)")
                plan_detail += (
                    f"Day {day_num} ({group.theme}): "
                    f"{', '.join(place_names)}\n"
                )

            try:
                review = await self.day_reviewer.review_batch(
                    day_plans_detail=plan_detail,
                    batch_themes=themes_text,
                    landmarks_section=landmarks_section,
                    destination=city_name,
                )
            except Exception as exc:
                logger.warning(
                    "[DayPlanOrchestrator] Day Reviewer failed: %s", exc,
                )
                break

            logger.info(
                "[DayPlanOrchestrator] Review score: %d "
                "(acceptable=%s, iteration=%d)",
                review.score, review.is_acceptable, iteration + 1,
            )

            if review.is_acceptable and review.score >= MIN_DAY_PLAN_SCORE:
                break

            # Day Fixer: fix issues
            try:
                city_plan = await self.day_fixer.fix_batch(
                    current_plan=city_plan,
                    issues=review.issues,
                    candidates=candidates,
                    destination=city_name,
                    already_used=set(),
                )
            except Exception as exc:
                logger.warning(
                    "[DayPlanOrchestrator] Day Fixer failed: %s", exc,
                )
                break

        return city_plan
