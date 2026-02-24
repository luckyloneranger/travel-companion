"""Google Directions API service with full transit support.

Provides rich transit data including:
- Driving routes with distance/duration
- Rail routes (intercity trains like Shatabdi, Rajdhani)
- Bus routes (intercity buses like KSRTC, RedBus)
- Ferry routes where applicable

This is different from the Routes API - Directions API has better transit coverage.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Self, cast

import httpx

from app.config import get_settings
from app.core.clients import HTTPClientPool
from app.models import Location

logger = logging.getLogger(__name__)


class TransitMode(str, Enum):
    """Transit modes supported by Google Directions API."""
    RAIL = "rail"
    BUS = "bus"
    SUBWAY = "subway"
    TRAM = "tram"
    FERRY = "ferry"


class VehicleType(str, Enum):
    """Vehicle types returned by Google Directions API."""
    HEAVY_RAIL = "HEAVY_RAIL"  # Intercity trains
    COMMUTER_TRAIN = "COMMUTER_TRAIN"
    HIGH_SPEED_TRAIN = "HIGH_SPEED_TRAIN"
    LONG_DISTANCE_TRAIN = "LONG_DISTANCE_TRAIN"
    METRO_RAIL = "METRO_RAIL"
    SUBWAY = "SUBWAY"
    BUS = "BUS"
    INTERCITY_BUS = "INTERCITY_BUS"
    TROLLEYBUS = "TROLLEYBUS"
    FERRY = "FERRY"
    OTHER = "OTHER"


@dataclass
class TransitLine:
    """Information about a transit line (train/bus)."""
    name: str  # e.g., "Shatabdi Express"
    short_name: Optional[str] = None  # e.g., "12007"
    vehicle_type: str = "OTHER"
    agency_name: Optional[str] = None  # e.g., "Indian Railways"
    color: Optional[str] = None
    url: Optional[str] = None


@dataclass
class TransitStop:
    """A transit stop (station/bus stop)."""
    name: str
    location: Optional[Location] = None


@dataclass
class TransitStep:
    """A single transit step (e.g., one train journey)."""
    line: TransitLine
    departure_stop: TransitStop
    arrival_stop: TransitStop
    departure_time: str  # e.g., "6:00 AM"
    arrival_time: str  # e.g., "8:30 AM"
    duration_seconds: int
    num_stops: int
    headsign: Optional[str] = None  # Final destination of the line


@dataclass
class TransitRoute:
    """A complete transit route (may have multiple steps/transfers)."""
    mode: str  # "rail", "bus", "mixed"
    duration_seconds: int
    duration_text: str
    distance_meters: int
    steps: list[TransitStep] = field(default_factory=list)
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    num_transfers: int = 0
    fare: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class DrivingRoute:
    """A driving route."""
    distance_meters: int
    distance_km: float
    duration_seconds: int
    duration_hours: float
    duration_text: str
    polyline: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TransportOptions:
    """All transport options between two cities."""
    origin: str
    destination: str
    driving: Optional[DrivingRoute] = None
    rail_routes: list[TransitRoute] = field(default_factory=list)
    bus_routes: list[TransitRoute] = field(default_factory=list)
    ferry_routes: list[TransitRoute] = field(default_factory=list)
    
    @property
    def has_rail(self) -> bool:
        return len(self.rail_routes) > 0
    
    @property
    def has_bus(self) -> bool:
        return len(self.bus_routes) > 0
    
    @property
    def has_ferry(self) -> bool:
        return len(self.ferry_routes) > 0
    
    @property
    def best_rail(self) -> Optional[TransitRoute]:
        """Get the fastest rail route."""
        if not self.rail_routes:
            return None
        return min(self.rail_routes, key=lambda r: r.duration_seconds)
    
    @property
    def best_bus(self) -> Optional[TransitRoute]:
        """Get the fastest bus route."""
        if not self.bus_routes:
            return None
        return min(self.bus_routes, key=lambda r: r.duration_seconds)


class GoogleDirectionsService:
    """Service for Google Directions API with full transit support.
    
    Uses the legacy Directions API (not Routes API) because it has
    better intercity transit coverage.
    """
    
    BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Google Directions service."""
        settings = get_settings()
        self.api_key = api_key or settings.google_places_api_key  # Same key works
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the shared HTTP client."""
        return HTTPClientPool.get_places_client()  # Reuse places client
    
    async def __aenter__(self) -> Self:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
    
    async def get_driving_route(
        self,
        origin: str,
        destination: str,
    ) -> Optional[DrivingRoute]:
        """
        Get driving route between two places.
        
        Args:
            origin: Origin city name or coordinates
            destination: Destination city name or coordinates
            
        Returns:
            DrivingRoute with distance and duration, or None if not found
        """
        try:
            response = await self.client.get(
                self.BASE_URL,
                params={
                    "origin": origin,
                    "destination": destination,
                    "mode": "driving",
                    "key": self.api_key,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Directions API error: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("routes"):
                logger.warning(f"No driving route: {origin} → {destination}: {data.get('status')}")
                return None
            
            route = data["routes"][0]
            leg = route["legs"][0]
            
            distance_m = leg["distance"]["value"]
            duration_s = leg["duration"]["value"]
            
            return DrivingRoute(
                distance_meters=distance_m,
                distance_km=round(distance_m / 1000, 1),
                duration_seconds=duration_s,
                duration_hours=round(duration_s / 3600, 2),
                duration_text=leg["duration"]["text"],
                polyline=route.get("overview_polyline", {}).get("points"),
                warnings=route.get("warnings", []),
            )
            
        except Exception as e:
            logger.error(f"Error getting driving route: {e}")
            return None
    
    async def get_transit_routes(
        self,
        origin: str,
        destination: str,
        transit_modes: Optional[list[TransitMode]] = None,
        alternatives: bool = True,
    ) -> list[TransitRoute]:
        """
        Get transit routes (rail, bus, ferry) between two places.
        
        Args:
            origin: Origin city name
            destination: Destination city name
            transit_modes: List of modes to include (default: all)
            alternatives: Whether to request alternative routes
            
        Returns:
            List of TransitRoute options
        """
        if transit_modes is None:
            transit_modes = [TransitMode.RAIL, TransitMode.BUS]
        
        try:
            params = {
                "origin": origin,
                "destination": destination,
                "mode": "transit",
                "alternatives": "true" if alternatives else "false",
                "key": self.api_key,
            }
            
            # Add transit mode preference if specified
            if transit_modes:
                params["transit_mode"] = "|".join([m.value for m in transit_modes])
            
            response = await self.client.get(self.BASE_URL, params=params)
            
            if response.status_code != 200:
                logger.error(f"Transit API error: {response.status_code}")
                return []
            
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("routes"):
                logger.debug(f"No transit routes: {origin} → {destination}: {data.get('status')}")
                return []
            
            routes = []
            for route_data in data["routes"]:
                route = self._parse_transit_route(route_data)
                if route:
                    routes.append(route)
            
            return routes
            
        except Exception as e:
            logger.error(f"Error getting transit routes: {e}")
            return []
    
    def _parse_transit_route(self, route_data: dict) -> Optional[TransitRoute]:
        """Parse a transit route from API response."""
        try:
            leg = route_data["legs"][0]
            
            # Extract transit steps
            steps = []
            primary_mode = "mixed"
            mode_counts = {"rail": 0, "bus": 0, "ferry": 0}
            
            for step in leg.get("steps", []):
                if step.get("travel_mode") != "TRANSIT":
                    continue
                
                transit_details = step.get("transit_details", {})
                if not transit_details:
                    continue
                
                line_info = transit_details.get("line", {})
                vehicle = line_info.get("vehicle", {})
                vehicle_type = vehicle.get("type", "OTHER")
                
                # Categorize vehicle type
                if vehicle_type in ["HEAVY_RAIL", "COMMUTER_TRAIN", "HIGH_SPEED_TRAIN", 
                                   "LONG_DISTANCE_TRAIN", "METRO_RAIL", "SUBWAY"]:
                    mode_counts["rail"] += 1
                elif vehicle_type in ["BUS", "INTERCITY_BUS", "TROLLEYBUS"]:
                    mode_counts["bus"] += 1
                elif vehicle_type == "FERRY":
                    mode_counts["ferry"] += 1
                
                line = TransitLine(
                    name=line_info.get("name", "Unknown"),
                    short_name=line_info.get("short_name"),
                    vehicle_type=vehicle_type,
                    agency_name=line_info.get("agencies", [{}])[0].get("name") if line_info.get("agencies") else None,
                    color=line_info.get("color"),
                    url=line_info.get("url"),
                )
                
                departure_stop = TransitStop(
                    name=transit_details.get("departure_stop", {}).get("name", "Unknown"),
                )
                
                arrival_stop = TransitStop(
                    name=transit_details.get("arrival_stop", {}).get("name", "Unknown"),
                )
                
                transit_step = TransitStep(
                    line=line,
                    departure_stop=departure_stop,
                    arrival_stop=arrival_stop,
                    departure_time=transit_details.get("departure_time", {}).get("text", ""),
                    arrival_time=transit_details.get("arrival_time", {}).get("text", ""),
                    duration_seconds=step.get("duration", {}).get("value", 0),
                    num_stops=transit_details.get("num_stops", 0),
                    headsign=transit_details.get("headsign"),
                )
                
                steps.append(transit_step)
            
            if not steps:
                return None
            
            # Determine primary mode
            if mode_counts["rail"] > mode_counts["bus"] and mode_counts["rail"] > mode_counts["ferry"]:
                primary_mode = "rail"
            elif mode_counts["bus"] > mode_counts["rail"] and mode_counts["bus"] > mode_counts["ferry"]:
                primary_mode = "bus"
            elif mode_counts["ferry"] > 0:
                primary_mode = "ferry"
            
            # Get fare info if available
            fare = None
            if leg.get("fare"):
                fare = leg["fare"].get("text")
            
            return TransitRoute(
                mode=primary_mode,
                duration_seconds=leg["duration"]["value"],
                duration_text=leg["duration"]["text"],
                distance_meters=leg["distance"]["value"],
                steps=steps,
                departure_time=leg.get("departure_time", {}).get("text"),
                arrival_time=leg.get("arrival_time", {}).get("text"),
                num_transfers=len(steps) - 1 if len(steps) > 1 else 0,
                fare=fare,
                warnings=route_data.get("warnings", []),
            )
            
        except Exception as e:
            logger.error(f"Error parsing transit route: {e}")
            return None
    
    async def get_all_transport_options(
        self,
        origin: str,
        destination: str,
    ) -> TransportOptions:
        """
        Get all transport options (driving + transit) between two places.
        
        This makes parallel API calls for efficiency.
        
        Args:
            origin: Origin city name
            destination: Destination city name
            
        Returns:
            TransportOptions with all available modes
        """
        # Run driving and transit queries in parallel
        driving_task = self.get_driving_route(origin, destination)
        rail_task = self.get_transit_routes(origin, destination, [TransitMode.RAIL])
        bus_task = self.get_transit_routes(origin, destination, [TransitMode.BUS])
        
        driving_result, rail_result, bus_result = await asyncio.gather(
            driving_task, rail_task, bus_task,
            return_exceptions=True
        )
        
        # Handle exceptions and extract valid results
        driving: Optional[DrivingRoute] = None
        if isinstance(driving_result, Exception):
            logger.error(f"Driving route error: {driving_result}")
        elif driving_result is not None:
            driving = cast(DrivingRoute, driving_result)
        
        rail_routes: list[TransitRoute] = []
        if isinstance(rail_result, Exception):
            logger.error(f"Rail routes error: {rail_result}")
        elif rail_result is not None:
            rail_routes = cast(list[TransitRoute], rail_result)
        
        bus_routes: list[TransitRoute] = []
        if isinstance(bus_result, Exception):
            logger.error(f"Bus routes error: {bus_result}")
        elif bus_result is not None:
            bus_routes = cast(list[TransitRoute], bus_result)
        
        # Separate rail routes by actual mode (API sometimes returns mixed results)
        actual_rail = [r for r in rail_routes if r.mode == "rail"]
        actual_bus = [r for r in bus_routes if r.mode == "bus"]
        
        # Add any bus routes that came back from rail query
        actual_bus.extend([r for r in rail_routes if r.mode == "bus"])
        
        return TransportOptions(
            origin=origin,
            destination=destination,
            driving=driving,
            rail_routes=actual_rail,
            bus_routes=actual_bus,
        )
    
    async def build_transport_matrix(
        self,
        cities: list[str],
        include_origin: Optional[str] = None,
    ) -> dict[str, TransportOptions]:
        """
        Build a transport matrix for all city pairs.
        
        Args:
            cities: List of city names
            include_origin: If provided, also include routes from this origin
            
        Returns:
            Dict mapping "CityA→CityB" to TransportOptions
        """
        # Build list of all pairs we need
        all_cities = cities.copy()
        if include_origin and include_origin not in all_cities:
            all_cities = [include_origin] + all_cities
        
        pairs = []
        for i, origin in enumerate(all_cities):
            for dest in all_cities[i+1:]:
                pairs.append((origin, dest))
                pairs.append((dest, origin))  # Both directions
        
        logger.info(f"[Directions] Building transport matrix for {len(pairs)} city pairs")
        
        # Query all pairs in parallel (with some rate limiting)
        BATCH_SIZE = 5  # Google has rate limits
        matrix = {}
        
        for i in range(0, len(pairs), BATCH_SIZE):
            batch = pairs[i:i+BATCH_SIZE]
            tasks = [self.get_all_transport_options(o, d) for o, d in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for (origin, dest), result in zip(batch, results):
                key = f"{origin}→{dest}"
                if isinstance(result, Exception):
                    logger.error(f"Error for {key}: {result}")
                    matrix[key] = TransportOptions(origin=origin, destination=dest)
                else:
                    matrix[key] = result
            
            # Small delay between batches to respect rate limits
            if i + BATCH_SIZE < len(pairs):
                await asyncio.sleep(0.2)
        
        return matrix
