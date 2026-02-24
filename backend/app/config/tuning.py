"""Centralized configuration for tunable parameters.

This file contains all the "magic numbers" and thresholds that can be
adjusted to fine-tune the itinerary generation behavior.

Categories:
- Fast Mode: Single-pass itinerary generation settings
- Discovery: Place search parameters
- Agents: LLM parameters
- Quality Weights: Evaluation scoring weights

Usage:
    from app.config.tuning import FAST_MODE, DISCOVERY, AGENT
    
    # Access values
    enable_validation = FAST_MODE.enable_validation_pass
    search_radius = DISCOVERY.default_radius_km
"""

from dataclasses import dataclass
from typing import Dict


# ═══════════════════════════════════════════════════════════════════════════════
# FAST MODE CONFIGURATION
# Settings for single-pass itinerary generation (quick results)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FastModeConfig:
    """Configuration for FAST mode itinerary generation.
    
    FAST mode generates itineraries quickly using a single AI pass
    followed by deterministic optimization.
    
    Tuning Guide:
    - enable_validation_pass: Set to True for an extra validation step (slower but better)
    - preserve_ai_order: Keep AI's logical ordering vs optimize for distance
    - max_tokens: Token limit for AI responses (higher = more detailed plans)
    """
    
    # Whether to run an additional AI validation pass after initial planning
    # Adds ~20-30s but can improve quality by catching issues
    enable_validation_pass: bool = True
    
    # Whether to preserve AI's logical order or optimize for shortest distance
    # True = Keep AI's thematic ordering (recommended)
    # False = Reorder for minimum travel distance
    preserve_ai_order: bool = True
    
    # Maximum tokens for planning AI response
    max_tokens: int = 64000
    
    # Maximum tokens for validation AI response (if enabled)
    validation_max_tokens: int = 64000
    
    # Temperature for planning (0.0 = deterministic, 1.0 = creative)
    planning_temperature: float = 0.7
    
    # Temperature for validation (lower = more consistent)
    validation_temperature: float = 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# DISCOVERY CONFIGURATION
# Parameters for place discovery and filtering
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DiscoveryConfig:
    """Configuration for place discovery.
    
    PHILOSOPHY: Be inclusive, let LLM decide.
    We want to discover as many places as possible, then let the LLM
    make contextual decisions about what fits the traveler's needs.
    """
    
    # Default search radius (kilometers) - expanded for better coverage
    default_radius_km: float = 20.0
    
    # Maximum results per search request
    max_results_per_search: int = 25
    
    # Minimum rating for quality places (0-5)
    # Lowered to 3.0 to include authentic local spots that may have lower aggregate ratings
    # (famous markets, street food, historic places often have 3.0-3.5)
    min_rating: float = 3.0
    
    # Required reviews for high-rated places (4.0+)
    # Lowered significantly - new/local places deserve a chance
    min_reviews_high_rating: int = 10
    
    # Required reviews for any place
    # Set to 1 - even brand new places should be considered
    min_reviews_any: int = 1
    
    # Maximum candidates to show to AI for planning
    # Increased to give LLM many options for diverse selection
    max_candidates_for_ai: int = 80


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT CONFIGURATION
# LLM-related parameters for agent interactions
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AgentConfig:
    """Configuration for LLM agents."""
    
    # Maximum tokens in response (64K for detailed responses)
    max_tokens: int = 64000
    
    # Temperature for text generation (0.0 = deterministic, 1.0 = creative)
    # Note: Currently disabled in Azure OpenAI calls for Reasoning models
    default_temperature: float = 0.7
    
    # Temperature for JSON output (lower for more consistent structure)
    json_temperature: float = 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULING CONFIGURATION
# Time-related parameters for building daily schedules
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SchedulingConfig:
    """Configuration for schedule building."""
    
    # Buffer time between activities (minutes)
    transition_buffer: int = 15
    
    # Minimum duration for any activity (minutes)
    min_activity_duration: int = 30
    
    # Default day start/end times (HH:MM)
    default_day_start: str = "09:00"
    default_day_end: str = "21:00"
    
    # Meal time windows
    lunch_start: str = "12:00"
    lunch_end: str = "14:00"
    dinner_start: str = "18:30"
    dinner_end: str = "21:00"


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY EVALUATION WEIGHTS
# Weights for final quality scoring (app/quality module)
# ═══════════════════════════════════════════════════════════════════════════════

QUALITY_METRIC_WEIGHTS: Dict[str, float] = {
    "meal_timing": 0.20,
    "geographic_clustering": 0.15,
    "travel_efficiency": 0.15,
    "variety": 0.15,
    "opening_hours": 0.15,
    "theme_alignment": 0.10,
    "duration_appropriateness": 0.10,
}

# Verify weights sum to 1.0
assert abs(sum(QUALITY_METRIC_WEIGHTS.values()) - 1.0) < 0.01, \
    f"Quality weights must sum to 1.0, got {sum(QUALITY_METRIC_WEIGHTS.values())}"


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT INSTANCES
# Pre-configured instances with default values for easy import
# ═══════════════════════════════════════════════════════════════════════════════

FAST_MODE = FastModeConfig()
DISCOVERY = DiscoveryConfig()
AGENT = AgentConfig()
SCHEDULING = SchedulingConfig()


def get_config_summary() -> dict:
    """Get a summary of all configuration values for debugging."""
    return {
        "fast_mode": {
            "enable_validation_pass": FAST_MODE.enable_validation_pass,
            "preserve_ai_order": FAST_MODE.preserve_ai_order,
            "max_tokens": FAST_MODE.max_tokens,
            "planning_temperature": FAST_MODE.planning_temperature,
            "validation_temperature": FAST_MODE.validation_temperature,
        },
        "discovery": {
            "default_radius_km": DISCOVERY.default_radius_km,
            "max_results_per_search": DISCOVERY.max_results_per_search,
            "min_rating": DISCOVERY.min_rating,
            "max_candidates_for_ai": DISCOVERY.max_candidates_for_ai,
        },
        "agent": {
            "max_tokens": AGENT.max_tokens,
            "default_temperature": AGENT.default_temperature,
            "json_temperature": AGENT.json_temperature,
        },
        "scheduling": {
            "transition_buffer": SCHEDULING.transition_buffer,
            "min_activity_duration": SCHEDULING.min_activity_duration,
            "default_day_start": SCHEDULING.default_day_start,
            "default_day_end": SCHEDULING.default_day_end,
            "lunch_window": f"{SCHEDULING.lunch_start}-{SCHEDULING.lunch_end}",
            "dinner_window": f"{SCHEDULING.dinner_start}-{SCHEDULING.dinner_end}",
        },
        "quality_weights": QUALITY_METRIC_WEIGHTS,
    }
