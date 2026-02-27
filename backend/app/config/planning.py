"""Centralized configuration for itinerary planning parameters."""

from dataclasses import dataclass

from app.models import Pace


@dataclass(frozen=True)
class PaceConfig:
    """Configuration for a specific travel pace."""
    activities_total: str
    attractions_per_day: str
    dining_per_day: str
    places_per_day: int
    duration_multiplier: float


# Pace-specific configurations
PACE_CONFIGS: dict[Pace, PaceConfig] = {
    Pace.RELAXED: PaceConfig(
        activities_total="4-5",
        attractions_per_day="2-3",
        dining_per_day="2",
        places_per_day=4,
        duration_multiplier=1.3,
    ),
    Pace.MODERATE: PaceConfig(
        activities_total="5-7",
        attractions_per_day="3-4",
        dining_per_day="2-3",
        places_per_day=5,
        duration_multiplier=1.0,
    ),
    Pace.PACKED: PaceConfig(
        activities_total="7-9",
        attractions_per_day="5-6",
        dining_per_day="2-3",
        places_per_day=7,
        duration_multiplier=0.8,
    ),
}


# Duration estimates by place type (in minutes)
DURATION_BY_TYPE: dict[str, int] = {
    # Museums and galleries
    "museum": 90,
    "art_gallery": 60,
    
    # Religious/historical sites
    "church": 30,
    "hindu_temple": 45,
    "mosque": 45,
    "place_of_worship": 30,
    "historical_landmark": 45,
    "monument": 30,
    "palace": 60,
    "castle": 60,
    "fort": 60,
    
    # Nature and outdoors
    "park": 60,
    "garden": 45,
    "zoo": 120,
    "aquarium": 90,
    "national_park": 120,
    "beach": 90,
    
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
    
    # Default
    "default": 45,
}


# Interest to Google Place Types mapping
# IMPORTANT: Only use types from Google Places API Table A
# Reference: https://developers.google.com/maps/documentation/places/web-service/place-types#table-a
# EXPANDED: More comprehensive mapping to capture diverse places
INTEREST_TYPE_MAP: dict[str, list[str]] = {
    # Arts & Culture
    "art": ["art_gallery", "museum", "cultural_center"],
    "history": ["museum", "historical_landmark", "monument", "church", "hindu_temple", "mosque", "synagogue"],
    "culture": ["cultural_center", "performing_arts_theater", "museum", "library", "community_center"],
    "architecture": ["church", "historical_landmark", "tourist_attraction", "city_hall", "hindu_temple", "mosque"],
    
    # Food & Dining
    "food": ["restaurant", "cafe", "bakery", "bar", "meal_takeaway", "meal_delivery"],
    "local": ["market", "cafe", "restaurant", "grocery_store", "supermarket"],
    "nightlife": ["night_club", "bar", "casino", "movie_theater", "bowling_alley"],
    
    # Nature & Outdoors
    "nature": ["park", "national_park", "zoo", "aquarium", "campground", "marina"],
    "adventure": ["amusement_park", "tourist_attraction", "aquarium", "zoo", "stadium", "ski_resort"],
    "relaxation": ["spa", "park", "tourist_attraction", "gym", "swimming_pool"],
    "beach": ["tourist_attraction", "park", "marina"],
    
    # Shopping & Markets
    "shopping": ["shopping_mall", "market", "clothing_store", "department_store", "gift_shop", "jewelry_store", "book_store"],
    "markets": ["market", "supermarket", "grocery_store", "convenience_store"],
    
    # Entertainment & Activities
    "entertainment": ["movie_theater", "bowling_alley", "amusement_park", "casino", "night_club"],
    "sports": ["stadium", "sports_club", "gym", "swimming_pool", "golf_course"],
    "family": ["amusement_park", "zoo", "aquarium", "park", "museum", "bowling_alley"],
    
    # Photography & Sightseeing
    "photography": ["tourist_attraction", "historical_landmark", "monument", "park", "church"],
    "sightseeing": ["tourist_attraction", "historical_landmark", "monument", "museum", "park"],
    
    # Wellness
    "wellness": ["spa", "gym", "yoga_studio", "park"],
}


# Fallback values for route optimization
FALLBACK_DISTANCE_METERS: int = 1000
FALLBACK_DURATION_SECONDS: int = 720  # 12 minutes


def get_duration_for_type(place_types: list[str]) -> int:
    """
    Get estimated duration for a place based on its types.
    
    Args:
        place_types: List of Google Places API types
        
    Returns:
        Duration in minutes
    """
    for place_type in place_types:
        type_lower = place_type.lower()
        if type_lower in DURATION_BY_TYPE:
            return DURATION_BY_TYPE[type_lower]
    return DURATION_BY_TYPE["default"]
