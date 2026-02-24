"""Meal timing quality evaluator."""

from datetime import time
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan


# Ideal meal time windows
BREAKFAST_WINDOW = (time(7, 0), time(9, 30))
LUNCH_WINDOW = (time(12, 0), time(14, 30))
DINNER_WINDOW = (time(18, 30), time(21, 0))

# Acceptable (but not ideal) windows
LUNCH_ACCEPTABLE = (time(11, 0), time(15, 30))
DINNER_ACCEPTABLE = (time(17, 30), time(22, 0))

# Categories that indicate dining
DINING_CATEGORIES = {"dining", "restaurant", "cafe", "food"}


class MealTimingEvaluator(BaseEvaluator):
    """
    Evaluates meal timing quality.
    
    Checks:
    - Each day has lunch and dinner
    - Meals are at appropriate times
    - Meals are proper restaurants (not temples/attractions)
    - Meals are positioned correctly in the schedule
    """
    
    @property
    def name(self) -> str:
        return "Meal Timing"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["meal_timing"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(
                score=0,
                issues=["No days in itinerary"],
                suggestions=["Generate an itinerary with at least one day"],
            )
        
        total_checks = 0
        passed_checks = 0
        
        details = {
            "days_analyzed": len(itinerary.days),
            "lunches_found": 0,
            "dinners_found": 0,
            "meals_at_ideal_time": 0,
            "meals_at_acceptable_time": 0,
        }
        
        for day in itinerary.days:
            day_result = self._evaluate_day(day)
            
            total_checks += day_result["total_checks"]
            passed_checks += day_result["passed_checks"]
            details["lunches_found"] += day_result["lunch_found"]
            details["dinners_found"] += day_result["dinner_found"]
            details["meals_at_ideal_time"] += day_result["ideal_times"]
            details["meals_at_acceptable_time"] += day_result["acceptable_times"]
            
            issues.extend(day_result["issues"])
            suggestions.extend(day_result["suggestions"])
        
        # Calculate score
        if total_checks == 0:
            score = 0.0
        else:
            score = (passed_checks / total_checks) * 100
        
        return self._create_result(
            score=score,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _evaluate_day(self, day: "DayPlan") -> dict:
        """Evaluate meal timing for a single day."""
        result = {
            "total_checks": 0,
            "passed_checks": 0,
            "lunch_found": 0,
            "dinner_found": 0,
            "ideal_times": 0,
            "acceptable_times": 0,
            "issues": [],
            "suggestions": [],
        }
        
        # Find dining activities
        dining_activities = []
        for activity in day.activities:
            category = activity.place.category.lower() if activity.place.category else ""
            if category in DINING_CATEGORIES:
                dining_activities.append(activity)
        
        # Check 1: Has lunch?
        result["total_checks"] += 1
        lunch = self._find_meal_in_window(dining_activities, LUNCH_ACCEPTABLE)
        if lunch:
            result["lunch_found"] = 1
            result["passed_checks"] += 1
            
            # Bonus: Is it at ideal time?
            lunch_time = self._parse_time(lunch.time_start)
            if lunch_time and self._in_window(lunch_time, LUNCH_WINDOW):
                result["ideal_times"] += 1
            elif lunch_time and self._in_window(lunch_time, LUNCH_ACCEPTABLE):
                result["acceptable_times"] += 1
        else:
            result["issues"].append(f"Day {day.day_number}: No lunch found between 11:00-15:30")
            result["suggestions"].append(f"Day {day.day_number}: Add a lunch restaurant around 12:00-14:00")
        
        # Check 2: Has dinner?
        result["total_checks"] += 1
        dinner = self._find_meal_in_window(dining_activities, DINNER_ACCEPTABLE)
        if dinner:
            result["dinner_found"] = 1
            result["passed_checks"] += 1
            
            # Bonus: Is it at ideal time?
            dinner_time = self._parse_time(dinner.time_start)
            if dinner_time and self._in_window(dinner_time, DINNER_WINDOW):
                result["ideal_times"] += 1
            elif dinner_time and self._in_window(dinner_time, DINNER_ACCEPTABLE):
                result["acceptable_times"] += 1
        else:
            result["issues"].append(f"Day {day.day_number}: No dinner found between 17:30-22:00")
            result["suggestions"].append(f"Day {day.day_number}: Add a dinner restaurant around 19:00-20:30")
        
        # Check 3: Lunch position (should be mid-day, not first or last)
        if lunch and len(day.activities) >= 3:
            result["total_checks"] += 1
            lunch_idx = day.activities.index(lunch) if lunch in day.activities else -1
            if lunch_idx == -1:
                # Find by matching
                for i, act in enumerate(day.activities):
                    if act.time_start == lunch.time_start and act.place.name == lunch.place.name:
                        lunch_idx = i
                        break
            
            if 1 <= lunch_idx <= len(day.activities) - 2:
                result["passed_checks"] += 1
            else:
                result["issues"].append(f"Day {day.day_number}: Lunch at position {lunch_idx + 1} (should be mid-day)")
        
        # Check 4: Dinner position (should be near end)
        if dinner and len(day.activities) >= 3:
            result["total_checks"] += 1
            dinner_idx = -1
            for i, act in enumerate(day.activities):
                if act.time_start == dinner.time_start and act.place.name == dinner.place.name:
                    dinner_idx = i
                    break
            
            if dinner_idx >= len(day.activities) - 2:
                result["passed_checks"] += 1
            else:
                result["issues"].append(f"Day {day.day_number}: Dinner at position {dinner_idx + 1} (should be near end)")
        
        # Check 5: No dining misclassification (temples as restaurants)
        for activity in dining_activities:
            result["total_checks"] += 1
            name_lower = activity.place.name.lower()
            
            # Check for religious place names being classified as dining
            non_restaurant_keywords = {
                "temple", "mandir", "masjid", "mosque", "church", "iskcon",
                "museum", "palace", "fort", "memorial", "gurudwara", "shrine"
            }
            
            is_misclassified = any(kw in name_lower for kw in non_restaurant_keywords)
            
            if not is_misclassified:
                result["passed_checks"] += 1
            else:
                result["issues"].append(
                    f"Day {day.day_number}: '{activity.place.name}' appears to be a non-restaurant classified as dining"
                )
                result["suggestions"].append(
                    f"Day {day.day_number}: Replace with an actual restaurant"
                )
        
        return result
    
    def _find_meal_in_window(
        self, 
        dining_activities: list, 
        window: tuple[time, time]
    ):
        """Find a dining activity within the specified time window."""
        for activity in dining_activities:
            activity_time = self._parse_time(activity.time_start)
            if activity_time and self._in_window(activity_time, window):
                return activity
        return None
    
    def _parse_time(self, time_str: str) -> time | None:
        """Parse time string like '12:30' to time object."""
        try:
            parts = time_str.split(":")
            return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError):
            return None
    
    def _in_window(self, t: time, window: tuple[time, time]) -> bool:
        """Check if time is within window (inclusive)."""
        return window[0] <= t <= window[1]
