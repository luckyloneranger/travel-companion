"""Transport validation service using Google APIs.

Validates and enriches inter-city transport info with real data and scheduling recommendations.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.models import Location, TravelMode
from app.services.external.google_places import GooglePlacesService
from app.services.external.google_routes import GoogleRoutesService

logger = logging.getLogger(__name__)


@dataclass
class ValidatedTransport:
    """Transport info enriched with Google API data and scheduling recommendations."""
    
    # Original from LLM
    llm_mode: str
    llm_duration_hours: float
    llm_notes: Optional[str]
    
    # Verified from Google
    driving_duration_hours: Optional[float] = None
    driving_distance_km: Optional[float] = None
    
    # Derived
    is_verified: bool = False
    verification_note: Optional[str] = None
    suggested_mode: Optional[str] = None
    
    # Scheduling recommendations
    suggested_departure: Optional[str] = None  # e.g., "08:00" or "Evening"
    estimated_arrival: Optional[str] = None    # e.g., "14:30" or "Next morning"
    is_overnight: bool = False
    booking_tip: Optional[str] = None
    
    @property
    def display_duration_hours(self) -> float:
        """Return the best available duration estimate."""
        if self.driving_duration_hours and self.llm_mode in ("train", "flight", "bus"):
            return self.llm_duration_hours
        return self.driving_duration_hours or self.llm_duration_hours
    
    def compute_schedule(self) -> None:
        """
        Compute recommended departure/arrival based on distance and mode.
        
        Logic:
        - Short journeys (< 4h): Morning departure to arrive for lunch/afternoon
        - Medium journeys (4-8h): Early morning (6-8 AM) to arrive evening
        - Long journeys (> 8h): Recommend overnight transport or flight
        - Flights: Airport timings (2h before) factored in
        """
        duration = self.llm_duration_hours
        distance = self.driving_distance_km or 0
        mode = self.llm_mode
        
        if mode == "flight":
            # Flights - need to be at airport early
            if duration <= 2:
                self.suggested_departure = "Morning (arrive airport by 06:00)"
                self.estimated_arrival = f"~{8 + duration:.0f}:00 (after landing + transfer)"
                self.booking_tip = "Book early for best fares; airport transfers add ~1h each end"
            else:
                self.suggested_departure = "Early morning or evening flight"
                arrival_hour = 8 + duration + 2  # 2h buffer for airport
                if arrival_hour > 20:
                    self.estimated_arrival = "Evening/night arrival"
                else:
                    self.estimated_arrival = f"~{arrival_hour:.0f}:00"
                self.booking_tip = "Check for direct flights; layovers add significant time"
            self.is_overnight = False
            
        elif mode in ("train", "bus"):
            if duration <= 3:
                # Short journey - comfortable morning travel
                self.suggested_departure = "09:00 - 10:00"
                arrival_hour = 9 + duration
                self.estimated_arrival = f"~{arrival_hour:.0f}:00"
                self.booking_tip = f"Regular {mode} service available; book day before"
                self.is_overnight = False
                
            elif duration <= 6:
                # Medium journey - early start
                self.suggested_departure = "07:00 - 08:00"
                arrival_hour = 7 + duration
                self.estimated_arrival = f"~{arrival_hour:.0f}:00"
                self.booking_tip = f"Book in advance; {mode} fills up on weekends"
                self.is_overnight = False
                
            elif duration <= 10:
                # Long journey - consider overnight
                self.suggested_departure = "Evening (20:00 - 22:00)"
                self.estimated_arrival = "Next morning (06:00 - 08:00)"
                self.is_overnight = True
                if mode == "train":
                    self.booking_tip = "Book sleeper/AC class for comfort on overnight train"
                else:
                    self.booking_tip = "Overnight bus - book semi-sleeper if available"
                    
            else:
                # Very long journey - strongly recommend alternatives
                self.suggested_departure = "Evening for overnight journey"
                self.estimated_arrival = "Next day"
                self.is_overnight = True
                self.booking_tip = f"Very long {mode} journey; consider flying or breaking the trip"
                
        elif mode == "car":
            if duration <= 4:
                self.suggested_departure = "08:00 - 09:00"
                arrival_hour = 8 + duration + 0.5  # Add break time
                self.estimated_arrival = f"~{arrival_hour:.0f}:30"
                self.booking_tip = "Straightforward drive; plan one rest stop"
                self.is_overnight = False
            elif duration <= 8:
                self.suggested_departure = "06:00 - 07:00 (early start)"
                arrival_hour = 6 + duration + 1  # Add break time
                self.estimated_arrival = f"~{arrival_hour:.0f}:00"
                self.booking_tip = "Long drive - plan 2-3 rest stops; consider sharing driving"
                self.is_overnight = False
            else:
                self.suggested_departure = "Early morning with planned overnight stop"
                self.estimated_arrival = "Next day recommended"
                self.is_overnight = True
                self.booking_tip = "Break journey with overnight stay midway for safety"
                
        elif mode == "ferry":
            if duration <= 4:
                self.suggested_departure = "Morning departure (check ferry schedule)"
                self.estimated_arrival = f"~{duration + 2:.0f}h after boarding"
                self.booking_tip = "Book ferry in advance during peak season"
                self.is_overnight = False
            else:
                self.suggested_departure = "Evening departure for overnight ferry"
                self.estimated_arrival = "Next morning"
                self.is_overnight = True
                self.booking_tip = "Book cabin for overnight ferry for comfortable rest"
    
    def get_enriched_notes(self) -> str:
        """Generate comprehensive transport notes."""
        notes = []
        
        if self.llm_notes:
            notes.append(self.llm_notes)
        
        if self.is_verified and self.driving_distance_km:
            notes.append(f"Distance: ~{self.driving_distance_km:.0f}km")
            
            if self.driving_duration_hours and self.driving_duration_hours > 8:
                notes.append("Consider breaking journey or flying")
        
        if self.verification_note:
            notes.append(self.verification_note)
            
        return " | ".join(notes) if notes else ""


class TransportValidator:
    """
    Validates inter-city transport using Google APIs.
    
    Workflow:
    1. Geocode each city to get coordinates
    2. Calculate driving distances/times via Routes API
    3. Compare with LLM estimates
    4. Flag unrealistic routes
    """
    
    def __init__(
        self,
        places_service: Optional[GooglePlacesService] = None,
        routes_service: Optional[GoogleRoutesService] = None,
    ):
        self.places = places_service or GooglePlacesService()
        self.routes = routes_service or GoogleRoutesService()
        self._coord_cache: dict[str, Location] = {}
    
    async def get_city_coordinates(self, city: str) -> Optional[Location]:
        """
        Get coordinates for a city using Places API.
        
        Results are cached for the session.
        """
        if city in self._coord_cache:
            return self._coord_cache[city]
        
        try:
            destination = await self.places.geocode(city)
            location = destination.location
            self._coord_cache[city] = location
            logger.info(f"[TransportValidator] Geocoded {city}: {location.lat}, {location.lng}")
            return location
        except Exception as e:
            logger.warning(f"[TransportValidator] Failed to geocode {city}: {e}")
            return None
    
    async def validate_transport(
        self,
        from_city: str,
        to_city: str,
        llm_mode: str,
        llm_duration_hours: float,
        llm_notes: Optional[str] = None,
    ) -> ValidatedTransport:
        """
        Validate transport between two cities.
        
        Gets driving distance/time from Google and compares with LLM estimate.
        """
        result = ValidatedTransport(
            llm_mode=llm_mode,
            llm_duration_hours=llm_duration_hours,
            llm_notes=llm_notes,
        )
        
        # Get coordinates for both cities
        from_coords, to_coords = await asyncio.gather(
            self.get_city_coordinates(from_city),
            self.get_city_coordinates(to_city),
        )
        
        if not from_coords or not to_coords:
            result.verification_note = "Could not verify route (geocoding failed)"
            return result
        
        # Get driving route
        try:
            route = await self.routes.compute_route(
                origin=from_coords,
                destination=to_coords,
                mode=TravelMode.DRIVE,
            )
            
            result.driving_duration_hours = route.duration_seconds / 3600
            result.driving_distance_km = route.distance_meters / 1000
            result.is_verified = True
            
            logger.info(
                f"[TransportValidator] {from_city} → {to_city}: "
                f"{result.driving_distance_km:.0f}km, {result.driving_duration_hours:.1f}h drive"
            )
            
            # Add suggestions based on distance
            if result.driving_distance_km > 600:
                if llm_mode != "flight":
                    result.suggested_mode = "flight"
                    result.verification_note = "Very long distance - consider flying"
            elif result.driving_distance_km > 300:
                if llm_mode == "bus" and result.driving_duration_hours > 6:
                    result.verification_note = "Long bus journey - train may be more comfortable"
            
            # Check if LLM estimate is realistic
            if llm_mode == "train":
                # Trains are typically slower than driving
                if llm_duration_hours < result.driving_duration_hours * 0.7:
                    result.verification_note = (
                        f"LLM train estimate ({llm_duration_hours:.1f}h) may be optimistic. "
                        f"Driving takes {result.driving_duration_hours:.1f}h."
                    )
            elif llm_mode == "bus":
                # Buses are similar to or slower than driving
                if llm_duration_hours < result.driving_duration_hours * 0.9:
                    result.verification_note = (
                        f"Bus time may be longer ({result.driving_duration_hours:.1f}h+ likely)"
                    )
                    
        except Exception as e:
            logger.warning(f"[TransportValidator] Route computation failed: {e}")
            result.verification_note = "Could not verify route"
        
        # Compute scheduling recommendations
        result.compute_schedule()
        
        logger.info(
            f"[TransportValidator] Schedule for {from_city} → {to_city}: "
            f"Depart {result.suggested_departure}, Arrive {result.estimated_arrival}"
            f"{' (overnight)' if result.is_overnight else ''}"
        )
        
        return result
    
    async def validate_journey_transports(
        self,
        legs: list[dict],
    ) -> list[ValidatedTransport]:
        """
        Validate all transport segments in a journey.
        
        Args:
            legs: List of journey legs with transport_to_next info
            
        Returns:
            List of validated transports (one less than number of legs)
        """
        validations = []
        
        for i in range(len(legs) - 1):
            from_city = legs[i].get("destination", "")
            to_city = legs[i + 1].get("destination", "")
            transport = legs[i].get("transport_to_next", {})
            
            if not transport or not from_city or not to_city:
                continue
                
            validated = await self.validate_transport(
                from_city=from_city,
                to_city=to_city,
                llm_mode=transport.get("mode", "train"),
                llm_duration_hours=transport.get("duration_hours", 2),
                llm_notes=transport.get("notes"),
            )
            validations.append(validated)
        
        return validations
