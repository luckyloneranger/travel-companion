"""Theme alignment quality evaluator."""

import re
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.evaluators.base import BaseEvaluator
from app.generators.day_plan.quality.models import MetricResult, METRIC_WEIGHTS

if TYPE_CHECKING:
    from app.models import ItineraryResponse, DayPlan


# Theme keywords and their expected activity types
THEME_KEYWORDS = {
    "heritage": {"museum", "palace", "fort", "historical", "heritage", "monument", "landmark", "attraction"},
    "old city": {"heritage", "bazaar", "market", "historical", "landmark", "gate", "mosque", "temple", "attraction"},
    "riverfront": {"river", "lake", "park", "garden", "waterfront", "bridge", "nature"},
    "ashram": {"ashram", "memorial", "museum", "culture"},
    "science": {"museum", "science", "planetarium", "exhibition", "culture"},
    "temple": {"temple", "mandir", "religious", "shrine", "worship", "attraction"},
    "spiritual": {"temple", "mosque", "church", "religious", "spiritual", "shrine"},
    "museum": {"museum", "gallery", "exhibition", "culture"},
    "nature": {"park", "garden", "lake", "nature", "zoo", "forest"},
    "food": {"restaurant", "dining", "cafe", "food", "market"},
    "culture": {"museum", "culture", "heritage", "art", "gallery", "theater"},
    "architecture": {"palace", "fort", "monument", "museum", "landmark", "historical", "attraction"},
    "park": {"park", "garden", "nature", "zoo"},
    "family": {"park", "zoo", "amusement", "museum", "entertainment"},
    "market": {"market", "bazaar", "shopping"},
    "fort": {"fort", "palace", "historical", "attraction", "landmark"},
    "gate": {"gate", "historical", "landmark", "attraction"},
}


class ThemeAlignmentEvaluator(BaseEvaluator):
    """
    Evaluates how well activities match their day's theme.
    
    Checks:
    - Activities align with the stated theme
    - Theme is specific and meaningful (not generic)
    """
    
    @property
    def name(self) -> str:
        return "Theme Alignment"
    
    @property
    def weight(self) -> float:
        return METRIC_WEIGHTS["theme_alignment"]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        issues: list[str] = []
        suggestions: list[str] = []
        
        if not itinerary.days:
            return self._create_result(score=100, issues=[], suggestions=[])
        
        day_scores: list[float] = []
        details = {
            "days_analyzed": len(itinerary.days),
            "themes": [],
            "alignment_scores": [],
        }
        
        for day in itinerary.days:
            day_result = self._evaluate_day(day)
            day_scores.append(day_result["score"])
            details["themes"].append(day.theme)
            details["alignment_scores"].append(round(day_result["score"], 1))
            
            issues.extend(day_result["issues"])
            suggestions.extend(day_result["suggestions"])
        
        score = sum(day_scores) / len(day_scores) if day_scores else 100
        
        return self._create_result(
            score=score,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )
    
    def _evaluate_day(self, day: "DayPlan") -> dict:
        """Evaluate theme alignment for a single day."""
        result = {
            "score": 100.0,
            "issues": [],
            "suggestions": [],
        }
        
        if not day.theme or not day.activities:
            return result
        
        theme_lower = day.theme.lower()
        
        # Extract theme keywords from the theme string
        expected_categories = self._extract_expected_categories(theme_lower)
        
        if not expected_categories:
            # Generic theme without specific keywords
            result["score"] = 70  # Partial credit
            result["issues"].append(
                f"Day {day.day_number}: Theme '{day.theme}' is too generic"
            )
            result["suggestions"].append(
                f"Day {day.day_number}: Use more specific themes like 'Heritage Walk' or 'Temple Trail'"
            )
            return result
        
        # Count how many non-dining activities match expected categories
        non_dining_activities = [
            a for a in day.activities 
            if a.place.category.lower() not in {"dining", "restaurant", "cafe", "food"}
        ]
        
        if not non_dining_activities:
            return result  # Only dining, can't evaluate theme match
        
        matching = 0
        for activity in non_dining_activities:
            category = activity.place.category.lower() if activity.place.category else ""
            name_lower = activity.place.name.lower()
            
            # Check if activity matches expected categories
            is_match = False
            
            # Check category
            if category in expected_categories:
                is_match = True
            
            # Check name keywords
            for keyword in expected_categories:
                if keyword in name_lower:
                    is_match = True
                    break
            
            if is_match:
                matching += 1
        
        # Calculate alignment percentage
        alignment = (matching / len(non_dining_activities)) * 100 if non_dining_activities else 100
        
        if alignment < 50:
            result["issues"].append(
                f"Day {day.day_number}: Only {matching}/{len(non_dining_activities)} activities match theme '{day.theme}'"
            )
            result["suggestions"].append(
                f"Day {day.day_number}: Add more activities related to the theme or adjust the theme"
            )
        
        result["score"] = alignment
        
        return result
    
    def _extract_expected_categories(self, theme: str) -> set[str]:
        """Extract expected activity categories from theme keywords."""
        expected = set()
        
        for keyword, categories in THEME_KEYWORDS.items():
            if keyword in theme:
                expected.update(categories)
        
        # Also check for common words in theme
        theme_words = re.findall(r'\b\w+\b', theme)
        for word in theme_words:
            if word in THEME_KEYWORDS:
                expected.update(THEME_KEYWORDS[word])
        
        return expected
