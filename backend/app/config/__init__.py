"""Configuration module for the travel companion backend."""

from app.config.settings import Settings, get_settings
from app.config.planning import (
    PaceConfig,
    PACE_CONFIGS,
    DURATION_BY_TYPE,
    INTEREST_TYPE_MAP,
    FALLBACK_DISTANCE_METERS,
    FALLBACK_DURATION_SECONDS,
    get_duration_for_type,
)
from app.config.tuning import (
    FastModeConfig,
    DiscoveryConfig,
    AgentConfig,
    SchedulingConfig,
    FAST_MODE,
    DISCOVERY,
    AGENT,
    SCHEDULING,
    QUALITY_METRIC_WEIGHTS,
    get_config_summary,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Planning config
    "PaceConfig",
    "PACE_CONFIGS",
    "DURATION_BY_TYPE",
    "INTEREST_TYPE_MAP",
    "FALLBACK_DISTANCE_METERS",
    "FALLBACK_DURATION_SECONDS",
    "get_duration_for_type",
    # Tuning config
    "FastModeConfig",
    "DiscoveryConfig",
    "AgentConfig",
    "SchedulingConfig",
    "FAST_MODE",
    "DISCOVERY",
    "AGENT",
    "SCHEDULING",
    "QUALITY_METRIC_WEIGHTS",
    "get_config_summary",
]


