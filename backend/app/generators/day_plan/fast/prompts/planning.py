"""Planning prompts for FAST mode itinerary generation.

Now uses centralized prompts from app.prompts folder.
"""

import json
import math
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


def _quality_score(place: dict[str, Any]) -> float:
    """Score a place summary for sorting. Higher = better quality."""
    rating = place.get("rating") or 3.5
    reviews = place.get("reviews") or 1
    return rating * math.log(reviews + 1)


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

    Places are sorted by quality (rating * log(reviews)) before truncation,
    ensuring the LLM sees the best candidates even when there are many.
    """
    from app.config.planning import PACE_CONFIGS

    config = PACE_CONFIGS[pace]

    # Sort by quality before truncating — best places first
    sorted_attractions = sorted(attractions, key=_quality_score, reverse=True)
    sorted_dining = sorted(dining, key=_quality_score, reverse=True)
    sorted_other = sorted(other, key=_quality_score, reverse=True)

    other_section = ""
    if sorted_other:
        other_section = f"=== OTHER ===\n{json.dumps(sorted_other[:10], indent=2)}"

    return _get_user_prompt_template().format(
        num_days=num_days,
        interests=", ".join(interests),
        pace=pace.value,
        total=config.activities_total,
        attractions=config.attractions_per_day,
        dining=config.dining_per_day,
        attractions_json=json.dumps(sorted_attractions[:25], indent=2),
        dining_json=json.dumps(sorted_dining[:15], indent=2),
        other_section=other_section,
        destination=destination or "the destination",
        travel_dates=travel_dates or "Flexible dates",
    )
