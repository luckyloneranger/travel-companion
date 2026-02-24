"""Unified itinerary quality scorer."""

import logging
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.models import (
    QualityScore,
    QualityReport,
    MetricResult,
    QualityGrade,
    METRIC_WEIGHTS,
)
from app.generators.day_plan.quality.evaluators import (
    MealTimingEvaluator,
    GeographicClusteringEvaluator,
    TravelEfficiencyEvaluator,
    VarietyEvaluator,
    OpeningHoursEvaluator,
    ThemeAlignmentEvaluator,
    DurationEvaluator,
)

if TYPE_CHECKING:
    from app.models import ItineraryResponse

logger = logging.getLogger(__name__)


class ItineraryScorer:
    """
    Unified quality scorer for any itinerary.
    
    Evaluates itineraries using multiple metrics and produces
    a comprehensive quality report with actionable feedback.
    
    Usage:
        scorer = ItineraryScorer()
        report = scorer.evaluate(itinerary)
        print(f"Grade: {report.overall_grade}")
    """
    
    def __init__(self):
        """Initialize the scorer with all evaluators."""
        self.evaluators = [
            MealTimingEvaluator(),
            GeographicClusteringEvaluator(),
            TravelEfficiencyEvaluator(),
            VarietyEvaluator(),
            OpeningHoursEvaluator(),
            ThemeAlignmentEvaluator(),
            DurationEvaluator(),
        ]
    
    def evaluate(self, itinerary: "ItineraryResponse") -> QualityReport:
        """
        Evaluate an itinerary and produce a comprehensive quality report.
        
        Args:
            itinerary: The itinerary response to evaluate
            
        Returns:
            QualityReport with scores, issues, and recommendations
        """
        logger.info(f"[QualityScorer] Evaluating itinerary for {itinerary.destination.name}")
        
        # Run all evaluators
        metric_results: list[MetricResult] = []
        
        for evaluator in self.evaluators:
            try:
                result = evaluator.evaluate(itinerary)
                metric_results.append(result)
                logger.debug(f"[QualityScorer] {evaluator.name}: {result.score:.1f}")
            except Exception as e:
                logger.error(f"[QualityScorer] Error in {evaluator.name}: {e}")
                # Create a default result on error
                metric_results.append(MetricResult(
                    name=evaluator.name,
                    score=50.0,  # Neutral score on error
                    weight=evaluator.weight,
                    issues=[f"Evaluation error: {str(e)}"],
                ))
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metric_results)
        
        # Build quality score object
        scores = self._build_quality_score(metric_results, overall_score)
        
        # Collect all issues and determine critical ones
        all_issues = []
        critical_issues = []
        all_suggestions = []
        
        for result in metric_results:
            all_issues.extend(result.issues)
            all_suggestions.extend(result.suggestions)
            
            # Issues from low-scoring metrics are critical
            if result.score < 50:
                critical_issues.extend(result.issues[:2])  # Top 2 issues per critical metric
        
        # Deduplicate and prioritize recommendations
        recommendations = self._prioritize_recommendations(all_suggestions, metric_results)
        
        # Extract metadata
        total_activities = sum(len(d.activities) for d in itinerary.days)
        
        report = QualityReport(
            overall_score=overall_score,
            overall_grade=QualityGrade.from_score(overall_score),
            scores=scores,
            metrics=metric_results,
            total_issues=len(all_issues),
            critical_issues=critical_issues[:5],  # Top 5
            recommendations=recommendations[:5],  # Top 5
            generation_mode=itinerary.generation_mode.value if itinerary.generation_mode else "unknown",
            destination=itinerary.destination.name,
            num_days=len(itinerary.days),
            total_activities=total_activities,
        )
        
        logger.info(
            f"[QualityScorer] Result: {report.overall_grade.value} ({overall_score:.1f}/100), "
            f"{len(all_issues)} issues"
        )
        
        return report
    
    def _calculate_overall_score(self, results: list[MetricResult]) -> float:
        """Calculate weighted overall score from metric results."""
        if not results:
            return 0.0
        
        total_weight = sum(r.weight for r in results)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(r.score * r.weight for r in results)
        return weighted_sum / total_weight
    
    def _build_quality_score(
        self, 
        results: list[MetricResult], 
        overall: float
    ) -> QualityScore:
        """Build QualityScore object from metric results."""
        scores = QualityScore(overall=overall)
        
        for result in results:
            # Map metric names to QualityScore fields
            name_map = {
                "Meal Timing": "meal_timing",
                "Geographic Clustering": "geographic_clustering",
                "Travel Efficiency": "travel_efficiency",
                "Variety & Diversity": "variety",
                "Opening Hours": "opening_hours",
                "Theme Alignment": "theme_alignment",
                "Duration Appropriateness": "duration_appropriateness",
            }
            
            field_name = name_map.get(result.name)
            if field_name and hasattr(scores, field_name):
                setattr(scores, field_name, result.score)
        
        return scores
    
    def _prioritize_recommendations(
        self,
        suggestions: list[str],
        results: list[MetricResult]
    ) -> list[str]:
        """
        Prioritize and deduplicate recommendations.
        
        Suggestions from lower-scoring metrics get higher priority.
        """
        # Score each suggestion by metric score
        scored_suggestions: list[tuple[float, str]] = []
        
        for result in sorted(results, key=lambda r: r.score):
            for suggestion in result.suggestions:
                # Lower metric score = higher priority (lower number)
                priority = result.score
                if suggestion not in [s[1] for s in scored_suggestions]:
                    scored_suggestions.append((priority, suggestion))
        
        # Sort by priority (lower score = higher priority)
        scored_suggestions.sort(key=lambda x: x[0])
        
        return [s[1] for s in scored_suggestions]
    
    def get_quick_score(self, itinerary: "ItineraryResponse") -> tuple[float, str]:
        """
        Get a quick overall score and grade without full report.
        
        Useful for fast comparisons.
        
        Returns:
            Tuple of (score, grade_string)
        """
        report = self.evaluate(itinerary)
        return report.overall_score, report.overall_grade.value


# Convenience function for quick evaluation
def evaluate_itinerary(itinerary: "ItineraryResponse") -> QualityReport:
    """
    Convenience function to evaluate an itinerary.
    
    Usage:
        from app.quality import evaluate_itinerary
        report = evaluate_itinerary(itinerary)
    """
    scorer = ItineraryScorer()
    return scorer.evaluate(itinerary)
