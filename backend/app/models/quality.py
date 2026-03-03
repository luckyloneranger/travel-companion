from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    name: str
    score: float = Field(..., ge=0, le=100)
    grade: str = ""
    issues: list[str] = []
    details: str = ""


class QualityReport(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    overall_grade: str = ""
    metrics: list[MetricResult] = []
    critical_issues: list[str] = []
    recommendations: list[str] = []
