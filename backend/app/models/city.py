from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.common import Location


class CityBase(BaseModel):
    name: str
    country: str
    country_code: str = Field(max_length=3)
    location: Location
    timezone: str
    currency: str = Field(max_length=10)
    population_tier: str
    region: str | None = None


class CityCreate(BaseModel):
    name: str
    country: str


class CityResponse(CityBase):
    id: UUID
    variant_count: int = 0
    photo_url: str | None = None
    created_at: datetime


class CityDetailResponse(CityResponse):
    landmarks: list[dict] = []
    available_variants: list[dict] = []
