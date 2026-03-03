"""Quality-specific internal models, separate from API-facing quality models."""

from dataclasses import dataclass, field


@dataclass
class EvaluatorResult:
    """Result from a single quality evaluator."""

    name: str
    score: float  # 0-100
    grade: str
    issues: list[str]
    details: str = ""
