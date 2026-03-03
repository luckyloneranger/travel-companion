"""Unified chat editing service for journeys and day plans.

Interprets natural language edit requests via LLM and returns
updated plan objects.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.models.chat import ChatEditResponse
from app.models.day_plan import DayPlan
from app.models.journey import JourneyPlan
from app.models.trip import TripRequest
from app.prompts.loader import chat_prompts
from app.services.google.places import GooglePlacesService
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

# Keywords that indicate the user wants to add or change places.
_PLACE_KEYWORDS: set[str] = {
    "add",
    "visit",
    "try",
    "go to",
    "restaurant",
    "cafe",
    "coffee",
    "hotel",
    "museum",
    "park",
    "temple",
    "church",
    "mosque",
    "bar",
    "club",
    "nightlife",
    "market",
    "shop",
    "shopping",
    "gallery",
    "beach",
    "spa",
    "attraction",
    "landmark",
    "monument",
    "food",
    "eat",
    "dine",
    "dining",
    "brunch",
    "lunch",
    "dinner",
    "breakfast",
    "bakery",
    "zoo",
    "aquarium",
    "theater",
    "theatre",
    "stadium",
    "garden",
}


def _needs_place_search(message: str) -> bool:
    """Return True if the user message suggests a place-related edit."""
    lower = message.lower()
    return any(kw in lower for kw in _PLACE_KEYWORDS)


def _format_journey_for_prompt(journey: JourneyPlan) -> str:
    """Serialize a JourneyPlan to a readable JSON string for the prompt."""
    return json.dumps(journey.model_dump(mode="json"), indent=2, default=str)


def _format_day_plans_for_prompt(day_plans: list[DayPlan]) -> str:
    """Serialize day plans to a readable JSON string for the prompt."""
    return json.dumps(
        [dp.model_dump(mode="json") for dp in day_plans],
        indent=2,
        default=str,
    )


def _format_place_results(results: list[dict[str, Any]]) -> str:
    """Format Google Places search results for injection into the prompt."""
    if not results:
        return "No nearby places found."
    lines: list[str] = []
    for r in results[:10]:  # Limit to top 10
        rating = f" (rating: {r['rating']})" if r.get("rating") else ""
        summary = f" - {r['editorial_summary']}" if r.get("editorial_summary") else ""
        lines.append(f"- {r['name']}: {r['address']}{rating}{summary}")
    return "\n".join(lines)


class ChatService:
    """Unified service for editing journeys and day plans via natural language chat."""

    def __init__(self, llm: LLMService, places: GooglePlacesService) -> None:
        self.llm = llm
        self.places = places

    async def edit_journey(
        self,
        message: str,
        journey: JourneyPlan,
        request: TripRequest | None = None,
    ) -> ChatEditResponse:
        """Edit a journey plan via chat.

        Uses the LLM to understand the user's intent and return an updated
        JourneyPlan.

        Args:
            message: The user's natural-language edit request.
            journey: The current journey plan to modify.
            request: Optional original trip request for additional context.

        Returns:
            ChatEditResponse with the updated journey and change summary.
        """
        system_prompt = chat_prompts.load("journey_edit_system")
        user_template = chat_prompts.load("journey_edit_user")

        # Build context variables for the user prompt template.
        origin = journey.origin or (request.origin if request else "")
        region = ""
        interests = ", ".join(request.interests) if request and request.interests else "general"
        pace = request.pace.value if request else "moderate"

        user_prompt = user_template.format(
            current_journey=_format_journey_for_prompt(journey),
            user_message=message,
            origin=origin,
            region=region,
            interests=interests,
            pace=pace,
        )

        logger.info("Journey edit request: %s", message)

        raw = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ChatEditResponse,
            max_tokens=8000,
            temperature=0.7,
        )

        # Build the response from the LLM output.
        updated_journey: JourneyPlan | None = None
        if raw.get("updated_journey"):
            try:
                updated_journey = JourneyPlan.model_validate(raw["updated_journey"])
            except Exception:
                logger.warning("Failed to parse updated_journey from LLM response")

        return ChatEditResponse(
            reply=raw.get("assistant_message", raw.get("understood_request", "")),
            updated_journey=updated_journey,
            updated_day_plans=None,
            changes_made=raw.get("changes_made", []),
        )

    async def edit_day_plans(
        self,
        message: str,
        day_plans: list[DayPlan],
        journey: JourneyPlan,
        request: TripRequest | None = None,
    ) -> ChatEditResponse:
        """Edit day plans via chat.

        Detects place-related requests and, when appropriate, searches
        Google Places for nearby options to inject into the prompt.

        Args:
            message: The user's natural-language edit request.
            day_plans: The current day plans to modify.
            journey: The parent journey for city context.
            request: Optional original trip request for additional context.

        Returns:
            ChatEditResponse with the updated day plans and change summary.
        """
        system_prompt = chat_prompts.load("day_plan_edit_system")
        user_template = chat_prompts.load("day_plan_edit_user")

        # Gather context from journey / request.
        cities = ", ".join(c.name for c in journey.cities) if journey.cities else ""
        interests = ", ".join(request.interests) if request and request.interests else "general"
        pace = request.pace.value if request else "moderate"

        # If the user wants to add/change places, search Google Places.
        place_context = ""
        if _needs_place_search(message):
            place_context = await self._search_relevant_places(message, journey)

        user_prompt = user_template.format(
            day_plans=_format_day_plans_for_prompt(day_plans),
            user_message=message,
            cities=cities,
            interests=interests,
            pace=pace,
        )

        # Append place search results if we found any.
        if place_context:
            user_prompt += (
                "\n\n# Nearby Places (from Google Places)\n"
                "You may use these real places when adding or swapping activities:\n"
                f"{place_context}\n"
            )

        logger.info("Day plan edit request: %s", message)

        raw = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ChatEditResponse,
            max_tokens=12000,
            temperature=0.7,
        )

        # Parse updated day plans from the LLM output.
        updated_day_plans: list[DayPlan] | None = None
        if raw.get("updated_day_plans"):
            try:
                updated_day_plans = [
                    DayPlan.model_validate(dp) for dp in raw["updated_day_plans"]
                ]
            except Exception:
                logger.warning("Failed to parse updated_day_plans from LLM response")

        return ChatEditResponse(
            reply=raw.get("assistant_message", raw.get("understood_request", "")),
            updated_journey=None,
            updated_day_plans=updated_day_plans,
            changes_made=raw.get("changes_made", []),
        )

    # ── Private helpers ──────────────────────────────────────────────────

    async def _search_relevant_places(
        self, message: str, journey: JourneyPlan
    ) -> str:
        """Search Google Places for places relevant to the user's request.

        Uses the first city in the journey as the search location and
        combines the user message with the city name as the query.
        """
        if not journey.cities:
            return ""

        # Use the first city as a default search location.
        city = journey.cities[0]
        query = f"{message} in {city.name}"

        try:
            results = await self.places.text_search(query, max_results=10)
            return _format_place_results(results)
        except Exception:
            logger.warning("Place search failed for chat edit", exc_info=True)
            return ""
