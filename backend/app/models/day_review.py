from pydantic import BaseModel, Field


class DayReviewIssue(BaseModel):
    """A specific issue found during day plan quality review."""
    severity: str
    day_number: int
    category: str
    description: str
    suggestion: str


class DayReviewResult(BaseModel):
    """Result of reviewing a batch of day plans."""
    score: int = Field(..., ge=0, le=100)
    is_acceptable: bool
    issues: list[DayReviewIssue] = []
    summary: str = ""
