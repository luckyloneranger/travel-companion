"""V6 Journey Planner - LLM-First with Iterative Refinement.

Architecture:
- Scout: LLM generates initial journey (cities + travel) 
- Enricher: Google APIs ground with real data
- Reviewer: Evaluates feasibility
- Planner: Fixes issues based on review
- Loop until acceptable

Day Plans: After journey approval, FastItineraryGenerator creates detailed itineraries.

Key insight: Use LLM for creative/geographic decisions, APIs for real-time data.
"""

from app.generators.journey_plan.v6.models import (
    JourneyPlan,
    EnrichedPlan,
    ReviewResult,
    V6Progress,
    CityStop,
    CityHighlight,
    TravelLeg,
    TransportMode,
)
from app.generators.journey_plan.v6.orchestrator import V6Orchestrator
from app.generators.journey_plan.v6.scout import Scout
from app.generators.journey_plan.v6.enricher import Enricher
from app.generators.journey_plan.v6.reviewer import Reviewer
from app.generators.journey_plan.v6.planner import Planner
from app.generators.journey_plan.v6.day_plan_generator import (
    V6DayPlanGenerator,
    DayPlanProgress,
    CityDayPlans,
    JourneyDayPlansResult,
)

__all__ = [
    "V6Orchestrator",
    "Scout",
    "Enricher", 
    "Reviewer",
    "Planner",
    "JourneyPlan",
    "EnrichedPlan",
    "ReviewResult",
    "V6Progress",
    "CityStop",
    "CityHighlight",
    "TravelLeg",
    "TransportMode",
    # Day plan generation
    "V6DayPlanGenerator",
    "DayPlanProgress",
    "CityDayPlans", 
    "JourneyDayPlansResult",
]
