"""Planning prompts for FAST mode itinerary generation.

Now uses centralized prompts from app.prompts folder.
"""

import json
from typing import Any

from app.models import Pace
from app.prompts.loader import day_plan_prompts


def get_planning_system_prompt() -> str:
    """Get the planning system prompt."""
    return day_plan_prompts.load("planning_system")


def _get_user_prompt_template() -> str:
    """Get the planning user prompt template."""
    return day_plan_prompts.load("planning_user")


# Pre-load the system prompt at module level for static analysis
PLANNING_SYSTEM_PROMPT = get_planning_system_prompt()


def build_planning_prompt(
    attractions: list[dict[str, Any]],
    dining: list[dict[str, Any]],
    other: list[dict[str, Any]],
    interests: list[str],
    num_days: int,
    pace: Pace,
    destination: str = "",
    travel_dates: str = "",
) -> str:
    """
    Build the user prompt for itinerary planning.
    
    Args:
        attractions: List of attraction place summaries
        dining: List of dining place summaries
        other: List of other place summaries
        interests: User's interests
        num_days: Number of days in the trip
        pace: Trip pace
        destination: Destination city name for context
        travel_dates: Travel date range for seasonal awareness
        
    Returns:
        Formatted user prompt string
    """
    from app.config.planning import PACE_CONFIGS
    
    config = PACE_CONFIGS[pace]
    
    other_section = ""
    if other:
        other_section = f"=== OTHER ===\n{json.dumps(other[:10], indent=2)}"
    
    return _get_user_prompt_template().format(
        num_days=num_days,
        interests=", ".join(interests),
        pace=pace.value,
        total=config.activities_total,
        attractions=config.attractions_per_day,
        dining=config.dining_per_day,
        attractions_json=json.dumps(attractions[:25], indent=2),
        dining_json=json.dumps(dining[:15], indent=2),
        other_section=other_section,
        destination=destination or "the destination",
        travel_dates=travel_dates or "Flexible dates",
    )
