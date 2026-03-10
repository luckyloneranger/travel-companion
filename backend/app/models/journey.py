from pydantic import BaseModel, Field, field_validator, model_validator

from .common import Location, TransportMode


class Accommodation(BaseModel):
    name: str
    why: str = ""
    address: str = ""
    location: Location | None = None
    place_id: str | None = None
    rating: float | None = None
    photo_url: str | None = None
    website: str | None = None
    editorial_summary: str | None = None
    price_level: int | None = None
    estimated_nightly_usd: float | None = None
    budget_range_usd: list[float] | None = None
    booking_hint: str | None = None


class ExperienceTheme(BaseModel):
    """A category of experience available at a destination — used by Scout for journey-level planning."""
    theme: str
    category: str
    destination_name: str | None = None
    excursion_type: str | None = None
    excursion_days: int | None = None
    distance_from_city_km: float | None = None
    why: str = ""


class MustSeeAttraction(BaseModel):
    """A globally iconic, must-visit attraction at a destination."""
    name: str
    city_or_region: str
    why_iconic: str


class MustSeeAttractions(BaseModel):
    """LLM-identified must-see attractions for a destination."""
    attractions: list[MustSeeAttraction] = Field(
        ..., min_length=1, max_length=7
    )


class CityHighlight(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    destination_name: str | None = None
    suggested_duration_hours: float | None = None
    excursion_type: str | None = None
    excursion_days: int | None = None


class CityStop(BaseModel):
    name: str
    country: str
    days: int
    highlights: list[CityHighlight] = []
    experience_themes: list[ExperienceTheme] = []
    why_visit: str = ""
    best_time_to_visit: str = ""
    location: Location | None = None
    place_id: str | None = None
    accommodation: Accommodation | None = None
    accommodation_alternatives: list[Accommodation] = []

    # Rich context from Scout (used by Reviewer and Planner)
    seasonal_notes: str | None = None
    visa_notes: str | None = None
    altitude_meters: float | None = None
    safety_notes: str | None = None
    timezone_offset_minutes: int | None = None


class TransportSegment(BaseModel):
    """One segment of a multi-modal travel leg."""
    mode: str  # "flight", "drive", "bus", "train", "ferry", "walk"
    from_place: str = ""
    to_place: str = ""
    duration_hours: float = 0
    distance_km: float | None = None
    notes: str = ""
    is_grounded: bool = False

    @model_validator(mode="before")
    @classmethod
    def _accept_from_to_aliases(cls, data: dict) -> dict:
        """Accept 'from'/'to' as aliases for 'from_place'/'to_place'.

        LLMs often return the shorter field names.
        """
        if isinstance(data, dict):
            if "from" in data and "from_place" not in data:
                data["from_place"] = data.pop("from")
            if "to" in data and "to_place" not in data:
                data["to_place"] = data.pop("to")
        return data


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

    segments: list[TransportSegment] = []

    # Visa/border context from Scout
    visa_requirement: str | None = None

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, v: str) -> str:
        """Handle combined modes from LLM (e.g. 'drive+ferry' → 'ferry')."""
        if not isinstance(v, str):
            return v
        v = v.strip().lower()
        # If it's already a valid mode, return as-is
        valid = {m.value for m in TransportMode}
        if v in valid:
            return v
        # For combined modes like 'drive+ferry', 'bus+ferry', pick the more
        # specific/interesting mode (ferry > train > flight > bus > drive)
        priority = ["ferry", "train", "flight", "bus", "drive"]
        parts = [p.strip() for p in v.replace("+", ",").replace("/", ",").replace(" and ", ",").split(",")]
        for preferred in priority:
            if preferred in parts:
                return preferred
        # Last resort: return first valid part
        for part in parts:
            if part in valid:
                return part
        return v  # Let Pydantic raise the validation error
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

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, v):
        """Handle LLM returning score as string or float."""
        if isinstance(v, str):
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return 50  # Safe middle-ground default
        if isinstance(v, float):
            return int(v)
        return v
    issues: list[ReviewIssue] = []
    summary: str = ""
    iteration: int = 1
    dimension_scores: dict[str, int] = {}


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
