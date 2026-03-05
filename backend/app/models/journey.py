from pydantic import BaseModel, Field

from .common import Location, TransportMode


class Accommodation(BaseModel):
    name: str
    address: str = ""
    location: Location | None = None
    place_id: str | None = None
    rating: float | None = None
    photo_url: str | None = None
    price_level: int | None = None
    estimated_nightly_usd: float | None = None


class CityHighlight(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    suggested_duration_hours: float | None = None
    excursion_type: str | None = None
    excursion_days: int | None = None


class CityStop(BaseModel):
    name: str
    country: str
    days: int
    highlights: list[CityHighlight] = []
    why_visit: str = ""
    best_time_to_visit: str = ""
    location: Location | None = None
    place_id: str | None = None
    accommodation: Accommodation | None = None


class TravelLeg(BaseModel):
    from_city: str
    to_city: str
    mode: TransportMode
    duration_hours: float = 0
    distance_km: float | None = None
    notes: str = ""
    fare: str | None = None
    fare_usd: float | None = None
    operator: str | None = None
    booking_tip: str | None = None
    polyline: str | None = None
    num_transfers: int = 0
    departure_time: str | None = None
    arrival_time: str | None = None


class ReviewIssue(BaseModel):
    severity: str
    category: str
    description: str
    affected_leg: int | None = None
    affected_city: int | None = None
    suggested_fix: str = ""


class ReviewResult(BaseModel):
    is_acceptable: bool
    score: int = Field(..., ge=0, le=100)
    issues: list[ReviewIssue] = []
    summary: str = ""
    iteration: int = 1


class JourneyPlan(BaseModel):
    theme: str
    summary: str
    origin: str = ""
    cities: list[CityStop]
    travel_legs: list[TravelLeg] = []
    total_days: int = 0
    total_distance_km: float | None = None
    total_travel_hours: float | None = None
    review_score: float | None = None
    route: str | None = None
