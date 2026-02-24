"""Fast itinerary generation module.

This module provides quick, single-pass itinerary generation using
a hybrid AI + deterministic approach.

For higher quality iterative generation, see app.generators.day_plan.pristine module.
"""

from app.generators.day_plan.fast.generator import FastItineraryGenerator
from app.generators.day_plan.fast.ai_service import FastAIService

__all__ = ["FastItineraryGenerator", "FastAIService"]
