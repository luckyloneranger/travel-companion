"""Unified itinerary quality scorer.

Runs all 7 evaluators, computes a weighted overall score, and returns
a :class:`QualityReport` (from ``app.models.quality``).

Ported from the battle-tested ItineraryScorer in the original codebase.
"""

import logging
from typing import Any

from app.algorithms.quality.evaluators import (
    DurationAppropriatenessEvaluator,
    GeographicClusteringEvaluator,
    MealTimingEvaluator,
    OpeningHoursEvaluator,
    ThemeAlignmentEvaluator,
    TravelEfficiencyEvaluator,
    VarietyEvaluator,
)
from app.algorithms.quality.models import EvaluatorResult
from app.models.day_plan import DayPlan
from app.models.quality import MetricResult, QualityReport

logger = logging.getLogger(__name__)

# Grade scale: A (90+), A- (85+), B+ (80+), B (75+), B- (70+),
#              C+ (65+), C (60+), D (below 60)

_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (90, "A"),
    (85, "A-"),
    (80, "B+"),
    (75, "B"),
    (70, "B-"),
    (65, "C+"),
    (60, "C"),
]


def _grade_from_score(score: float) -> str:
    """Map a 0-100 score to a letter grade."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "D"


class ItineraryScorer:
    """
    Unified quality scorer for any itinerary.

    Evaluates itineraries using 7 weighted metrics and produces a
    comprehensive :class:`QualityReport`.

    Usage::

        scorer = ItineraryScorer()
        report = scorer.evaluate(day_plans, context={
            "destination": "Paris",
            "num_days": 3,
        })
        print(f"Grade: {report.overall_grade}")
    """

    def __init__(self) -> None:
        """Initialise the scorer with all evaluators."""
        self.evaluators = [
            MealTimingEvaluator(),
            GeographicClusteringEvaluator(),
            TravelEfficiencyEvaluator(),
            VarietyEvaluator(),
            OpeningHoursEvaluator(),
            ThemeAlignmentEvaluator(),
            DurationAppropriatenessEvaluator(),
        ]

    def evaluate(
        self,
        day_plans: list[DayPlan],
        context: dict[str, Any] | None = None,
    ) -> QualityReport:
        """
        Evaluate an itinerary and produce a comprehensive quality report.

        Args:
            day_plans: List of DayPlan objects to evaluate.
            context: Optional dict with keys like ``destination``,
                ``theme``, ``num_days``.

        Returns:
            QualityReport with overall score, per-metric results, and
            actionable recommendations.
        """
        context = context or {}
        logger.info(
            "[QualityScorer] Evaluating itinerary (%d days)",
            len(day_plans),
        )

        evaluator_results: list[EvaluatorResult] = []

        for evaluator in self.evaluators:
            try:
                result = evaluator.evaluate(day_plans, context)
                evaluator_results.append(result)
                logger.debug(
                    "[QualityScorer] %s: %.1f", evaluator.name, result.score
                )
            except Exception as e:
                logger.error("[QualityScorer] Error in %s: %s", evaluator.name, e)
                evaluator_results.append(
                    EvaluatorResult(
                        name=evaluator.name,
                        score=50.0,
                        grade="D",
                        issues=[f"Evaluation error: {e}"],
                    )
                )

        # Compute weighted overall score
        overall_score = self._calculate_overall_score(evaluator_results)
        overall_grade = _grade_from_score(overall_score)

        # Collect issues and recommendations
        all_issues: list[str] = []
        critical_issues: list[str] = []
        recommendations: list[str] = []

        for r in evaluator_results:
            all_issues.extend(r.issues)
            if r.score < 50:
                critical_issues.extend(r.issues[:2])

        # Build per-metric model results
        metric_results: list[MetricResult] = []
        for r in evaluator_results:
            metric_results.append(
                MetricResult(
                    name=r.name,
                    score=round(r.score, 1),
                    grade=r.grade,
                    issues=r.issues,
                    details=r.details,
                )
            )

        # Prioritise recommendations from lowest-scoring metrics
        for r in sorted(evaluator_results, key=lambda x: x.score):
            for issue in r.issues:
                if issue not in recommendations:
                    recommendations.append(issue)

        report = QualityReport(
            overall_score=round(overall_score, 1),
            overall_grade=overall_grade,
            metrics=metric_results,
            critical_issues=critical_issues[:5],
            recommendations=recommendations[:5],
        )

        logger.info(
            "[QualityScorer] Result: %s (%.1f/100), %d issues",
            overall_grade,
            overall_score,
            len(all_issues),
        )

        return report

    def _calculate_overall_score(
        self, results: list[EvaluatorResult]
    ) -> float:
        """Calculate weighted overall score from evaluator results."""
        if not results:
            return 0.0

        # Use the weight from each evaluator instance
        total_weight = 0.0
        weighted_sum = 0.0

        for r in results:
            # Look up the evaluator's weight by name
            w = self._weight_for(r.name)
            weighted_sum += r.score * w
            total_weight += w

        return weighted_sum / total_weight if total_weight else 0.0

    def _weight_for(self, name: str) -> float:
        """Get the weight for an evaluator by its name."""
        for ev in self.evaluators:
            if ev.name == name:
                return ev.weight
        return 0.1  # fallback

    def get_quick_score(
        self,
        day_plans: list[DayPlan],
        context: dict[str, Any] | None = None,
    ) -> tuple[float, str]:
        """
        Get a quick overall score and grade without a full report.

        Returns:
            Tuple of (score, grade_string).
        """
        report = self.evaluate(day_plans, context)
        return report.overall_score, report.overall_grade
