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

    async def enrich_plan(self, plan: JourneyPlan) -> JourneyPlan:
        """Enrich a journey plan with real Google API data.

        Geocodes all cities, enriches accommodation, fetches real transport
        data, and updates plan totals.

        Args:
            plan: JourneyPlan from Scout or Planner (cities may lack
                  coordinates and real transport data).

        Returns:
            The same JourneyPlan, mutated in-place with enriched data and
            updated total_distance_km / total_travel_hours.
        """
        logger.info("[Enricher] Enriching plan: %s", plan.route or "unknown route")

        # Phase 1: Geocode all cities in parallel.
        await self._geocode_cities(plan)

        # Phase 2: Enrich accommodations in parallel.
        await self._enrich_accommodations(plan)

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
        """Geocode a single city and set its location and place_id."""
        try:
            result = await self.places.geocode(city.name)
            lat = result.get("lat", 0.0)
            lng = result.get("lng", 0.0)
            if lat and lng:
                city.location = Location(lat=lat, lng=lng)
            city.place_id = result.get("place_id")
            # Update country if geocode returns one and the city lacks it.
            if not city.country and result.get("country"):
                city.country = result["country"]
            logger.debug("[Enricher] Geocoded %s: (%.4f, %.4f)", city.name, lat, lng)
        except Exception as e:
            logger.warning("[Enricher] Failed to geocode %s: %s", city.name, e)

    # ── Accommodation enrichment ─────────────────────────────────────────

    async def _enrich_accommodations(self, plan: JourneyPlan) -> None:
        """Enrich accommodation data for each city using Google Places."""
        tasks = []
        for city in plan.cities:
            if city.accommodation and city.accommodation.name:
                tasks.append(self._enrich_accommodation(city))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _enrich_accommodation(self, city: CityStop) -> None:
        """Search for a city's accommodation via Places lodging search.

        Falls back gracefully if the suggested hotel is not found.
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
            query = f"{city.accommodation.name} hotel {city.name}"
            result = await self.places.search_lodging(
                query=query,
                location=city_location,
            )

            if result:
                city.accommodation = Accommodation(
                    name=result.name,
                    address=result.address,
                    location=result.location,
                    place_id=result.place_id,
                    rating=result.rating,
                    price_level=result.price_level,
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
        except Exception as e:
            logger.warning(
                "[Enricher] Accommodation enrichment failed for %s: %s",
                city.name,
                e,
            )

    # ── Travel leg enrichment ────────────────────────────────────────────

    async def _enrich_travel_leg(
        self, leg: TravelLeg, plan: JourneyPlan
    ) -> None:
        """Enrich a single travel leg with real transport data.

        Resolves city names to locations, fetches transport options via
        the Directions API, and updates the leg in-place.
        """
        origin_loc = self._find_city_location(leg.from_city, plan)
        dest_loc = self._find_city_location(leg.to_city, plan)

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
        except Exception as e:
            logger.warning(
                "[Enricher] Failed to get transport for %s -> %s: %s",
                leg.from_city,
                leg.to_city,
                e,
            )

    def _find_city_location(
        self, city_name: str, plan: JourneyPlan
    ) -> Location | None:
        """Look up a city's location from the enriched plan.

        Checks the plan's cities first, then tries the origin name
        (which may have been geocoded separately).
        """
        for city in plan.cities:
            if city.name.lower() == city_name.lower() and city.location:
                return city.location
        return None

    def _update_leg_with_real_data(
        self, leg: TravelLeg, options: TransportOptions
    ) -> None:
        """Update a travel leg with real transport data from the API.

        Picks the best available data source based on the leg's transport
        mode, falling back to driving distance when the requested mode
        is not available.
        """
        # For flights, keep LLM estimates (we don't have a flight API).
        if leg.mode == TransportMode.FLIGHT:
            return

        # Try to find a matching transit route by mode.
        if leg.mode in (
            TransportMode.TRAIN,
            TransportMode.BUS,
            TransportMode.FERRY,
        ):
            best_transit = self._find_best_transit_route(
                leg.mode, options.transit_routes
            )
            if best_transit:
                leg.duration_hours = round(
                    best_transit.duration_seconds / 3600, 2
                )
                leg.fare = best_transit.fare
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
                        leg.notes = " -> ".join(step_descriptions)
                        if best_transit.departure_time and best_transit.arrival_time:
                            leg.notes += (
                                f" | {best_transit.departure_time}"
                                f" -> {best_transit.arrival_time}"
                            )
                return

        # For driving, use real driving data.
        if leg.mode == TransportMode.DRIVE and options.driving:
            driving = options.driving
            leg.duration_hours = round(driving.duration_seconds / 3600, 2)
            leg.distance_km = round(driving.distance_meters / 1000, 1)
            leg.polyline = driving.polyline
            leg.notes = (
                f"Drive: {driving.duration_text}, "
                f"{round(driving.distance_meters / 1000, 1)}km"
            )
            return

        # Fallback: use driving distance as baseline for any mode.
        if options.driving:
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

    @staticmethod
    def _find_best_transit_route(
        mode: TransportMode, transit_routes: list
    ):
        """Find the best transit route matching the requested mode.

        Filters transit routes by vehicle type and picks the one with
        the shortest duration.

        Returns:
            The best matching transit route, or None if no match.
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

        matching = []
        for route in transit_routes:
            for step in route.steps:
                if (
                    step.travel_mode == "TRANSIT"
                    and step.line.vehicle_type in target_types
                ):
                    matching.append(route)
                    break

        if not matching:
            # Fall back to any transit route if no exact mode match.
            return min(transit_routes, key=lambda r: r.duration_seconds) if transit_routes else None

        return min(matching, key=lambda r: r.duration_seconds)
