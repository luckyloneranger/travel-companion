"""
Quality evaluation module for itinerary scoring.

This module provides rigorous quality assessment for any generated itinerary,
regardless of the generation method (fast or pristine).

Usage:
    from app.quality import ItineraryScorer, QualityReport
    
    scorer = ItineraryScorer()
    report = await scorer.evaluate(itinerary_response)
    print(f"Overall: {report.overall_score}")
"""

from app.generators.day_plan.quality.models import (
    QualityScore,
    QualityReport,
    MetricResult,
    QualityGrade,
)
from app.generators.day_plan.quality.scorer import ItineraryScorer

__all__ = [
    "QualityScore",
    "QualityReport",
    "MetricResult",
    "QualityGrade",
    "ItineraryScorer",
]
