"""V6 Scout Agent - LLM-only initial journey generation.

The Scout uses pure LLM intelligence to generate a high-quality journey plan.
It suggests CITIES (not attractions) and creates a sensible route.
Features:
- Regional transport intelligence (knows what's popular where)
- Smart city count based on days, pace, and region characteristics

Uses centralized prompts from app.prompts and service from app.services.external.
"""

import logging

from app.config.regional_transport import get_transport_guidance
from app.generators.journey_plan.request import JourneyRequest
from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    CityStop,
    CityHighlight,
    TravelLeg,
    TransportMode,
)
from app.prompts.loader import journey_prompts
from app.services.external import AzureOpenAIService

logger = logging.getLogger(__name__)


class Scout:
    """Generates initial journey plan using LLM intelligence with regional transport awareness.
    
    Uses centralized prompts and OpenAI service for consistent behavior.
    """
    
    def __init__(self):
        """Initialize the Scout with centralized service."""
        self._service = AzureOpenAIService()
        self._system_prompt = journey_prompts.load("scout_system")
        self._user_prompt_template = journey_prompts.load("scout_user")
    
    async def generate_plan(
        self,
        request: JourneyRequest,
    ) -> JourneyPlan:
        """
        Generate initial journey plan using LLM.
        
        The Scout decides the optimal number of cities based on:
        - Total days available
        - Pace preference  
        - Regional distances and characteristics
        
        Args:
            request: Journey request with origin, region, interests, etc.
            
        Returns:
            JourneyPlan with cities and travel legs (not yet enriched)
        """
        total_days = request.get_total_days()
        region = request.region or "surrounding area"
        
        # Build transport guidance with regional intelligence
        transport_guidance = get_transport_guidance(
            request.origin,
            region,
            request.transport_preferences
        )

        # Add return-to-origin guidance if requested
        if request.return_to_origin:
            transport_guidance += (
                f"\n\n**RETURN JOURNEY:** The traveler needs to return to {request.origin} "
                f"at the end of the trip. Include a final travel_leg from the last city back to "
                f"{request.origin}. Choose the most practical transport mode for this return."
            )
        
        # Derive travel dates string
        travel_dates = str(request.start_date) if request.start_date else "Flexible dates"
        
        # Format system prompt with basic context
        system_prompt = self._system_prompt.format(
            region=region,
            total_days=total_days,
            pace=request.pace or "moderate",
            origin=request.origin,
            travel_dates=travel_dates,
        )
        
        # Format user prompt with full request details
        user_prompt = self._user_prompt_template.format(
            origin=request.origin,
            region=region,
            total_days=total_days,
            interests=", ".join(request.interests) if request.interests else "general exploration",
            pace=request.pace or "moderate",
            transport_guidance=transport_guidance,
            travel_dates=travel_dates,
            must_include=", ".join(request.must_include) if request.must_include else "None",
            avoid=", ".join(request.avoid) if request.avoid else "None",
        )
        
        logger.info(f"[Scout] Generating {total_days}-day journey in {region}")
        
        data = await self._service.chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        # Parse cities
        cities = []
        for c in data.get("cities", []):
            highlights = []
            for h in c.get("highlights", []):
                highlights.append(CityHighlight(
                    name=h.get("name", ""),
                    description=h.get("description", ""),
                    category=h.get("category", "culture"),
                    suggested_duration_hours=h.get("suggested_duration_hours", 2.0),
                ))
            
            cities.append(CityStop(
                name=c.get("name", ""),
                country=c.get("country", ""),
                days=c.get("days", 1),
                highlights=highlights,
                why_visit=c.get("why_visit", ""),
                best_time_to_visit=c.get("best_time_to_visit", ""),
            ))
        
        # Parse travel legs
        travel_legs = []
        for leg in data.get("travel_legs", []):
            mode_str = leg.get("mode", "drive").lower()
            try:
                mode = TransportMode(mode_str)
            except ValueError:
                mode = TransportMode.DRIVE
            
            travel_legs.append(TravelLeg(
                from_city=leg.get("from_city", ""),
                to_city=leg.get("to_city", ""),
                mode=mode,
                duration_hours=leg.get("duration_hours", 0),
                distance_km=leg.get("distance_km"),
                notes=leg.get("notes", ""),
                estimated_cost=leg.get("estimated_cost"),
                booking_tip=leg.get("booking_tip"),
            ))
        
        plan = JourneyPlan(
            theme=data.get("theme", "Journey of Discovery"),
            summary=data.get("summary", ""),
            cities=cities,
            travel_legs=travel_legs,
            total_days=total_days,
            origin=request.origin,
            region=region,
        )

        # Validate travel legs count: should be N-1 for N cities
        expected_legs = len(cities) - 1
        if len(travel_legs) != expected_legs and expected_legs > 0:
            logger.warning(
                f"[Scout] Travel legs mismatch: got {len(travel_legs)}, expected {expected_legs} for {len(cities)} cities"
            )

        logger.info(f"[Scout] Generated plan with {len(cities)} cities: {plan.route_string}")
        
        return plan
