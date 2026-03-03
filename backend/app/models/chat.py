from pydantic import BaseModel

from .day_plan import DayPlan
from .journey import JourneyPlan


class ChatEditRequest(BaseModel):
    message: str
    context: str = ""


class ChatEditResponse(BaseModel):
    reply: str
    updated_journey: JourneyPlan | None = None
    updated_day_plans: list[DayPlan] | None = None
    changes_made: list[str] = []
