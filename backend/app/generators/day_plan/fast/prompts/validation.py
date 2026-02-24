"""Validation prompts for FAST mode itinerary quality checking.

Now uses centralized prompts from app.prompts folder.
"""

import json
from typing import Any

from app.prompts.loader import day_plan_prompts


def get_validation_system_prompt() -> str:
    """Get the validation system prompt."""
    return day_plan_prompts.load("validation_system")


def _get_user_prompt_template() -> str:
    """Get the validation user prompt template."""
    return day_plan_prompts.load("validation_user")


# Pre-load the system prompt at module level for static analysis
VALIDATION_SYSTEM_PROMPT = get_validation_system_prompt()


def build_validation_prompt(
    plan_data: list[dict[str, Any]],
    available_dining: list[dict[str, Any]],
    available_attractions: list[dict[str, Any]],
    destination: str = "",
    interests: str = "",
    pace: str = "",
    travel_dates: str = "",
) -> str:
    """
    Build the user prompt for plan validation.
    
    Args:
        plan_data: Current plan structure with day/place info
        available_dining: Unused dining places that can be substituted
        available_attractions: Unused attractions that can be substituted
        destination: Destination city name for context
        interests: Comma-separated user interests
        pace: Trip pace (relaxed/moderate/packed)
        travel_dates: Travel date range
        
    Returns:
        Formatted user prompt string
    """
    return _get_user_prompt_template().format(
        plan_json=json.dumps(plan_data),
        dining_json=json.dumps(available_dining[:8]),
        attractions_json=json.dumps(available_attractions[:8]),
        destination=destination or "the destination",
        interests=interests or "general exploration",
        pace=pace or "moderate",
        travel_dates=travel_dates or "Flexible dates",
    )
