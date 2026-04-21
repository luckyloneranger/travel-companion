from pydantic import BaseModel
from uuid import UUID


class JobStatus(BaseModel):
    id: UUID
    status: str
    progress_pct: int = 0
    estimated_seconds_remaining: int | None = None
    result: dict | None = None
    error: str | None = None


class JobCreate(BaseModel):
    job_type: str
    city_id: UUID | None = None
    parameters: dict
    priority: int = 0
