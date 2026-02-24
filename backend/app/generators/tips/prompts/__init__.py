"""Prompts for tips generation.

Now uses centralized prompts from app.prompts folder.
"""

from app.prompts.loader import tips_prompts


def get_tips_system_prompt() -> str:
    """Get the tips system prompt."""
    return tips_prompts.load("tips_system")


def _get_user_prompt_template() -> str:
    """Get the tips user prompt template."""
    return tips_prompts.load("tips_user")


# Pre-load the system prompt at module level
TIPS_SYSTEM_PROMPT = get_tips_system_prompt()


def build_tips_prompt(
    schedule: list[dict],
    destination: str = "",
    interests: list[str] | None = None,
) -> tuple[str, list[str]]:
    """
    Build the user prompt for tips generation.
    
    Args:
        schedule: List of scheduled activities with place_id, time_start, name, category
        destination: Destination city name for contextual tips
        interests: User's interests for personalized tips
        
    Returns:
        Tuple of (formatted user prompt, list of place_ids)
    """
    schedule_lines = []
    place_ids = []
    
    for activity in schedule:
        schedule_lines.append(
            f"[{activity['place_id']}] {activity['time_start']} - {activity['name']} ({activity['category']})"
        )
        place_ids.append(activity['place_id'])
    
    example_id = place_ids[0] if place_ids else "place_id"
    
    return _get_user_prompt_template().format(
        schedule="\n".join(schedule_lines),
        example_id=example_id,
        destination=destination or "the destination",
        interests=", ".join(interests) if interests else "general exploration",
    ), place_ids


__all__ = [
    "TIPS_SYSTEM_PROMPT",
    "build_tips_prompt",
]
