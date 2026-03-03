from typing import Any

from pydantic import BaseModel


class ProgressEvent(BaseModel):
    phase: str
    message: str
    progress: int = 0
    data: dict[str, Any] | None = None
