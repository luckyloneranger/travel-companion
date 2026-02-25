"""Prompt loader for .md template files.

Provides centralized loading and caching of prompt templates.
"""

from functools import lru_cache
from pathlib import Path

# Base path for all prompts
PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(category: str, name: str) -> str:
    """Load a prompt template from file.
    
    Args:
        category: Prompt category (journey, day_plan, tips)
        name: Prompt name without extension (e.g., 'scout_system')
        
    Returns:
        Prompt content as string
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = PROMPTS_DIR / category / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


class PromptLoader:
    """Helper class for loading prompts from a specific category."""
    
    def __init__(self, category: str):
        """Initialize loader for a category.
        
        Args:
            category: Prompt category (journey, day_plan, tips)
        """
        self.category = category
    
    def load(self, name: str) -> str:
        """Load a prompt by name.
        
        Args:
            name: Prompt name without extension
            
        Returns:
            Prompt content
        """
        return load_prompt(self.category, name)


# Pre-configured loaders for each category
journey_prompts = PromptLoader("journey")
day_plan_prompts = PromptLoader("day_plan")
tips_prompts = PromptLoader("tips")
