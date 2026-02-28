"""Pydantic models for itinerary data structures."""

from datetime import date, time
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Pace(str, Enum):
    """Trip pace options."""

    RELAXED = "relaxed"
    MODERATE = "moderate"
    PACKED = "packed"


class Budget(str, Enum):
    """Budget level options."""

    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"


class TravelMode(str, Enum):
    """Travel mode options."""

    WALK = "WALK"
    DRIVE = "DRIVE"
    TRANSIT = "TRANSIT"


class GenerationMode(str, Enum):
    """Itinerary generation mode."""

    FAST = "fast"  # Quick single-pass generation


class Location(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class Preferences(BaseModel):
    """User preferences for trip planning."""

    budget: Budget = Budget.MODERATE


class ItineraryRequest(BaseModel):
    """Request model for itinerary generation."""

    destination: str = Field(..., min_length=2, max_length=200)
    start_date: date
    end_date: date
    interests: list[str] = Field(..., min_length=1, max_length=10)
    pace: Pace = Pace.MODERATE
    travel_mode: TravelMode = TravelMode.WALK
    preferences: Optional[Preferences] = None
    mode: GenerationMode = GenerationMode.FAST

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be after start_date")
        if start and (v - start).days > 14:
            raise ValueError("Trip duration cannot exceed 14 days")
        return v

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v: list[str]) -> list[str]:
        valid_interests = {
            "art",
            "history",
            "food",
            "nature",
            "shopping",
            "nightlife",
            "architecture",
            "culture",
            "adventure",
            "relaxation",
            "photography",
            "local",
        }
        normalized = [i.lower().strip() for i in v]
        invalid = set(normalized) - valid_interests
        if invalid:
            raise ValueError(f"Invalid interests: {invalid}. Valid options: {valid_interests}")
        return normalized


class OpeningHours(BaseModel):
    """Structured opening hours for a place."""

    day: int = Field(..., ge=0, le=6)  # 0=Sunday, 6=Saturday
    open_time: str  # "09:00"
    close_time: str  # "18:00"


class PlaceCandidate(BaseModel):
    """A candidate place discovered from Google Places API."""

    place_id: str
    name: str
    address: str
    location: Location
    types: list[str]
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = Field(default=None, ge=0, le=4)
    opening_hours: Optional[list[OpeningHours]] = None
    photo_reference: Optional[str] = None
    business_status: Optional[str] = None
    website: Optional[str] = None
    editorial_summary: Optional[str] = None
    # LLM-estimated visit duration (used by ScheduleBuilder if available)
    suggested_duration_minutes: Optional[int] = None


class Place(BaseModel):
    """A finalized place in the itinerary."""

    place_id: str
    name: str
    address: str
    location: Location
    category: str
    rating: Optional[float] = None
    photo_url: Optional[str] = None
    opening_hours: Optional[list[str]] = None
    website: Optional[str] = None
    phone: Optional[str] = None


class Route(BaseModel):
    """Route information between two places."""

    distance_meters: int
    duration_seconds: int
    duration_text: str
    travel_mode: TravelMode
    polyline: str


class Activity(BaseModel):
    """A scheduled activity in the itinerary."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    time_start: str  # "09:00"
    time_end: str  # "12:00"
    duration_minutes: int
    place: Place
    notes: str = ""
    route_to_next: Optional[Route] = None


class DayPlan(BaseModel):
    """A single day's itinerary."""

    date: date
    day_number: int
    theme: str
    activities: list[Activity]


class Destination(BaseModel):
    """Destination information."""

    name: str
    place_id: str
    location: Location
    country: str
    timezone: str


class TripDates(BaseModel):
    """Trip date information."""

    start: date
    end: date
    duration_days: int


class Summary(BaseModel):
    """Itinerary summary statistics."""

    total_activities: int
    total_distance_km: float
    interests_covered: list[str]
    estimated_cost_range: Optional[str] = None


class QualityScoreResponse(BaseModel):
    """Quality metrics for itinerary responses."""

    meal_timing: float = Field(..., ge=0, le=100)
    geographic_clustering: float = Field(..., ge=0, le=100)
    travel_efficiency: float = Field(..., ge=0, le=100)
    variety: float = Field(..., ge=0, le=100)
    opening_hours: float = Field(..., ge=0, le=100)
    theme_alignment: float = Field(default=0, ge=0, le=100)
    duration_appropriateness: float = Field(default=0, ge=0, le=100)
    overall: float = Field(..., ge=0, le=100)
    grade: Optional[str] = None  # Letter grade like "A", "B+", etc.


class QualityReportResponse(BaseModel):
    """Detailed quality report for itineraries."""
    
    overall_score: float = Field(..., ge=0, le=100)
    overall_grade: str
    scores: QualityScoreResponse
    total_issues: int
    critical_issues: list[str]
    recommendations: list[str]


class ItineraryResponse(BaseModel):
    """Response model for generated itinerary."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    destination: Destination
    trip_dates: TripDates
    days: list[DayPlan]
    summary: Summary
    generated_at: str
    
    # Pristine mode fields
    generation_mode: GenerationMode = GenerationMode.FAST
    quality_score: Optional[QualityScoreResponse] = None
    iterations_used: Optional[int] = None


# Internal models for AI communication


class DayGroup(BaseModel):
    """AI's grouping of places into a day."""

    theme: str
    place_ids: list[str]


class AIPlan(BaseModel):
    """AI's initial plan (selection + grouping)."""

    selected_place_ids: list[str]
    day_groups: list[DayGroup]
    # LLM-estimated durations: place_id -> minutes
    durations: dict[str, int] = {}


class ScheduledActivity(BaseModel):
    """An activity with calculated time slot."""

    place: PlaceCandidate
    start_time: str
    end_time: str
    duration_minutes: int


class OptimizationResult(BaseModel):
    """Result of route optimization."""

    places: list[PlaceCandidate]
    total_distance_meters: int
    total_duration_seconds: int


# ═══════════════════════════════════════════════════════════
# On-Demand Tips API Models
# ═══════════════════════════════════════════════════════════


class TipsRequest(BaseModel):
    """Request for generating tips for activities."""
    
    activities: list[dict] = Field(
        ...,
        description="List of activities with place_id, name, category, time_start, duration_minutes",
        examples=[[
            {
                "place_id": "ChIJ...",
                "name": "Colosseum",
                "category": "attraction",
                "time_start": "09:00",
                "duration_minutes": 120,
            }
        ]],
    )
    destination: str = Field(..., description="Destination name for context")


class TipsResponse(BaseModel):
    """Response containing tips for requested activities."""
    
    tips: dict[str, str] = Field(
        default_factory=dict,
        description="Map of place_id to tip text",
    )
