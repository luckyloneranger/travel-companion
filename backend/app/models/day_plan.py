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


class DayPlan(BaseModel):
    date: str
    day_number: int
    theme: str = ""
    activities: list[Activity] = []
    city_name: str = ""
