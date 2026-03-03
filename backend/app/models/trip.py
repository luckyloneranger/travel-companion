from datetime import date, datetime

from pydantic import BaseModel, Field

from .common import Pace, TravelMode
from .day_plan import DayPlan
from .journey import JourneyPlan


class TripRequest(BaseModel):
    """Unified input for both single-city and multi-city planning."""

    destination: str = Field(..., min_length=2, max_length=200)
    origin: str = ""
    total_days: int = Field(..., ge=1, le=21)
    start_date: date
    interests: list[str] = []
    pace: Pace = Pace.MODERATE
    travel_mode: TravelMode = TravelMode.WALK
    must_include: list[str] = []
    avoid: list[str] = []


class TripSummary(BaseModel):
    id: str
    theme: str
    destination: str
    total_days: int
    cities_count: int
    created_at: datetime
    has_day_plans: bool


class TripResponse(BaseModel):
    id: str
    request: TripRequest
    journey: JourneyPlan
    day_plans: list[DayPlan] | None = None
    quality_score: float | None = None
    created_at: datetime
    updated_at: datetime
