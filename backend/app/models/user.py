from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    provider: str
