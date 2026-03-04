from uuid import uuid4

from pydantic import BaseModel, Field

from .common import Location, TravelMode


class Place(BaseModel):
    place_id: str
    name: str
    address: str = ""
    location: Location
    category: str = ""
    rating: float | None = None
    photo_url: str | None = None
    photo_urls: list[str] = []
    opening_hours: list[str] = []
    website: str | None = None


class Route(BaseModel):
    distance_meters: int = 0
    duration_seconds: int = 0
    duration_text: str = ""
    travel_mode: TravelMode = TravelMode.WALK
    polyline: str | None = None


class Activity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    time_start: str
    time_end: str
    duration_minutes: int
    place: Place
    notes: str = ""
    route_to_next: Route | None = None
    weather_warning: str | None = None
    estimated_cost_local: str | None = None
    estimated_cost_usd: float | None = None
    price_tier: str | None = None


class Weather(BaseModel):
    """Daily weather forecast for a day plan."""
    temperature_high_c: float
    temperature_low_c: float
    condition: str = ""
    precipitation_chance_percent: int = Field(default=0, ge=0, le=100)
    wind_speed_kmh: float = 0.0
    humidity_percent: int = Field(default=0, ge=0, le=100)
    uv_index: int | None = None


class DayPlan(BaseModel):
    date: str
    day_number: int
    theme: str = ""
    activities: list[Activity] = []
    city_name: str = ""
    weather: Weather | None = None
    daily_cost_usd: float | None = None
