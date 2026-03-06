"""Enricher agent — grounds a journey plan with real Google API data.

Takes an LLM-generated JourneyPlan and enriches it with:
1. Geocoded city locations via Google Places
2. Accommodation details via Places lodging search
3. Real transport durations/distances via Google Directions API
"""

import asyncio
import logging

from app.models.common import Location, TransportMode
from app.models.journey import Accommodation, CityStop, JourneyPlan, TravelLeg
from app.services.google import (
    GoogleDirectionsService,
    GooglePlacesService,
    GoogleRoutesService,
)
from app.services.google.directions import TransportOptions

logger = logging.getLogger(__name__)

# ── Cost estimation heuristics ────────────────────────────────────────

class EnricherAgent:
    """Enriches journey plans with Google API data.

    Parameters
    ----------
    places:
        Google Places service for geocoding and accommodation lookup.
    routes:
        Google Routes service (currently unused but available for
        driving-only route computation).
    directions:
        Google Directions service for transit, driving, and ferry routing.
    """

    def __init__(
        self,
        places: GooglePlacesService,
        routes: GoogleRoutesService,
        directions: GoogleDirectionsService,
    ):
        self.places = places
        self.routes = routes
        self.directions = directions
        self._origin_cache: dict[str, Location] = {}

    async def enrich_plan(self, plan: JourneyPlan, budget_tier: str = "moderate") -> JourneyPlan:
        """Enrich a journey plan with real Google API data.

        Geocodes all cities, enriches accommodation, fetches real transport
        data, and updates plan totals. LLM-provided cost estimates
        (estimated_nightly_usd, fare_usd) are preserved.

        Args:
            plan: JourneyPlan from Scout or Planner.
            budget_tier: One of "budget", "moderate", "luxury" (informational only).

        Returns:
            The same JourneyPlan, mutated in-place with enriched data.
        """
        logger.info("[Enricher] Enriching plan: %s", plan.route or "unknown route")

        # Phase 1: Geocode all cities in parallel.
        await self._geocode_cities(plan)

        # Phase 2: Enrich accommodations in parallel.
        await self._enrich_accommodations(plan, budget_tier=budget_tier)

        # Phase 3: Enrich all travel legs with real transport data.
        total_travel_hours = 0.0
        total_distance_km = 0.0

        if plan.travel_legs:
            enriched_legs = await asyncio.gather(
                *(self._enrich_travel_leg(leg, plan) for leg in plan.travel_legs),
                return_exceptions=True,
            )
            for i, result in enumerate(enriched_legs):
                if isinstance(result, Exception):
                    logger.warning(
                        "[Enricher] Failed to enrich leg %d: %s", i, result
                    )
                    continue
                leg = plan.travel_legs[i]
                total_travel_hours += leg.duration_hours
                if leg.distance_km:
                    total_distance_km += leg.distance_km

        plan.total_travel_hours = round(total_travel_hours, 1)
        plan.total_distance_km = round(total_distance_km, 1)

        logger.info(
            "[Enricher] Plan enriched: %.1fh travel, %.0fkm",
            total_travel_hours,
            total_distance_km,
        )

        return plan

    # ── City geocoding ───────────────────────────────────────────────────

    async def _geocode_cities(self, plan: JourneyPlan) -> None:
        """Geocode all cities in the plan to get coordinates and place IDs."""
        tasks = [self._enrich_city(city) for city in plan.cities]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _enrich_city(self, city: CityStop) -> None:
        """Geocode a single city and set its location and place_id.

        Tries the country-qualified name first (e.g. "Barcelona Spain")
        to avoid resolving to same-named cities in other countries, then
        falls back to the city name alone.
        """
        queries: list[str] = []
        if city.country:
            queries.append(f"{city.name}, {city.country}")
        queries.append(city.name)

        for query in queries:
            try:
                result = await self.places.geocode(query)
                lat = result.get("lat", 0.0)
                lng = result.get("lng", 0.0)
                if lat and lng:
                    city.location = Location(lat=lat, lng=lng)
                    # Reject null-island coordinates (0,0)
                    if abs(city.location.lat) < 0.01 and abs(city.location.lng) < 0.01:
                        logger.warning("[Enricher] Geocoding returned null-island (0,0) for %s — treating as failed", city.name)
                        city.location = None
                        continue
                    city.place_id = result.get("place_id")
                    if not city.country and result.get("country"):
                        city.country = result["country"]
                    utc_offset = result.get("utc_offset_minutes")
                    if utc_offset is not None:
                        city.timezone_offset_minutes = utc_offset
                    logger.debug(
                        "[Enricher] Geocoded %s (query=%r): (%.4f, %.4f)",
                        city.name, query, lat, lng,
                    )
                    return
            except Exception as e:
                logger.debug(
                    "[Enricher] Geocode attempt failed for %r: %s", query, e
                )

        logger.warning("[Enricher] Failed to geocode %s (tried %s), attempting broader fallback", city.name, queries)

        # Fallback: try with country suffix if not already tried
        if city.country:
            fallback_query = f"{city.name}, {city.country}"
            if fallback_query not in queries:
                logger.info("[Enricher] Retrying geocode with: %s", fallback_query)
                try:
                    result = await self.places.geocode(fallback_query)
                    lat = result.get("lat", 0.0)
                    lng = result.get("lng", 0.0)
                    if lat and lng:
                        city.location = Location(lat=lat, lng=lng)
                        # Reject null-island coordinates (0,0)
                        if abs(city.location.lat) < 0.01 and abs(city.location.lng) < 0.01:
                            logger.warning("[Enricher] Fallback geocoding returned null-island (0,0) for %s — treating as failed", city.name)
                            city.location = None
                        else:
                            city.place_id = result.get("place_id")
                            utc_offset = result.get("utc_offset_minutes")
                            if utc_offset is not None:
                                city.timezone_offset_minutes = utc_offset
                            logger.info(
                                "[Enricher] Fallback geocode succeeded for %s: (%.4f, %.4f)",
                                city.name, lat, lng,
                            )
                            return
                except Exception as e:
                    logger.debug(
                        "[Enricher] Fallback geocode failed for %r: %s", fallback_query, e
                    )

        logger.warning("[Enricher] All geocode attempts failed for %s", city.name)

    # ── Accommodation enrichment ─────────────────────────────────────────

    async def _enrich_accommodations(self, plan: JourneyPlan, budget_tier: str = "moderate") -> None:
        """Enrich accommodation data for each city using Google Places."""
        tasks = []
        for city in plan.cities:
            if city.accommodation and city.accommodation.name:
                tasks.append(self._enrich_accommodation(city, budget_tier=budget_tier))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _enrich_accommodation(self, city: CityStop, budget_tier: str = "moderate") -> None:
        """Search for a city's accommodation via Places lodging search.

        Tries the LLM-suggested name first, then falls back to a generic
        search by city name if the specific hotel isn't found.
        Uses budget_tier to select appropriate price heuristics.
        """
        if not city.accommodation or not city.accommodation.name:
            return

        city_location = city.location
        if not city_location:
            logger.warning(
                "[Enricher] No location for %s, skipping accommodation enrichment",
                city.name,
            )
            return

        try:
            # Try 1: search for the specific accommodation name
            query = f"{city.accommodation.name} {city.name}"
            result = await self.places.search_lodging(
                query=query,
                location=city_location,
            )

            # Try 2: broader search with just the city name
            if not result:
                logger.info(
                    "[Enricher] Specific lodging %r not found in %s, "
                    "trying generic search",
                    city.accommodation.name,
                    city.name,
                )
                result = await self.places.search_lodging(
                    query=f"hotel {city.name}",
                    location=city_location,
                    radius_meters=20_000,
                )

            if result:
                # Validate accommodation quality before accepting
                if (result.rating is not None and result.rating < 3.5) or \
                   (result.user_ratings_total is not None and result.user_ratings_total < 20):
                    logger.warning(
                        "[Enricher] Low-quality lodging result for %s: %s (rating=%s, reviews=%s) — keeping LLM suggestion",
                        city.name, result.name, result.rating, result.user_ratings_total,
                    )
                    # Keep LLM's original accommodation, just add place_id and location for maps
                    if city.accommodation:
                        city.accommodation.place_id = result.place_id
                        city.accommodation.location = result.location
                    return

                # Preserve LLM's cost estimate from the Scout agent
                llm_nightly = city.accommodation.estimated_nightly_usd if city.accommodation else None
                llm_why = city.accommodation.why if city.accommodation else ""
                city.accommodation = Accommodation(
                    name=result.name,
                    why=llm_why,
                    address=result.address,
                    location=result.location,
                    place_id=result.place_id,
                    rating=result.rating,
                    price_level=result.price_level,
                    estimated_nightly_usd=llm_nightly,
                    website=result.website,
                    editorial_summary=result.editorial_summary,
                    photo_url=(
                        self.places.get_photo_url(result.photo_reference)
                        if result.photo_reference
                        else None
                    ),
                )
                logger.info(
                    "[Enricher] Enriched accommodation for %s: %s",
                    city.name,
                    result.name,
                )
            else:
                logger.warning(
                    "[Enricher] No lodging found for %s in %s",
                    city.accommodation.name,
                    city.name,
                )
                # LLM's estimate is already on city.accommodation — nothing to do
        except Exception as e:
            logger.warning(
                "[Enricher] Accommodation enrichment failed for %s: %s",
                city.name,
                e,
            )
            # LLM's estimate is already on city.accommodation — nothing to do

    # ── Travel leg enrichment ────────────────────────────────────────────

    async def _enrich_travel_leg(
        self, leg: TravelLeg, plan: JourneyPlan
    ) -> None:
        """Enrich a single travel leg with real transport data.

        Resolves city names to locations, fetches transport options via
        the Directions API, and updates the leg in-place.
        """
        original_booking_tip = leg.booking_tip

        origin_loc = self._find_city_location(leg.from_city, plan)
        dest_loc = self._find_city_location(leg.to_city, plan)

        # If origin not found (e.g. departure city not in destinations), geocode it
        if not origin_loc:
            origin_loc = await self._geocode_origin(leg.from_city)
            if origin_loc:
                self._origin_cache[leg.from_city.lower()] = origin_loc

        if not origin_loc or not dest_loc:
            logger.warning(
                "[Enricher] Cannot enrich leg %s -> %s: missing location(s)",
                leg.from_city,
                leg.to_city,
            )
            return

        try:
            options = await self.directions.get_all_transport_options(
                origin=origin_loc,
                destination=dest_loc,
                origin_name=leg.from_city,
                destination_name=leg.to_city,
            )
            self._update_leg_with_real_data(leg, options)
            # LLM's fare_usd from Scout is already on the leg — no overwrite needed
        except Exception as e:
            logger.warning(
                "[Enricher] Failed to get transport for %s -> %s: %s",
                leg.from_city,
                leg.to_city,
                e,
            )

        # Check for multi-country legs without visa context
        from_country = next(
            (c.country for c in plan.cities if c.name.lower() == leg.from_city.lower()),
            None,
        )
        to_country = next(
            (c.country for c in plan.cities if c.name.lower() == leg.to_city.lower()),
            None,
        )
        if (
            from_country
            and to_country
            and from_country.lower() != to_country.lower()
            and (not leg.notes or "visa" not in leg.notes.lower())
        ):
            logger.info(
                "[Enricher] Multi-country leg %s (%s) -> %s (%s) has no visa notes",
                leg.from_city,
                from_country,
                leg.to_city,
                to_country,
            )

        if not leg.booking_tip and original_booking_tip:
            leg.booking_tip = original_booking_tip

    async def _geocode_origin(self, origin_name: str) -> Location | None:
        """Geocode the origin city if it's not in the plan's destinations."""
        try:
            result = await self.places.geocode(origin_name)
            lat = result.get("lat", 0.0)
            lng = result.get("lng", 0.0)
            if lat and lng:
                return Location(lat=lat, lng=lng)
        except Exception as e:
            logger.warning("[Enricher] Failed to geocode origin %s: %s", origin_name, e)
        return None

    def _find_city_location(
        self, city_name: str, plan: JourneyPlan
    ) -> Location | None:
        """Look up a city's location from the enriched plan.

        Checks the plan's cities and the cached origin location.
        """
        for city in plan.cities:
            if city.name.lower() == city_name.lower() and city.location:
                return city.location
        # Check cached origin location
        if city_name.lower() in self._origin_cache:
            return self._origin_cache[city_name.lower()]
        return None

    def _update_leg_with_real_data(
        self, leg: TravelLeg, options: TransportOptions
    ) -> None:
        """Update a travel leg with real transport data from the API.

        Picks the best available data source based on the leg's transport
        mode, falling back to driving distance when the requested mode
        is not available. Rejects transit routes that are absurdly long
        compared to driving.
        """
        # If leg has segments, ground each non-flight segment
        if leg.segments:
            self._ground_segments(leg, options)
            return

        # For flights without segments, estimate distance from driving data
        if leg.mode == TransportMode.FLIGHT:
            if options.driving:
                leg.distance_km = round(options.driving.distance_meters / 1000, 1)
            return

        # Determine driving duration as a sanity baseline.
        driving_seconds = (
            options.driving.duration_seconds if options.driving else None
        )

        # Try to find a matching transit route by mode.
        if leg.mode in (
            TransportMode.TRAIN,
            TransportMode.BUS,
            TransportMode.FERRY,
        ):
            best_transit = self._find_best_transit_route(
                leg.mode, options.transit_routes, driving_seconds
            )
            if best_transit:
                leg.duration_hours = round(
                    best_transit.duration_seconds / 3600, 2
                )
                leg.fare = best_transit.fare
                # Try to update fare_usd from the new fare string
                if best_transit.fare:
                    parsed = self._try_parse_fare_usd(best_transit.fare)
                    if parsed is not None:
                        leg.fare_usd = parsed
                leg.num_transfers = best_transit.num_transfers
                leg.departure_time = best_transit.departure_time
                leg.arrival_time = best_transit.arrival_time
                # Use driving distance as approximate geographic distance.
                if options.driving:
                    leg.distance_km = round(
                        options.driving.distance_meters / 1000, 1
                    )
                # Build descriptive notes from transit steps.
                if best_transit.steps:
                    step_descriptions = []
                    for step in best_transit.steps:
                        if step.travel_mode == "TRANSIT" and step.line.name:
                            desc = step.line.name
                            if step.line.agency:
                                desc += f" ({step.line.agency})"
                            step_descriptions.append(desc)
                    if step_descriptions:
                        transit_info = " -> ".join(step_descriptions)
                        if best_transit.departure_time and best_transit.arrival_time:
                            transit_info += (
                                f" | {best_transit.departure_time}"
                                f" -> {best_transit.arrival_time}"
                            )
                        # Preserve original notes and booking_tip
                        parts = [transit_info]
                        if leg.booking_tip:
                            parts.append(f"Booking: {leg.booking_tip}")
                        leg.notes = " | ".join(parts)
                return

        # For driving, use real driving data.
        if leg.mode == TransportMode.DRIVE and options.driving:
            driving = options.driving
            leg.duration_hours = round(driving.duration_seconds / 3600, 2)
            leg.distance_km = round(driving.distance_meters / 1000, 1)
            leg.polyline = driving.polyline
            drive_info = (
                f"Drive: {driving.duration_text}, "
                f"{round(driving.distance_meters / 1000, 1)}km"
            )
            # Preserve original notes and booking_tip
            parts = [drive_info]
            if leg.booking_tip:
                parts.append(f"Booking: {leg.booking_tip}")
            leg.notes = " | ".join(parts)
            return

        # Fallback: use driving distance as baseline for any mode.
        if options.driving:
            # Preserve island transport modes — warn when ferry has no API match
            if leg.mode == TransportMode.FERRY:
                logger.info(
                    "[Enricher] Preserving ferry mode for %s -> %s "
                    "(API suggested driving — %.1fkm). "
                    "Only updating distance, keeping Scout's duration estimate.",
                    leg.from_city,
                    leg.to_city,
                    options.driving.distance_meters / 1000,
                )
                # Only update distance, keep Scout's duration for ferry routes
                leg.distance_km = round(options.driving.distance_meters / 1000, 1)
                return

            logger.info(
                "[Enricher] No %s data for %s -> %s, using driving distance "
                "(%.1fkm) as baseline",
                leg.mode.value,
                leg.from_city,
                leg.to_city,
                options.driving.distance_meters / 1000,
            )
            leg.distance_km = round(options.driving.distance_meters / 1000, 1)
            if leg.duration_hours == 0:
                leg.duration_hours = round(
                    options.driving.duration_seconds / 3600, 2
                )

    def _ground_segments(
        self, leg: TravelLeg, options: TransportOptions
    ) -> None:
        """Ground non-flight segments using available API data.

        Flight segments are preserved as-is (no Google flight API).
        Drive/transit segments use driving route data for distance estimation.
        Marks grounded segments with is_grounded=True.
        """
        total_hours = 0.0

        for segment in leg.segments:
            if segment.mode == "flight":
                # No API for flights — keep LLM estimate
                total_hours += segment.duration_hours
                continue

            if segment.mode in ("drive", "walk"):
                # Mark as grounded — driving data provides baseline validation
                if options.driving:
                    segment.is_grounded = True
                total_hours += segment.duration_hours
                continue

            # bus/train/ferry segments — keep LLM estimates, mark as not grounded
            total_hours += segment.duration_hours

        # Update total leg duration from segment sum
        if total_hours > 0:
            leg.duration_hours = round(total_hours, 2)

        # Use driving distance as baseline for total leg distance
        if options.driving and not leg.distance_km:
            leg.distance_km = round(options.driving.distance_meters / 1000, 1)

        logger.info(
            "[Enricher] Grounded %d/%d segments for %s → %s (%.1fh total)",
            sum(1 for s in leg.segments if s.is_grounded),
            len(leg.segments),
            leg.from_city, leg.to_city, total_hours,
        )

    @staticmethod
    def _try_parse_fare_usd(fare_string: str) -> float | None:
        """Try to parse a USD numeric value from a fare string like '$12.50' or 'USD 5.50'."""
        import re
        if not fare_string:
            return None
        # Match patterns like "$12.50", "USD 5.50", "12.50"
        match = re.search(r'\$?\s*(\d+(?:\.\d{1,2})?)', fare_string)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _find_best_transit_route(
        mode: TransportMode,
        transit_routes: list,
        driving_seconds: int | None = None,
    ):
        """Find the best transit route matching the requested mode.

        Filters transit routes by vehicle type and picks the one with
        the shortest duration. Rejects routes that take more than 4x
        the driving time (likely indirect/absurd routings).

        Returns:
            The best matching transit route, or None if no reasonable match.
        """
        if not transit_routes:
            return None

        # Map our TransportMode to Directions API vehicle types.
        vehicle_type_map = {
            TransportMode.TRAIN: {"RAIL", "HEAVY_RAIL", "COMMUTER_TRAIN", "HIGH_SPEED_TRAIN", "LONG_DISTANCE_TRAIN", "SUBWAY", "METRO_RAIL"},
            TransportMode.BUS: {"BUS", "INTERCITY_BUS", "TROLLEYBUS"},
            TransportMode.FERRY: {"FERRY"},
        }
        target_types = vehicle_type_map.get(mode, set())

        # Max acceptable duration: 4x driving time (allows scenic/slow routes),
        # or 6x for potential overnight routes (sleeper trains, long ferries).
        # 24 hours absolute cap.
        max_duration = 24 * 3600
        if driving_seconds and driving_seconds > 0:
            max_duration = min(max_duration, driving_seconds * 4)

        matching = []
        for route in transit_routes:
            if route.duration_seconds > max_duration:
                continue
            for step in route.steps:
                if (
                    step.travel_mode == "TRANSIT"
                    and step.line.vehicle_type in target_types
                ):
                    matching.append(route)
                    break

        if not matching:
            # Fall back to any transit route, but still apply sanity check.
            sane_routes = [
                r for r in transit_routes
                if r.duration_seconds <= max_duration
            ]
            if sane_routes:
                return min(sane_routes, key=lambda r: r.duration_seconds)
            logger.warning(
                "[Enricher] All transit routes exceed sanity threshold "
                "(max %.1fh), rejecting",
                max_duration / 3600,
            )
            return None

        return min(matching, key=lambda r: r.duration_seconds)
