from datetime import date, datetime

from pydantic import BaseModel, Field

from .common import Budget, Pace, TravelMode
from .day_plan import DayPlan
from .journey import JourneyPlan


class Travelers(BaseModel):
    """Group composition for the trip."""
    adults: int = Field(1, ge=1, le=20)
    children: int = Field(0, ge=0, le=10)
    infants: int = Field(0, ge=0, le=5)

    @property
    def total(self) -> int:
        return self.adults + self.children + self.infants

    @property
    def summary(self) -> str:
        parts = [f"{self.adults} adult{'s' if self.adults != 1 else ''}"]
        if self.children:
            parts.append(f"{self.children} child{'ren' if self.children != 1 else ''}")
        if self.infants:
            parts.append(f"{self.infants} infant{'s' if self.infants != 1 else ''}")
        return ", ".join(parts)


class TripRequest(BaseModel):
    """Unified input for both single-city and multi-city planning."""

    destination: str = Field(..., min_length=2, max_length=200)
    origin: str = ""
    total_days: int = Field(..., ge=1, le=21)
    start_date: date
    interests: list[str] = []
    pace: Pace = Pace.MODERATE
    travel_mode: TravelMode = TravelMode.DRIVE
    must_include: list[str] = []
    avoid: list[str] = []
    budget: Budget = Budget.MODERATE
    budget_usd: float | None = None
    home_currency: str = "USD"
    travelers: Travelers = Field(default_factory=Travelers)


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
    cost_breakdown: dict[str, float] | None = None
    created_at: datetime
    updated_at: datetime
