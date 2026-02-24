"""Quality evaluation data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class QualityGrade(str, Enum):
    """Letter grade for quality assessment."""
    A_PLUS = "A+"   # 95-100
    A = "A"         # 90-94
    A_MINUS = "A-"  # 85-89
    B_PLUS = "B+"   # 80-84
    B = "B"         # 75-79
    B_MINUS = "B-"  # 70-74
    C_PLUS = "C+"   # 65-69
    C = "C"         # 60-64
    C_MINUS = "C-"  # 55-59
    D = "D"         # 50-54
    F = "F"         # 0-49

    @classmethod
    def from_score(cls, score: float) -> "QualityGrade":
        """Convert numeric score to letter grade."""
        if score >= 95:
            return cls.A_PLUS
        elif score >= 90:
            return cls.A
        elif score >= 85:
            return cls.A_MINUS
        elif score >= 80:
            return cls.B_PLUS
        elif score >= 75:
            return cls.B
        elif score >= 70:
            return cls.B_MINUS
        elif score >= 65:
            return cls.C_PLUS
        elif score >= 60:
            return cls.C
        elif score >= 55:
            return cls.C_MINUS
        elif score >= 50:
            return cls.D
        else:
            return cls.F


@dataclass
class MetricResult:
    """Result from a single quality metric evaluation."""
    
    name: str
    score: float  # 0-100
    weight: float  # Weight in overall calculation
    grade: QualityGrade = field(init=False)
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    details: Optional[dict] = None  # Metric-specific details
    
    def __post_init__(self):
        self.grade = QualityGrade.from_score(self.score)
    
    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "score": round(self.score, 1),
            "weight": self.weight,
            "grade": self.grade.value,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class QualityScore:
    """Individual metric scores."""
    
    meal_timing: float = 0.0
    geographic_clustering: float = 0.0
    travel_efficiency: float = 0.0
    variety: float = 0.0
    opening_hours: float = 0.0
    theme_alignment: float = 0.0
    duration_appropriateness: float = 0.0
    overall: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "meal_timing": round(self.meal_timing, 1),
            "geographic_clustering": round(self.geographic_clustering, 1),
            "travel_efficiency": round(self.travel_efficiency, 1),
            "variety": round(self.variety, 1),
            "opening_hours": round(self.opening_hours, 1),
            "theme_alignment": round(self.theme_alignment, 1),
            "duration_appropriateness": round(self.duration_appropriateness, 1),
            "overall": round(self.overall, 1),
        }


@dataclass  
class QualityReport:
    """Complete quality evaluation report for an itinerary."""
    
    overall_score: float
    overall_grade: QualityGrade
    scores: QualityScore
    metrics: list[MetricResult]
    total_issues: int
    critical_issues: list[str]  # Issues that significantly impact experience
    recommendations: list[str]  # Top suggestions for improvement
    
    # Metadata
    generation_mode: str
    destination: str
    num_days: int
    total_activities: int
    
    def __post_init__(self):
        if not isinstance(self.overall_grade, QualityGrade):
            self.overall_grade = QualityGrade.from_score(self.overall_score)
    
    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "overall_grade": self.overall_grade.value,
            "scores": self.scores.to_dict(),
            "metrics": [m.to_dict() for m in self.metrics],
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "recommendations": self.recommendations[:5],  # Top 5
            "metadata": {
                "generation_mode": self.generation_mode,
                "destination": self.destination,
                "num_days": self.num_days,
                "total_activities": self.total_activities,
            }
        }
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        return (
            f"Quality Report: {self.overall_grade.value} ({self.overall_score:.1f}/100)\n"
            f"Destination: {self.destination} ({self.num_days} days, {self.total_activities} activities)\n"
            f"Mode: {self.generation_mode}\n"
            f"Issues Found: {self.total_issues}\n"
            f"Critical: {len(self.critical_issues)}"
        )


# Import metric weights from central config
from app.config.tuning import QUALITY_METRIC_WEIGHTS as METRIC_WEIGHTS

# Thresholds for quality evaluation
QUALITY_THRESHOLDS = {
    "excellent": 90.0,
    "acceptable": 70.0,
    "poor": 50.0,
}
