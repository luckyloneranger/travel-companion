"""Duration appropriateness quality evaluator."""

from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan, Activity


# Recommended durations by place type/category (in minutes)
RECOMMENDED_DURATIONS = {
    # Museums and galleries - need 1.5-3 hours
    "museum": (90, 180),
    "culture": (60, 150),
    "art_gallery": (60, 120),
    
    # Temples and religious places - 30-90 mins
    "temple": (30, 90),
    "religious": (30, 60),
    "attraction": (45, 120),
    
    # Parks and nature - 45-90 mins
    "park": (45, 90),
    "garden": (30, 60),
    "nature": (45, 90),
    "zoo": (120, 240),
    
    # Landmarks and monuments - 30-60 mins
    "monument": (30, 60),
    "landmark": (30, 60),
    "tourist_attraction": (45, 90),
    
    # Dining - 45-90 mins
    "dining": (45, 90),
    "restaurant": (45, 90),
    "cafe": (30, 60),
    
    # Forts and palaces - need more time
    "fort": (90, 180),
    "palace": (60, 150),
    
    # Default
    "default": (45, 90),
}

# Name-based duration adjustments for famous places
FAMOUS_PLACES_DURATIONS = {
    "salar jung museum": (150, 240),
    "golconda fort": (120, 180),
    "chowmahalla palace": (90, 150),
    "science city": (120, 180),
    "taj mahal": (120, 180),
    "qutub minar": (60, 90),
    "red fort": (90, 150),
    "sabarmati ashram": (60, 90),
    "calico museum": (90, 150),
    "ajanta caves": (180, 300),
    "ellora caves": (180, 300),
}


class DurationEvaluator(BaseEvaluator):
    """
    Evaluates if activity durations are appropriate.
    
    Checks:
    - Durations match place type requirements
    - Major attractions get adequate time
    - No rushed schedules
    - No excessively long single-activity durations
    """
    
    @property
    def name(self) -> str:
        return "Duration Appropriateness"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["duration_appropriateness"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(score=100, issues=[], suggestions=[])
        
        total_activities = 0
        appropriate_durations = 0
        
        details = {
            "activities_checked": 0,
            "too_short": 0,
            "too_long": 0,
            "appropriate": 0,
            "avg_duration_minutes": 0.0,
        }
        
        all_durations = []
        
        for day in itinerary.days:
            for activity in day.activities:
                result = self._check_duration(activity, day.day_number)
                total_activities += 1
                details["activities_checked"] += 1
                all_durations.append(activity.duration_minutes)
                
                if result["status"] == "appropriate":
                    appropriate_durations += 1
                    details["appropriate"] += 1
                elif result["status"] == "too_short":
                    details["too_short"] += 1
                    issues.append(result["issue"])
                    suggestions.append(result["suggestion"])
                elif result["status"] == "too_long":
                    details["too_long"] += 1
                    issues.append(result["issue"])
                    suggestions.append(result["suggestion"])
        
        if all_durations:
            details["avg_duration_minutes"] = float(round(sum(all_durations) / len(all_durations), 1))
        
        # Calculate score
        if total_activities == 0:
            score = 100.0
        else:
            score = (appropriate_durations / total_activities) * 100
            
            # Partial credit for being close
            for day in itinerary.days:
                for activity in day.activities:
                    duration = activity.duration_minutes
                    min_dur, max_dur = self._get_recommended_duration(activity)
                    
                    if duration < min_dur:
                        # Partial credit if within 20% of minimum
                        if duration >= min_dur * 0.8:
                            score += 5
                    elif duration > max_dur:
                        # Partial credit if within 20% of maximum
                        if duration <= max_dur * 1.2:
                            score += 5
        
        return self._create_result(
            score=min(100, score),
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _check_duration(self, activity: "Activity", day_number: int) -> dict:
        """Check if an activity's duration is appropriate."""
        duration = activity.duration_minutes
        min_duration, max_duration = self._get_recommended_duration(activity)
        
        # Check for unrealistic durations first
        if duration > 480:  # More than 8 hours
            return {
                "status": "too_long",
                "issue": f"Day {day_number}: '{activity.place.name}' has unrealistic {duration}min duration",
                "suggestion": f"Day {day_number}: Limit '{activity.place.name}' to reasonable duration",
            }
        
        if duration < 15:  # Less than 15 minutes
            return {
                "status": "too_short",
                "issue": f"Day {day_number}: '{activity.place.name}' has only {duration}min (too short)",
                "suggestion": f"Day {day_number}: Allow at least {min_duration}min for '{activity.place.name}'",
            }
        
        # Check against recommended range
        if duration < min_duration:
            return {
                "status": "too_short",
                "issue": f"Day {day_number}: '{activity.place.name}' has {duration}min (recommended: {min_duration}-{max_duration}min)",
                "suggestion": f"Day {day_number}: Increase time at '{activity.place.name}' to at least {min_duration}min",
            }
        
        if duration > max_duration * 1.5:  # Allow some flexibility
            return {
                "status": "too_long",
                "issue": f"Day {day_number}: '{activity.place.name}' has {duration}min (recommended: {min_duration}-{max_duration}min)",
                "suggestion": f"Day {day_number}: Consider reducing time at '{activity.place.name}'",
            }
        
        return {"status": "appropriate"}
    
    def _get_recommended_duration(self, activity: "Activity") -> tuple[int, int]:
        """Get recommended min/max duration for an activity."""
        name_lower = activity.place.name.lower()
        category = activity.place.category.lower() if activity.place.category else ""
        
        # Check famous places first
        for place_name, duration in FAMOUS_PLACES_DURATIONS.items():
            if place_name in name_lower:
                return duration
        
        # Check category
        if category in RECOMMENDED_DURATIONS:
            return RECOMMENDED_DURATIONS[category]
        
        # Check if name contains category hints
        for cat, duration in RECOMMENDED_DURATIONS.items():
            if cat in name_lower:
                return duration
        
        return RECOMMENDED_DURATIONS["default"]
