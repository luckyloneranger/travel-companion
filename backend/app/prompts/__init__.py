"""Centralized prompt management for all generators.

All prompt templates are stored as .md files and loaded via the loader module.
Prompt folders:
    - journey/: Multi-city journey planning (scout, reviewer, planner)
    - day_plan/: Single-city itinerary planning
    - tips/: Activity tips generation
"""

from app.prompts.loader import PromptLoader

__all__ = ["PromptLoader"]
