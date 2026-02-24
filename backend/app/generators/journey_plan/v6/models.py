"""V6 Journey Planner Models.

V6 Architecture: LLM-First with Iterative Refinement
- Scout: LLM generates initial journey (cities, highlights, travel)
- Enricher: Google APIs ground plan with real data
- Reviewer: Evaluates if trip is humanly feasible
- Planner: Corrects based on reviewer feedback
- Loop until reviewer is satisfied
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class TransportMode(str, Enum):
    """Available transport modes."""
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    DRIVE = "drive"


@dataclass
class CityHighlight:
    """A highlight/attraction within a city."""
    name: str
    description: str
    category: str  # food, culture, nature, history, etc.
    suggested_duration_hours: float = 2.0


@dataclass
class TravelLeg:
    """Travel between two cities."""
    from_city: str
    to_city: str
    mode: TransportMode
    duration_hours: float
    distance_km: Optional[float] = None
    notes: str = ""  # e.g., "Morning Shatabdi recommended"
    
    # Enriched data from Google/LLM
    route_polyline: Optional[str] = None
    estimated_cost: Optional[str] = None
    booking_tip: Optional[str] = None


@dataclass
class CityStop:
    """A city stop in the journey."""
    name: str
    country: str
    days: int
    highlights: list[CityHighlight] = field(default_factory=list)
    why_visit: str = ""
    best_time_to_visit: str = ""
    
    # Enriched data from Google
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None


@dataclass
class JourneyPlan:
    """Complete journey plan from Scout/Planner."""
    theme: str
    summary: str
    cities: list[CityStop]
    travel_legs: list[TravelLeg]
    total_days: int
    
    # Metadata
    origin: str = ""
    region: str = ""
    
    @property
    def route_string(self) -> str:
        """Get route as string: City1 → City2 → City3."""
        city_names = [self.origin] + [c.name for c in self.cities]
        return " → ".join(city_names)
    
    @property
    def city_names(self) -> list[str]:
        """List of city names in order."""
        return [c.name for c in self.cities]


@dataclass
class ReviewIssue:
    """A specific issue found by the reviewer."""
    severity: str  # "critical", "major", "minor"
    category: str  # "timing", "routing", "transport", "balance", "interest_alignment", "safety", "seasonal"
    description: str
    affected_leg: Optional[int] = None  # Index of affected travel leg
    affected_city: Optional[int] = None  # Index of affected city
    suggested_fix: str = ""


@dataclass
class ReviewResult:
    """Result of journey review."""
    is_acceptable: bool
    score: int  # 0-100
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    iteration: int = 1
    
    @property
    def critical_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity == "critical"]
    
    @property
    def major_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity == "major"]
    
    @property
    def warnings(self) -> list[ReviewIssue]:
        """Return major issues (backward-compatible alias)."""
        return self.major_issues


@dataclass
class EnrichedPlan:
    """Journey plan enriched with Google API data."""
    plan: JourneyPlan
    directions_available: bool = True
    total_travel_hours: float = 0.0
    total_distance_km: float = 0.0
    
    # Raw direction data for each leg
    direction_data: dict = field(default_factory=dict)


@dataclass
class V6Progress:
    """Progress tracking for streaming."""
    phase: str  # "scout", "enrich", "review", "plan", "complete", "error"
    step: str
    message: str
    progress: int  # 0-100
    iteration: int = 1
    data: Optional[dict] = None
