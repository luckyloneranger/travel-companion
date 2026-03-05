"""Centralized configuration for itinerary planning parameters.

Pace configs, duration-by-type mappings, interest-to-place-type mappings,
journey thresholds, service timeouts, LLM defaults, and place quality filters
used by generators and services throughout the planning pipeline.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Journey orchestration
# ---------------------------------------------------------------------------
MAX_JOURNEY_ITERATIONS: int = 3
MIN_JOURNEY_SCORE: int = 70

# ---------------------------------------------------------------------------
# Service timeouts (seconds)
# ---------------------------------------------------------------------------
HTTP_DEFAULT_TIMEOUT: float = 30.0
HTTP_MAX_RETRIES: int = 3
GOOGLE_API_TIMEOUT: float = 15.0
WEATHER_API_TIMEOUT: float = 10.0

# ---------------------------------------------------------------------------
# LLM defaults
# ---------------------------------------------------------------------------
LLM_DEFAULT_MAX_TOKENS: int = 8000
LLM_DEFAULT_TEMPERATURE: float = 0.7
LLM_SCOUT_TEMPERATURE: float = 0.8
LLM_REVIEWER_MAX_TOKENS: int = 4000
LLM_REVIEWER_TEMPERATURE: float = 0.3

# ---------------------------------------------------------------------------
# Place quality filters
# ---------------------------------------------------------------------------
PLACES_MIN_RATING: float = 3.5
PLACES_MIN_RATINGS_COUNT: int = 30
PLACES_DISCOVERY_RADIUS_KM: float = 5.0

# ---------------------------------------------------------------------------
# Dining type identifiers (shared by scheduler, day_planner, places)
# ---------------------------------------------------------------------------
DINING_TYPES: set[str] = {"restaurant", "cafe", "bakery", "bar", "food", "dining"}

# ---------------------------------------------------------------------------
# Day planner pace guide (stops per day)
# ---------------------------------------------------------------------------
DAY_PLANNER_PACE_GUIDE: dict[str, dict[str, int]] = {
    "relaxed": {"total": 5, "attractions": 3, "dining": 2},
    "moderate": {"total": 7, "attractions": 5, "dining": 2},
    "packed": {"total": 9, "attractions": 7, "dining": 2},
}


@dataclass(frozen=True)
class PaceConfig:
    """Configuration for a specific travel pace."""

    activities_per_day: int
    duration_multiplier: float
    description: str


PACE_CONFIGS: dict[str, PaceConfig] = {
    "relaxed": PaceConfig(
        activities_per_day=4,
        duration_multiplier=1.3,
        description="A leisurely pace with plenty of downtime between activities",
    ),
    "moderate": PaceConfig(
        activities_per_day=6,
        duration_multiplier=1.0,
        description="A balanced pace mixing sightseeing with rest",
    ),
    "packed": PaceConfig(
        activities_per_day=8,
        duration_multiplier=0.8,
        description="An intensive pace maximizing activities per day",
    ),
}


# Map Google Place types to default visit duration in minutes
DURATION_BY_TYPE: dict[str, int] = {
    # Museums and galleries
    "museum": 90,
    "art_gallery": 60,
    # Religious and historical sites
    "church": 30,
    "hindu_temple": 45,
    "temple": 60,
    "mosque": 45,
    "synagogue": 45,
    "place_of_worship": 30,
    "historical_landmark": 45,
    "monument": 30,
    "palace": 60,
    "castle": 60,
    "fort": 60,
    "cemetery": 45,
    # Nature and outdoors
    "park": 60,
    "garden": 45,
    "botanical_garden": 90,
    "zoo": 120,
    "aquarium": 90,
    "national_park": 120,
    "beach": 90,
    "viewpoint": 30,
    "waterfall": 60,
    "lake": 60,
    "mountain": 180,
    "hiking_trail": 180,
    # Entertainment
    "amusement_park": 180,
    "tourist_attraction": 45,
    "stadium": 30,
    "movie_theater": 150,
    "performing_arts_theater": 120,
    # Dining
    "restaurant": 75,
    "cafe": 45,
    "bar": 60,
    "bakery": 20,
    "coffee_shop": 30,
    # Shopping
    "shopping_mall": 90,
    "market": 60,
    "clothing_store": 45,
    # Wellness
    "spa": 120,
    # Education
    "library": 60,
    "university": 60,
    # Default
    "default": 45,
}


# Map user interests to Google Places types for search
# Only uses types from Google Places API (Table A)
INTEREST_TO_TYPES: dict[str, list[str]] = {
    # Arts and culture
    "art": ["art_gallery", "museum", "cultural_center"],
    "history": [
        "museum",
        "historical_landmark",
        "monument",
        "church",
        "hindu_temple",
        "mosque",
        "synagogue",
    ],
    "culture": [
        "cultural_center",
        "performing_arts_theater",
        "museum",
        "library",
        "community_center",
    ],
    "architecture": [
        "church",
        "historical_landmark",
        "tourist_attraction",
        "city_hall",
        "hindu_temple",
        "mosque",
    ],
    # Food and dining
    "food": ["restaurant", "cafe", "bakery", "bar", "meal_takeaway"],
    "local_experience": ["market", "cafe", "restaurant", "grocery_store"],
    "nightlife": ["night_club", "bar", "casino", "movie_theater", "bowling_alley"],
    # Nature and outdoors
    "nature": ["park", "national_park", "zoo", "aquarium", "campground", "marina"],
    "adventure": [
        "amusement_park",
        "tourist_attraction",
        "aquarium",
        "zoo",
        "stadium",
    ],
    "relaxation": ["spa", "park", "tourist_attraction", "gym", "swimming_pool"],
    "beach": ["tourist_attraction", "park", "marina"],
    # Shopping
    "shopping": [
        "shopping_mall",
        "market",
        "clothing_store",
        "department_store",
        "gift_shop",
        "jewelry_store",
        "book_store",
    ],
    "markets": ["market", "supermarket", "grocery_store"],
    # Entertainment and activities
    "entertainment": [
        "movie_theater",
        "bowling_alley",
        "amusement_park",
        "casino",
        "night_club",
    ],
    "sports": ["stadium", "sports_club", "gym", "swimming_pool", "golf_course"],
    "family": [
        "amusement_park",
        "zoo",
        "aquarium",
        "park",
        "museum",
        "bowling_alley",
    ],
    # Photography and sightseeing
    "photography": [
        "tourist_attraction",
        "historical_landmark",
        "monument",
        "park",
        "church",
    ],
    "sightseeing": [
        "tourist_attraction",
        "historical_landmark",
        "monument",
        "museum",
        "park",
    ],
    # Wellness
    "wellness": ["spa", "gym", "yoga_studio", "park"],
}


# Fallback values for route optimization when API calls fail
FALLBACK_DISTANCE_METERS: int = 1000
FALLBACK_DURATION_SECONDS: int = 720  # 12 minutes


def get_duration_for_type(place_types: list[str]) -> int:
    """Get estimated visit duration for a place based on its types.

    Iterates through the place's types and returns the duration for the
    first matching type found in DURATION_BY_TYPE.

    Args:
        place_types: List of Google Places API type strings.

    Returns:
        Duration in minutes.
    """
    for place_type in place_types:
        type_lower = place_type.lower()
        if type_lower in DURATION_BY_TYPE:
            return DURATION_BY_TYPE[type_lower]
    return DURATION_BY_TYPE["default"]
