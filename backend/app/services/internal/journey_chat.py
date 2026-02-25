"""Journey Chat Edit Service - AI-powered journey modifications.

Handles user requests to modify journey plans in real-time via chat interface.
Uses LLM to interpret natural language edit requests and apply them to the journey.
"""

import json
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.services.external import AzureOpenAIService
from app.prompts.loader import journey_prompts

logger = logging.getLogger(__name__)


class ChatEditRequest(BaseModel):
    """Request to edit a journey via chat."""
    message: str = Field(..., min_length=1, max_length=1000, description="User's edit request")
    journey: dict = Field(..., description="Current journey plan to edit")
    context: dict = Field(default_factory=dict, description="Original trip context (origin, interests, pace)")


class ChatEditResponse(BaseModel):
    """Response from journey chat edit."""
    success: bool = Field(..., description="Whether the edit was successfully applied")
    message: str = Field(..., description="Assistant's response message")
    understood_request: str = Field(default="", description="What the AI understood from the request")
    changes_made: list[str] = Field(default_factory=list, description="List of changes applied")
    updated_journey: Optional[dict] = Field(None, description="Updated journey plan (if successful)")
    error: Optional[str] = Field(None, description="Error message (if failed)")


class JourneyChatService:
    """Service for handling journey plan edits via chat."""
    
    def __init__(self):
        """Initialize the chat service."""
        self.llm = AzureOpenAIService()
    
    async def process_edit(self, request: ChatEditRequest) -> ChatEditResponse:
        """
        Process a user's edit request and return the modified journey.
        
        Args:
            request: The chat edit request with message and current journey
            
        Returns:
            ChatEditResponse with the updated journey or error
        """
        try:
            # Load prompts
            system_prompt = journey_prompts.load("chat_edit_system")
            user_template = journey_prompts.load("chat_edit_user")
            
            # Build the user prompt with context
            user_prompt = user_template.format(
                current_journey=json.dumps(request.journey, indent=2),
                user_message=request.message,
                origin=request.context.get("origin", request.journey.get("origin", "Unknown")),
                region=request.context.get("region", request.journey.get("region", "Unknown")),
                interests=", ".join(request.context.get("interests", ["general"])),
                pace=request.context.get("pace", "moderate"),
            )
            
            logger.info(f"Processing chat edit: {request.message[:100]}...")
            
            # Call LLM
            response = await self.llm.chat_completion_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )
            
            # Validate response structure
            if not isinstance(response, dict):
                raise ValueError("Invalid response format from LLM")
            
            updated_journey = response.get("updated_journey")
            if not updated_journey:
                raise ValueError("LLM did not return an updated journey")
            
            # Validate journey has required fields
            required_fields = ["theme", "cities", "travel_legs", "total_days"]
            for field in required_fields:
                if field not in updated_journey:
                    raise ValueError(f"Updated journey missing required field: {field}")
            
            # Ensure total_days matches sum of city days
            city_days_sum = sum(city.get("days", 0) for city in updated_journey.get("cities", []))
            updated_journey["total_days"] = city_days_sum
            
            # Update route string if not present
            if "route" not in updated_journey or not updated_journey["route"]:
                cities = updated_journey.get("cities", [])
                city_names = [c.get("name", "Unknown") for c in cities]
                updated_journey["route"] = " → ".join(city_names)
            
            logger.info(f"Chat edit successful: {response.get('changes_made', [])}")
            
            return ChatEditResponse(
                success=True,
                message=response.get("assistant_message", "I've updated your journey plan."),
                understood_request=response.get("understood_request", ""),
                changes_made=response.get("changes_made", []),
                updated_journey=updated_journey,
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in chat edit: {e}")
            return ChatEditResponse(
                success=False,
                message="I had trouble understanding that request. Could you try rephrasing it?",
                error=f"JSON decode error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Chat edit failed: {e}", exc_info=True)
            return ChatEditResponse(
                success=False,
                message="Sorry, I couldn't process that edit. Please try again.",
                error=str(e),
            )
