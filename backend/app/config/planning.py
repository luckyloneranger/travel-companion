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
# Day plan orchestration
# ---------------------------------------------------------------------------
MAX_DAY_PLAN_ITERATIONS: int = 2
MIN_DAY_PLAN_SCORE: int = 70
DAY_PLAN_BATCH_SIZE: int = 3
MAX_CONCURRENT_CITIES: int = 3

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
LLM_DEFAULT_MAX_TOKENS: int = 64000
LLM_DEFAULT_TEMPERATURE: float = 0.7
LLM_SCOUT_TEMPERATURE: float = 0.8
LLM_REVIEWER_MAX_TOKENS: int = 64000
LLM_REVIEWER_TEMPERATURE: float = 0.3

# ---------------------------------------------------------------------------
# Place quality filters
# ---------------------------------------------------------------------------
PLACES_MIN_RATING: float = 3.5
PLACES_MIN_RATINGS_COUNT: int = 30
PLACES_DISCOVERY_RADIUS_KM: float = 5.0


def get_adaptive_place_filters(result_count: int = 0) -> dict[str, float | int]:
    """Return place quality filters adapted to discovery result density.

    When few results are found, thresholds are lowered to include hidden
    gems and emerging destinations. When many results exist, thresholds
    are tightened to surface the best options.
    """
    if result_count > 0 and result_count < 15:
        return {"min_rating": 3.0, "min_ratings_count": 10, "radius_km": 8.0}
    if result_count > 100:
        return {"min_rating": 4.0, "min_ratings_count": 50, "radius_km": 3.0}
    return {
        "min_rating": PLACES_MIN_RATING,
        "min_ratings_count": PLACES_MIN_RATINGS_COUNT,
        "radius_km": PLACES_DISCOVERY_RADIUS_KM,
    }

# ---------------------------------------------------------------------------
# Dining type identifiers (shared by scheduler, day_planner, places)
# ---------------------------------------------------------------------------
DINING_TYPES: set[str] = {"restaurant", "cafe", "bakery", "bar", "food", "dining"}

# ---------------------------------------------------------------------------
# Lodging type identifiers (used to filter hotels/motels from activity candidates)
# ---------------------------------------------------------------------------
LODGING_TYPES: set[str] = {
    "lodging", "hotel", "resort_hotel", "motel", "inn",
    "bed_and_breakfast", "hostel", "guest_house", "cottage",
    "campground", "extended_stay_hotel", "farm_stay",
}

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


# Base pace configurations. The LLM day planner can override activity counts
# and durations via its response. These serve as defaults for the scheduler
# when LLM estimates are not available.
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


# Last-resort fallback durations only. Priority order:
# 1. LLM-estimated duration (suggested_duration_minutes on PlaceCandidate)
# 2. Google Places API suggested duration
# 3. This fallback table
_FALLBACK_DURATION_BY_TYPE: dict[str, int] = {
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
    "zoo": 240,
    "aquarium": 180,
    "national_park": 120,
    "beach": 90,
    "viewpoint": 30,
    "waterfall": 60,
    "lake": 60,
    "mountain": 180,
    "hiking_trail": 180,
    # Entertainment
    "amusement_park": 480,
    "theme_park": 480,
    "water_park": 300,
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

# Backward-compatible alias — other modules import DURATION_BY_TYPE directly.
DURATION_BY_TYPE = _FALLBACK_DURATION_BY_TYPE


# Seed mapping for Google Places API discovery queries. Not an exhaustive
# taxonomy — the LLM day planner considers ALL discovered places regardless
# of how they were initially found via these type mappings.
# Map user interests to Google Places types for search.
# Only uses types from Google Places API (Table A).
# This is the single source of truth — also imported by places.py.
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
        "cooking_class",
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
    "food": ["restaurant", "cafe", "bakery", "bar", "meal_takeaway", "market", "food_court"],
    "local_experience": ["market", "cafe", "restaurant", "grocery_store"],
    "local": ["market", "cafe", "restaurant"],
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


def compute_haversine_fallback(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
) -> tuple[int, int]:
    """Estimate distance (meters) and walk duration (seconds) from coordinates.

    Uses haversine distance with a 4 km/h walking speed assumption.
    Returns (distance_meters, duration_seconds). Falls back to fixed
    defaults when coordinates are zero/missing.
    """
    import math
    if not (origin_lat and origin_lng and dest_lat and dest_lng):
        return FALLBACK_DISTANCE_METERS, FALLBACK_DURATION_SECONDS

    R = 6_371_000  # Earth radius in meters
    lat1, lat2 = math.radians(origin_lat), math.radians(dest_lat)
    dlat = math.radians(dest_lat - origin_lat)
    dlng = math.radians(dest_lng - origin_lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    distance_m = int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    # Assume 4 km/h walking speed
    duration_s = int(distance_m / (4000 / 3600))
    return distance_m, duration_s


def get_duration_for_type(place_types: list[str]) -> int:
    """Get estimated visit duration for a place based on its types.

    This is a last-resort fallback. Prefer LLM-estimated durations or
    Google Places suggested_duration_minutes when available.
    """
    for place_type in place_types:
        type_lower = place_type.lower()
        if type_lower in _FALLBACK_DURATION_BY_TYPE:
            return _FALLBACK_DURATION_BY_TYPE[type_lower]
    return _FALLBACK_DURATION_BY_TYPE["default"]


def map_themes_to_days(
    themes: list,
    num_days: int,
    blocked_days: dict | None = None,
) -> dict[int, list]:
    """Assign experience themes to day numbers, ensuring coverage.

    1. Excursion themes (multi_day, full_day) go on their blocked days
    2. Evening themes pair with daytime themes on least-loaded days
    3. Remaining themes spread evenly across free days
    4. Empty free days get a repeated theme
    """
    blocked = blocked_days or {}
    day_map: dict[int, list] = {d: [] for d in range(1, num_days + 1)}

    excursion_themes = []
    evening_themes = []
    regular_themes = []

    for t in themes:
        et = getattr(t, 'excursion_type', None)
        if et in ('full_day', 'multi_day'):
            excursion_themes.append(t)
        elif et in ('evening', 'half_day_morning', 'half_day_afternoon'):
            evening_themes.append(t)
        else:
            regular_themes.append(t)

    # Step 1: Excursion themes go on blocked days
    for day_num, exc_highlight in blocked.items():
        matching = [t for t in excursion_themes
                    if hasattr(t, 'theme') and hasattr(exc_highlight, 'name') and
                    (t.theme.lower() in exc_highlight.name.lower()
                     or exc_highlight.name.lower() in t.theme.lower())]
        if matching:
            day_map[day_num].append(matching[0])

    # Step 2: Regular themes spread across free days
    free_days = sorted(d for d in range(1, num_days + 1) if d not in blocked)
    for i, theme in enumerate(regular_themes):
        if free_days:
            day_idx = free_days[i % len(free_days)]
            day_map[day_idx].append(theme)

    # Step 3: Evening/half-day themes pair with least-loaded free days
    for theme in evening_themes:
        if free_days:
            lightest = min(free_days, key=lambda d: len(day_map[d]))
            day_map[lightest].append(theme)

    # Step 4: Empty free days get themes distributed round-robin
    empty_days = [d for d in free_days if not day_map[d]]
    if empty_days and regular_themes:
        for i, d in enumerate(empty_days):
            # Cycle through all regular themes, not just the first
            theme_idx = i % len(regular_themes)
            day_map[d].append(regular_themes[theme_idx])

    return day_map
