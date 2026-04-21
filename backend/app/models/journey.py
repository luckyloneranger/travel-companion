from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from app.models.common import Pace, Budget


class JourneyRequest(BaseModel):
    destination: str = Field(min_length=1)
    origin: str | None = None
    start_date: date
    total_days: int = Field(ge=1, le=30)
    pace: Pace = Pace.MODERATE
    budget: Budget = Budget.MODERATE
    travelers: dict = Field(default_factory=lambda: {"adults": 2})


class CityAllocation(BaseModel):
    city_name: str
    country: str | None = None
    day_count: int
    order: int


class JourneyResponse(BaseModel):
    id: UUID
    destination: str
    origin: str | None = None
    start_date: date
    total_days: int
    pace: str
    budget: str
    travelers: dict
    status: str
    city_sequence: list[dict]
    transport_legs: list[dict] | None = None
    weather_forecasts: list[dict] | None = None
    cost_breakdown: dict | None = None
    created_at: datetime


class JourneySummary(BaseModel):
    id: UUID
    destination: str
    start_date: date
    total_days: int
    city_count: int
    status: str
    created_at: datetime
