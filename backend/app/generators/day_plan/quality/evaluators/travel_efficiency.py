"""Travel efficiency quality evaluator."""

from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan


# Maximum acceptable travel time between activities (minutes)
MAX_TRAVEL_MINUTES = 45
IDEAL_TRAVEL_MINUTES = 20

# Maximum acceptable total travel time per day (minutes)
MAX_DAILY_TRAVEL_MINUTES = 120
IDEAL_DAILY_TRAVEL_MINUTES = 60


class TravelEfficiencyEvaluator(BaseEvaluator):
    """
    Evaluates travel time efficiency.
    
    Checks:
    - Travel times between activities are reasonable
    - No excessive commuting
    - Total daily travel time is manageable
    """
    
    @property
    def name(self) -> str:
        return "Travel Efficiency"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["travel_efficiency"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(score=100, issues=[], suggestions=[])
        
        day_scores: list[float] = []
        details = {
            "days_analyzed": len(itinerary.days),
            "total_travel_minutes": 0,
            "avg_daily_travel_minutes": 0.0,
            "max_single_travel_minutes": 0,
            "trips_over_threshold": 0,
        }
        
        for day in itinerary.days:
            day_result = self._evaluate_day(day)
            day_scores.append(day_result["score"])
            details["total_travel_minutes"] += day_result["total_travel"]
            details["max_single_travel_minutes"] = max(
                details["max_single_travel_minutes"],
                day_result["max_travel"]
            )
            details["trips_over_threshold"] += day_result["trips_over_threshold"]
            
            issues.extend(day_result["issues"])
            suggestions.extend(day_result["suggestions"])
        
        if itinerary.days:
            details["avg_daily_travel_minutes"] = float(round(
                details["total_travel_minutes"] / len(itinerary.days), 1
            ))
        
        score = sum(day_scores) / len(day_scores) if day_scores else 100
        
        return self._create_result(
            score=score,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _evaluate_day(self, day: "DayPlan") -> dict:
        """Evaluate travel efficiency for a single day."""
        result = {
            "score": 100.0,
            "total_travel": 0,
            "max_travel": 0,
            "trips_over_threshold": 0,
            "issues": [],
            "suggestions": [],
        }
        
        if len(day.activities) < 2:
            return result
        
        travel_times: list[int] = []
        
        # Extract travel times from route_to_next
        for i, activity in enumerate(day.activities[:-1]):
            if activity.route_to_next:
                travel_minutes = activity.route_to_next.duration_seconds // 60
                travel_times.append(travel_minutes)
                result["total_travel"] += travel_minutes
                result["max_travel"] = max(result["max_travel"], travel_minutes)
                
                if travel_minutes > MAX_TRAVEL_MINUTES:
                    result["trips_over_threshold"] += 1
                    result["issues"].append(
                        f"Day {day.day_number}: {travel_minutes}min travel from "
                        f"'{activity.place.name}' to '{day.activities[i+1].place.name}'"
                    )
                    result["suggestions"].append(
                        f"Day {day.day_number}: Consider reordering activities or using faster transport"
                    )
        
        # Calculate score
        penalty = 0.0
        
        # Penalty for long individual trips
        for travel_time in travel_times:
            if travel_time > MAX_TRAVEL_MINUTES:
                penalty += 20
            elif travel_time > IDEAL_TRAVEL_MINUTES:
                penalty += (travel_time - IDEAL_TRAVEL_MINUTES) * 0.5
        
        # Penalty for excessive daily travel
        if result["total_travel"] > MAX_DAILY_TRAVEL_MINUTES:
            penalty += 25
        elif result["total_travel"] > IDEAL_DAILY_TRAVEL_MINUTES:
            over = result["total_travel"] - IDEAL_DAILY_TRAVEL_MINUTES
            penalty += over * 0.3
        
        result["score"] = max(0, 100 - penalty)
        
        return result
