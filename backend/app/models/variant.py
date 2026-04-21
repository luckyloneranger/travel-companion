from pydantic import BaseModel
from uuid import UUID
from datetime import time


class ActivityResponse(BaseModel):
    id: UUID
    place_id: UUID
    place_name: str
    place_address: str | None = None
    place_location: dict
    place_rating: float | None = None
    place_photo_url: str | None = None
    place_types: list[str] = []
    place_opening_hours: list[dict] | None = None
    sequence: int
    start_time: time
    end_time: time
    duration_minutes: int
    category: str
    description: str | None = None
    is_meal: bool = False
    meal_type: str | None = None
    estimated_cost_usd: float | None = None


class RouteResponse(BaseModel):
    from_activity_sequence: int
    to_activity_sequence: int
    travel_mode: str
    distance_meters: int
    duration_seconds: int
    polyline: str | None = None


class DayPlanResponse(BaseModel):
    day_number: int
    theme: str
    theme_description: str | None = None
    activities: list[ActivityResponse] = []
    routes: list[RouteResponse] = []


class VariantSummary(BaseModel):
    id: UUID
    pace: str
    budget: str
    day_count: int
    quality_score: int | None = None
    cost_total: float | None = None
    status: str


class VariantDetailResponse(BaseModel):
    id: UUID
    city_id: UUID
    city_name: str
    pace: str
    budget: str
    day_count: int
    quality_score: int | None = None
    status: str
    accommodation: dict | None = None
    accommodation_alternatives: list[dict] = []
    booking_hint: str | None = None
    cost_breakdown: dict | None = None
    day_plans: list[DayPlanResponse] = []
