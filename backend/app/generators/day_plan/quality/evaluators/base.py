"""Base class for quality metric evaluators."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.generators.day_plan.quality.models import MetricResult

if TYPE_CHECKING:
    from app.models import ItineraryResponse


class BaseEvaluator(ABC):
    """Abstract base class for quality metric evaluators."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the metric."""
        pass
    
    @property
    @abstractmethod
    def weight(self) -> float:
        """Weight of this metric in overall score (0-1)."""
        pass
    
    @abstractmethod
    def evaluate(self, itinerary: "ItineraryResponse") -> MetricResult:
        """
        Evaluate the itinerary for this metric.
        
        Args:
            itinerary: The itinerary to evaluate
            
        Returns:
            MetricResult with score, issues, and suggestions
        """
        pass
    
    def _create_result(
        self,
        score: float,
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
        details: dict | None = None,
    ) -> MetricResult:
        """Helper to create a MetricResult with proper defaults."""
        return MetricResult(
            name=self.name,
            score=max(0, min(100, score)),  # Clamp to 0-100
            weight=self.weight,
            issues=issues or [],
            suggestions=suggestions or [],
            details=details,
        )
