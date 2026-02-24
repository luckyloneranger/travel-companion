"""Geographic utility functions."""

import math


def haversine_distance(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """
    Calculate distance between two points in kilometers using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lng1: Longitude of first point
        lat2: Latitude of second point
        lng2: Longitude of second point
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def estimate_travel_minutes(distance_km: float, mode: str = "walking") -> int:
    """
    Estimate travel time in minutes based on distance.
    
    Args:
        distance_km: Distance in kilometers
        mode: Travel mode - "walking", "transit", "driving"
        
    Returns:
        Estimated travel time in minutes
    """
    # Average speeds (km/h)
    speeds = {
        "walking": 5,
        "transit": 20,  # Urban average including wait times
        "driving": 30,  # Urban average with traffic
    }
    speed = speeds.get(mode, 20)
    return int((distance_km / speed) * 60)
