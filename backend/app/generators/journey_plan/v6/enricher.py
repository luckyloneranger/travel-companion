"""V6 Enricher - Ground plan with Google API data.

The Enricher takes an LLM-generated plan and enriches it with real data:
1. Validates and geocodes cities using Google Places
2. Gets actual directions/routes using Google Directions API
3. Updates travel durations with real data
"""

import asyncio
import logging
from typing import Optional

from app.services.external.google_places import GooglePlacesService
from app.services.external.google_directions import (
    GoogleDirectionsService,
    TransportOptions,
    TransitMode,
)
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    EnrichedPlan,
    TravelLeg,
    TransportMode,
)

logger = logging.getLogger(__name__)


class Enricher:
    """Enriches journey plans with Google API data."""
    
    def __init__(self):
        self.places_service = GooglePlacesService()
        self.directions_service = GoogleDirectionsService()
    
    async def enrich_plan(self, plan: JourneyPlan) -> EnrichedPlan:
        """
        Enrich a journey plan with real Google API data.
        
        Args:
            plan: JourneyPlan from Scout or Planner
            
        Returns:
            EnrichedPlan with validated cities and real transport data
        """
        logger.info(f"[Enricher] Enriching plan: {plan.route_string}")
        
        # Phase 1: Geocode all cities
        await self._geocode_cities(plan)
        
        # Phase 2: Get directions for all legs
        direction_data = {}
        total_travel_hours = 0.0
        total_distance_km = 0.0
        
        for i, leg in enumerate(plan.travel_legs):
            options = await self._get_transport_options(leg)
            direction_data[i] = options
            
            # Update leg with real data if available
            if options:
                self._update_leg_with_real_data(leg, options)
                total_travel_hours += leg.duration_hours
                if leg.distance_km:
                    total_distance_km += leg.distance_km
        
        enriched = EnrichedPlan(
            plan=plan,
            directions_available=True,
            total_travel_hours=total_travel_hours,
            total_distance_km=total_distance_km,
            direction_data=direction_data,
        )
        
        logger.info(f"[Enricher] Plan enriched: {total_travel_hours:.1f}h travel, {total_distance_km:.0f}km")
        
        return enriched
    
    async def _geocode_cities(self, plan: JourneyPlan) -> None:
        """Geocode all cities in the plan to get coordinates."""
        cities_to_geocode = [plan.origin] + [c.name for c in plan.cities]
        
        tasks = []
        for city_name in cities_to_geocode:
            tasks.append(self._geocode_city(city_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update city stops with geocoded data
        for i, city in enumerate(plan.cities):
            result = results[i + 1]  # Skip origin (index 0)
            if isinstance(result, dict):
                city.latitude = result.get("lat")
                city.longitude = result.get("lng")
                city.place_id = result.get("place_id")
    
    async def _geocode_city(self, city_name: str) -> dict:
        """Geocode a single city."""
        try:
            destination = await self.places_service.geocode(city_name)
            return {
                "lat": destination.location.lat,
                "lng": destination.location.lng,
                "place_id": getattr(destination, "place_id", None),
            }
        except Exception as e:
            logger.warning(f"[Enricher] Failed to geocode {city_name}: {e}")
            return {}
    
    async def _get_transport_options(self, leg: TravelLeg) -> Optional[TransportOptions]:
        """Get transport options for a travel leg."""
        origin = leg.from_city
        destination = leg.to_city
        
        try:
            # Get driving route
            driving = await self.directions_service.get_driving_route(origin, destination)
            
            # Get transit routes (rail, bus & ferry)
            transit_routes = await self.directions_service.get_transit_routes(
                origin,
                destination,
                transit_modes=[TransitMode.RAIL, TransitMode.BUS, TransitMode.FERRY],
                alternatives=True,
            )
            
            # Separate rail vs bus vs ferry routes
            rail_routes = [r for r in transit_routes if r.mode == "rail"]
            bus_routes = [r for r in transit_routes if r.mode == "bus"]
            ferry_routes = [r for r in transit_routes if r.mode == "ferry"]
            
            return TransportOptions(
                origin=origin,
                destination=destination,
                driving=driving,
                rail_routes=rail_routes,
                bus_routes=bus_routes,
                ferry_routes=ferry_routes,
            )
            
        except Exception as e:
            logger.warning(f"[Enricher] Failed to get transport for {origin} → {destination}: {e}")
            return None
    
    def _update_leg_with_real_data(self, leg: TravelLeg, options: TransportOptions) -> None:
        """Update a travel leg with real transport data."""
        
        # For flights, keep LLM estimates (we don't have flight API)
        if leg.mode == TransportMode.FLIGHT:
            # LLM provides flight estimates - keep them
            return
        
        # For train, use real rail data if available
        if leg.mode == TransportMode.TRAIN and options.best_rail:
            rail = options.best_rail
            leg.duration_hours = round(rail.duration_seconds / 3600, 2)
            if rail.steps:
                step = rail.steps[0]
                leg.notes = f"{step.line.name} - {step.departure_time} → {step.arrival_time}"
            if options.driving:
                leg.distance_km = options.driving.distance_km
            leg.route_polyline = None  # Transit doesn't have polyline
            
        # For bus, use real bus data if available
        elif leg.mode == TransportMode.BUS and options.best_bus:
            bus = options.best_bus
            leg.duration_hours = round(bus.duration_seconds / 3600, 2)
            if bus.steps:
                step = bus.steps[0]
                leg.notes = f"{step.line.name} - {step.departure_time} → {step.arrival_time}"
            if options.driving:
                leg.distance_km = options.driving.distance_km
                
        # For ferry, use real ferry data if available
        elif leg.mode == TransportMode.FERRY and options.best_ferry:
            ferry = options.best_ferry
            leg.duration_hours = round(ferry.duration_seconds / 3600, 2)
            if ferry.steps:
                step = ferry.steps[0]
                leg.notes = f"{step.line.name} - {step.departure_time} → {step.arrival_time}"
            # Ferry distance is usually not meaningful, keep LLM estimate if any
                
        # For driving, use real driving data
        elif leg.mode == TransportMode.DRIVE and options.driving:
            driving = options.driving
            leg.duration_hours = driving.duration_hours
            leg.distance_km = driving.distance_km
            leg.route_polyline = driving.polyline
            leg.notes = f"Drive: {driving.duration_text}, {driving.distance_km}km"
            
        # Fallback: If requested mode not available, use driving as baseline
        elif options.driving:
            # Keep the original mode but update with driving estimate
            driving = options.driving
            if leg.duration_hours == 0:
                leg.duration_hours = driving.duration_hours
            if not leg.distance_km:
                leg.distance_km = driving.distance_km
