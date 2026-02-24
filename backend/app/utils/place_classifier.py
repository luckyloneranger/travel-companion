"""Place classification utilities for categorizing Google Places."""

from enum import Enum
from typing import Literal


class PlaceCategory(str, Enum):
    """Category of a place for itinerary planning."""
    DINING = "dining"
    ATTRACTION = "attraction"
    OTHER = "other"


# Google Places API types that indicate dining establishments
DINING_TYPES: frozenset[str] = frozenset({
    "restaurant",
    "cafe",
    "bakery",
    "bar",
    "food",
    "meal_delivery",
    "meal_takeaway",
    "indian_restaurant",
    "chinese_restaurant",
    "italian_restaurant",
    "pizza_restaurant",
    "coffee_shop",
    "fast_food_restaurant",
    "seafood_restaurant",
    "steak_house",
    "vegetarian_restaurant",
    "ice_cream_shop",
    "breakfast_restaurant",
    "brunch_restaurant",
    "fine_dining_restaurant",
    "biryani_restaurant",
    "south_indian_restaurant",
})

# Google Places API types that indicate tourist attractions
ATTRACTION_TYPES: frozenset[str] = frozenset({
    "museum",
    "art_gallery",
    "tourist_attraction",
    "church",
    "park",
    "historical_landmark",
    "monument",
    "amusement_park",
    "hindu_temple",
    "mosque",
    "place_of_worship",
    "zoo",
    "aquarium",
    "stadium",
    "palace",
    "castle",
    "fort",
    "national_park",
    "garden",
    "viewpoint",
    "scenic_point",
    "cultural_center",
    "performing_arts_theater",
    "movie_theater",
})

# Types that should NEVER be classified as dining - even if they have food courts
NEVER_DINING_TYPES: frozenset[str] = frozenset({
    "hindu_temple",
    "mosque",
    "church",
    "place_of_worship",
    "synagogue",
    "buddhist_temple",
    "gurudwara",
    "shrine",
    "museum",
    "art_gallery",
    "tourist_attraction",
    "amusement_park",
    "zoo",
    "aquarium",
    "palace",
    "fort",
    "memorial",
})


def classify_place(
    types: list[str],
    name: str = "",
) -> Literal["dining", "attraction", "other"]:
    """
    Classify a place based on its Google Places types and name.
    
    Args:
        types: List of Google Places API type strings
        name: Place name (used for fallback classification)
        
    Returns:
        Classification as "dining", "attraction", or "other"
    """
    types_lower = {t.lower() for t in types}
    name_lower = name.lower()
    
    # PRIORITY 1: Check for "never dining" types FIRST
    # These places should never be classified as restaurants even if they have food
    for place_type in types_lower:
        for never_dining in NEVER_DINING_TYPES:
            if never_dining in place_type or place_type in never_dining:
                return "attraction"
    
    # PRIORITY 2: Check name for attraction keywords that override dining
    attraction_name_keywords = {"temple", "mandir", "masjid", "mosque", "church", 
                                "museum", "palace", "fort", "memorial", "iskcon",
                                "gurudwara", "shrine"}
    if any(keyword in name_lower for keyword in attraction_name_keywords):
        return "attraction"
    
    # PRIORITY 3: Check for dining types
    for place_type in types_lower:
        for dining_type in DINING_TYPES:
            if dining_type in place_type or place_type in dining_type:
                return "dining"
    
    # Check name for dining keywords
    dining_keywords = {"restaurant", "cafe", "café", "bistro", "eatery", "diner", 
                       "dhaba", "hotel", "biryani", "kitchen"}
    # Exclude "hotel" if it's a lodging (check for other hotel indicators)
    if any(keyword in name_lower for keyword in dining_keywords):
        # Extra check: "hotel" in South India often means restaurant
        # but exclude if it has lodging indicators
        if "hotel" in name_lower and any(x in name_lower for x in ["inn", "resort", "stay", "lodge"]):
            pass  # It's a lodging, not a restaurant
        else:
            return "dining"
    
    # PRIORITY 4: Check for attraction types
    for place_type in types_lower:
        for attraction_type in ATTRACTION_TYPES:
            if attraction_type in place_type or place_type in attraction_type:
                return "attraction"
    
    # Check name for other attraction keywords
    other_attraction_keywords = {"park", "garden", "monument", "gallery", "zoo"}
    if any(keyword in name_lower for keyword in other_attraction_keywords):
        return "attraction"
    
    return "other"


def is_dining(types: list[str], name: str = "") -> bool:
    """Check if a place is a dining establishment."""
    return classify_place(types, name) == "dining"


def is_attraction(types: list[str], name: str = "") -> bool:
    """Check if a place is a tourist attraction."""
    return classify_place(types, name) == "attraction"
