from pydantic import BaseModel, Field

from .common import Location


class OpeningHours(BaseModel):
    day: int = Field(..., ge=0, le=6)
    open_time: str
    close_time: str


class PlaceCandidate(BaseModel):
    place_id: str
    name: str
    address: str
    location: Location
    types: list[str] = []
    rating: float | None = None
    user_ratings_total: int | None = None
    price_level: int | None = Field(default=None, ge=0, le=4)
    opening_hours: list[OpeningHours] | None = None
    business_status: str | None = None
    photo_reference: str | None = None
    photo_references: list[str] = []
    website: str | None = None
    editorial_summary: str | None = None
    suggested_duration_minutes: int | None = None
    good_for_children: bool | None = None
    good_for_groups: bool | None = None
    serves_vegetarian_food: bool | None = None
    serves_brunch: bool | None = None
    serves_lunch: bool | None = None
    serves_dinner: bool | None = None


class DayGroup(BaseModel):
    theme: str
    place_ids: list[str]


class AIPlan(BaseModel):
    selected_place_ids: list[str]
    day_groups: list[DayGroup]
    durations: dict[str, int] = {}
    cost_estimates: dict[str, float] = {}
