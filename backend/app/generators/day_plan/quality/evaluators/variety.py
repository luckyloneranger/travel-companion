"""Variety quality evaluator."""

from collections import Counter
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan


# Category groups for variety assessment
CATEGORY_GROUPS = {
    "cultural": {"museum", "culture", "art_gallery", "heritage", "historical_landmark"},
    "religious": {"temple", "church", "mosque", "place_of_worship", "shrine"},
    "nature": {"park", "garden", "nature", "lake", "beach", "viewpoint"},
    "entertainment": {"entertainment", "amusement_park", "zoo", "aquarium", "theme_park"},
    "shopping": {"shopping", "market", "mall", "bazaar"},
    "dining": {"dining", "restaurant", "cafe", "food", "bar"},
    "landmark": {"tourist_attraction", "attraction", "landmark", "monument", "fort", "palace"},
}


class VarietyEvaluator(BaseEvaluator):
    """
    Evaluates activity variety and diversity.
    
    Checks:
    - Mix of activity types across the trip
    - No excessive repetition of same category
    - Each day has some variety
    """
    
    @property
    def name(self) -> str:
        return "Variety & Diversity"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["variety"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(score=100, issues=[], suggestions=[])
        
        # Collect all categories
        all_categories: list[str] = []
        category_groups_found: set[str] = set()
        
        day_scores: list[float] = []
        
        for day in itinerary.days:
            day_result = self._evaluate_day(day)
            day_scores.append(day_result["score"])
            all_categories.extend(day_result["categories"])
            category_groups_found.update(day_result["groups_found"])
            
            issues.extend(day_result["issues"])
            suggestions.extend(day_result["suggestions"])
        
        # Overall trip variety analysis
        category_counts = Counter(all_categories)
        total_activities = len(all_categories)
        
        details = {
            "total_activities": total_activities,
            "unique_categories": len(category_counts),
            "category_distribution": dict(category_counts.most_common()),
            "category_groups_covered": list(category_groups_found),
            "groups_count": len(category_groups_found),
        }
        
        # Check for over-concentration
        if total_activities > 0:
            for category, count in category_counts.items():
                percentage = (count / total_activities) * 100
                if percentage > 40 and count > 3:
                    issues.append(
                        f"Over-concentration: {category} makes up {percentage:.0f}% of activities"
                    )
                    suggestions.append(
                        f"Consider adding more variety beyond {category}"
                    )
        
        # Check for missing essential categories
        essential_groups = {"dining", "landmark"}
        missing_essentials = essential_groups - category_groups_found
        for missing in missing_essentials:
            issues.append(f"Missing essential category group: {missing}")
            suggestions.append(f"Add some {missing} activities to the itinerary")
        
        # Calculate overall score
        # Base: average of day scores
        # Bonus/penalty for trip-level variety
        base_score = sum(day_scores) / len(day_scores) if day_scores else 100
        
        # Bonus for covering many category groups (max 10 points)
        variety_bonus = min(10, len(category_groups_found) * 2)
        
        # Penalty for missing essentials (10 points each)
        essential_penalty = len(missing_essentials) * 10
        
        score = base_score + variety_bonus - essential_penalty
        
        return self._create_result(
            score=max(0, min(100, score)),
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _evaluate_day(self, day: "DayPlan") -> dict:
        """Evaluate variety for a single day."""
        result = {
            "score": 100.0,
            "categories": [],
            "groups_found": set(),
            "issues": [],
            "suggestions": [],
        }
        
        if not day.activities:
            return result
        
        categories = []
        groups_found = set()
        
        for activity in day.activities:
            category = activity.place.category.lower() if activity.place.category else "other"
            categories.append(category)
            
            # Map to group
            for group, group_categories in CATEGORY_GROUPS.items():
                if category in group_categories:
                    groups_found.add(group)
                    break
        
        result["categories"] = categories
        result["groups_found"] = groups_found
        
        # Check for day-level variety issues
        category_counts = Counter(categories)
        non_dining = [c for c in categories if c not in CATEGORY_GROUPS["dining"]]
        
        if len(non_dining) >= 3:
            # Check for same-category repetition
            for category, count in category_counts.items():
                if count >= 3 and category not in CATEGORY_GROUPS["dining"]:
                    result["score"] -= 15
                    result["issues"].append(
                        f"Day {day.day_number}: {count} activities of type '{category}' (repetitive)"
                    )
                    result["suggestions"].append(
                        f"Day {day.day_number}: Mix in different activity types"
                    )
        
        # Bonus for having multiple groups in a day
        if len(groups_found) >= 3:
            result["score"] = min(100, result["score"] + 5)
        elif len(groups_found) == 1 and len(day.activities) > 2:
            result["score"] -= 10
            result["issues"].append(
                f"Day {day.day_number}: All activities are in one category group"
            )
        
        return result
    
    def _get_category_group(self, category: str) -> str | None:
        """Get the group a category belongs to."""
        category_lower = category.lower()
        for group, categories in CATEGORY_GROUPS.items():
            if category_lower in categories:
                return group
        return None
