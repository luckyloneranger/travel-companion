"""Prompts for FAST mode itinerary generation."""

from app.generators.day_plan.fast.prompts.planning import (
    PLANNING_SYSTEM_PROMPT,
    build_planning_prompt,
)
from app.generators.day_plan.fast.prompts.validation import (
    VALIDATION_SYSTEM_PROMPT,
    build_validation_prompt,
)

__all__ = [
    "PLANNING_SYSTEM_PROMPT",
    "build_planning_prompt",
    "VALIDATION_SYSTEM_PROMPT",
    "build_validation_prompt",
]
