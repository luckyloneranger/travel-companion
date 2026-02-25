"""Day Plan Chat Edit Service - AI-powered day plan modifications.

Handles user requests to modify day-by-day itineraries in real-time via chat interface.
Uses LLM to interpret natural language edit requests and apply them to day plans.
**Now grounded with Google Places API for finding real restaurants and attractions!**
"""

import json
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.services.external import AzureOpenAIService, GooglePlacesService
from app.prompts.loader import day_plan_prompts
from app.models import Location

logger = logging.getLogger(__name__)


class DayPlanChatEditRequest(BaseModel):
    """Request to edit day plans via chat."""
    message: str = Field(..., min_length=1, max_length=1000, description="User's edit request")
    day_plans: list[dict] = Field(..., description="Current day plans to edit")
    context: dict = Field(default_factory=dict, description="Trip context (cities, interests, pace)")


class DayPlanChatEditResponse(BaseModel):
    """Response from day plan chat edit."""
    success: bool = Field(..., description="Whether the edit was successfully applied")
    message: str = Field(..., description="Assistant's response message")
    understood_request: str = Field(default="", description="What the AI understood from the request")
    changes_made: list[str] = Field(default_factory=list, description="List of changes applied")
    updated_day_plans: Optional[list[dict]] = Field(None, description="Updated day plans (if successful)")
    error: Optional[str] = Field(None, description="Error message (if failed)")


class DayPlanChatService:
    """Service for handling day plan edits via chat.
    
    Now grounded with Google Places API - when users want to add activities,
    we search for real places and let the LLM choose from actual options.
    """
    
    # Keywords that suggest the user wants to add new places
    ADD_KEYWORDS = ["add", "include", "put", "schedule", "insert", "want", "need", "missing", "don't have", "no dinner", "no lunch", "no breakfast"]
    PLACE_KEYWORDS = ["restaurant", "dinner", "lunch", "breakfast", "cafe", "coffee", "museum", "attraction", "temple", "beach", "park", "shopping", "bar", "nightlife", "spa", "activity"]
    
    def __init__(self):
        """Initialize the chat service."""
        self.llm = AzureOpenAIService()
        self.places = GooglePlacesService()
    
    def _needs_place_search(self, message: str) -> tuple[bool, str]:
        """
        Check if the message requires searching for real places.
        
        Returns:
            (needs_search, place_type) - whether to search and what type of place
        """
        message_lower = message.lower()
        
        # Check for add-type intent
        has_add_intent = any(kw in message_lower for kw in self.ADD_KEYWORDS)
        
        # Check for place type mentions
        place_type = None
        for pt in self.PLACE_KEYWORDS:
            if pt in message_lower:
                place_type = pt
                break
        
        # If asking about missing meals, infer the place type
        if "dinner" in message_lower or "no dinner" in message_lower:
            place_type = "restaurant"
        elif "lunch" in message_lower:
            place_type = "restaurant"
        elif "breakfast" in message_lower:
            place_type = "cafe"
        elif "coffee" in message_lower:
            place_type = "cafe"
        
        return (has_add_intent and place_type is not None, place_type or "")
    
    def _extract_location_from_plans(self, day_plans: list[dict], target_day: int = -1) -> Optional[Location]:
        """
        Extract a location from the day plans to search near.
        
        Args:
            day_plans: List of day plan dictionaries
            target_day: Which day to search near (-1 for last day)
        """
        if not day_plans:
            return None
        
        # Get the target day
        if target_day < 0:
            target_day = len(day_plans) + target_day
        target_day = max(0, min(target_day, len(day_plans) - 1))
        
        target_plan = day_plans[target_day]
        activities = target_plan.get("activities", [])
        
        if not activities:
            # Try any day with activities
            for plan in day_plans:
                if plan.get("activities"):
                    activities = plan["activities"]
                    break
        
        # Get location from the first activity
        if activities:
            first_activity = activities[0]
            place = first_activity.get("place", {})
            location = place.get("location", {})
            if location.get("lat") and location.get("lng"):
                return Location(lat=location["lat"], lng=location["lng"])
        
        return None
    
    async def _search_real_places(
        self, 
        location: Location, 
        place_type: str,
        max_results: int = 5
    ) -> list[dict]:
        """
        Search for real places using Google Places API.
        
        Returns a list of simplified place dicts for LLM to choose from.
        """
        # Map place types to Google Places search types
        search_types = {
            "restaurant": ["restaurant"],
            "dinner": ["restaurant"],
            "lunch": ["restaurant"],
            "cafe": ["cafe", "coffee_shop"],
            "breakfast": ["cafe", "bakery"],
            "coffee": ["cafe", "coffee_shop"],
            "museum": ["museum"],
            "temple": ["hindu_temple", "buddhist_temple", "place_of_worship"],
            "beach": ["beach"],
            "park": ["park"],
            "shopping": ["shopping_mall", "market"],
            "bar": ["bar", "night_club"],
            "nightlife": ["night_club", "bar"],
            "spa": ["spa"],
            "attraction": ["tourist_attraction"],
        }
        
        types = search_types.get(place_type.lower(), ["tourist_attraction"])
        
        try:
            candidates = await self.places._nearby_search(
                location=location,
                included_types=types,
                radius_meters=5000,  # 5km radius
                max_results=max_results,
            )
            
            # Convert to simple dicts for LLM
            results = []
            for c in candidates:
                results.append({
                    "name": c.name,
                    "category": c.primary_type or place_type,
                    "address": c.address or "",
                    "location": {"lat": c.location.lat, "lng": c.location.lng},
                    "rating": c.rating,
                    "user_ratings_total": c.user_ratings_total,
                    "price_level": c.price_level,
                })
            
            logger.info(f"Found {len(results)} real {place_type} options via Google Places")
            return results
            
        except Exception as e:
            logger.warning(f"Google Places search failed: {e}")
            return []
    
    async def process_edit(self, request: DayPlanChatEditRequest) -> DayPlanChatEditResponse:
        """
        Process a user's edit request and return the modified day plans.
        
        Now with Google Places grounding:
        - Detects if user wants to add new activities
        - Searches for real places via Google API
        - Provides real options to LLM for integration
        
        Args:
            request: The chat edit request with message and current day plans
            
        Returns:
            DayPlanChatEditResponse with the updated day plans or error
        """
        try:
            # Load prompts
            system_prompt = day_plan_prompts.load("chat_edit_system")
            user_template = day_plan_prompts.load("chat_edit_user")
            
            # Extract city names from day plans
            cities = []
            for plan in request.day_plans:
                city = plan.get("city", "")
                if city and city not in cities:
                    cities.append(city)
            
            # Check if we need to search for real places
            needs_search, place_type = self._needs_place_search(request.message)
            real_places = []
            
            if needs_search:
                # Extract location from day plans
                # If message mentions "last day", search near last day's location
                target_day = -1  # Default to last day
                if "first day" in request.message.lower():
                    target_day = 0
                elif "day 1" in request.message.lower():
                    target_day = 0
                elif "day 2" in request.message.lower():
                    target_day = 1
                
                location = self._extract_location_from_plans(request.day_plans, target_day)
                
                if location:
                    real_places = await self._search_real_places(location, place_type)
            
            # Build the user prompt with context
            user_prompt = user_template.format(
                day_plans=json.dumps(request.day_plans, indent=2),
                user_message=request.message,
                cities=", ".join(cities) if cities else "Various",
                interests=", ".join(request.context.get("interests", ["general"])),
                pace=request.context.get("pace", "moderate"),
            )
            
            # If we found real places, add them to the prompt
            if real_places:
                places_info = "\n\n## REAL PLACES AVAILABLE (from Google Places API)\n"
                places_info += "When adding new activities, YOU MUST CHOOSE FROM THESE REAL PLACES:\n"
                places_info += json.dumps(real_places, indent=2)
                places_info += "\n\nUse the exact name, address, location, and rating from above. Do NOT make up places."
                user_prompt += places_info
                logger.info(f"Grounded LLM with {len(real_places)} real places for '{place_type}'")
            
            logger.info(f"Processing day plan chat edit: {request.message[:100]}...")
            
            # Call LLM
            response = await self.llm.chat_completion_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=8192,
            )
            
            # Validate response structure
            if not isinstance(response, dict):
                raise ValueError("Invalid response format from LLM")
            
            updated_plans = response.get("updated_day_plans")
            if not updated_plans or not isinstance(updated_plans, list):
                raise ValueError("LLM did not return updated day plans")
            
            # Validate each day plan has required fields
            for idx, plan in enumerate(updated_plans):
                required_fields = ["date", "day_number", "theme", "activities"]
                for field in required_fields:
                    if field not in plan:
                        raise ValueError(f"Day plan {idx + 1} missing required field: {field}")
            
            changes_made = response.get("changes_made", [])
            if real_places:
                changes_made.append(f"Used real {place_type} from Google Places")
            
            logger.info(f"Day plan chat edit successful: {changes_made}")
            
            return DayPlanChatEditResponse(
                success=True,
                message=response.get("assistant_message", "I've updated your day plans."),
                understood_request=response.get("understood_request", ""),
                changes_made=changes_made,
                updated_day_plans=updated_plans,
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in day plan chat edit: {e}")
            return DayPlanChatEditResponse(
                success=False,
                message="I had trouble understanding that request. Could you try rephrasing it?",
                error=f"JSON decode error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Day plan chat edit failed: {e}", exc_info=True)
            return DayPlanChatEditResponse(
                success=False,
                message="Sorry, I couldn't process that edit. Please try again.",
                error=str(e),
            )
