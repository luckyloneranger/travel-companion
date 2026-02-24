"""Shared request models for journey planning.

Defines the common request interface used by V6 journey planning.
"""

from datetime import date
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class JourneyRequestProtocol(Protocol):
    """Protocol defining what a journey request must provide."""
    origin: str
    region: Optional[str]
    destinations: list[str]
    start_date: str | date
    total_days: Optional[int]
    interests: list[str]
    pace: str
    return_to_origin: bool
    must_include: list[str]
    avoid: list[str]
    
    def get_total_days(self) -> int:
        """Get total trip days."""
        ...


class JourneyRequest:
    """Simple journey request object that V6 agents can use.
    
    This is a flexible class that accepts keyword arguments,
    allowing the router to easily construct requests.
    """
    
    def __init__(
        self,
        origin: str,
        region: str = "",
        destinations: list[str] | None = None,
        start_date: str | date | None = None,
        total_days: int | None = None,
        interests: list[str] | None = None,
        pace: str = "moderate",
        return_to_origin: bool = False,
        must_include: list[str] | None = None,
        avoid: list[str] | None = None,
        transport_preferences: list[str] | None = None,
        **kwargs,  # Accept extra kwargs for flexibility
    ):
        self.origin = origin
        self.region = region or ""
        self.destinations = destinations or []
        self.start_date = start_date
        self.total_days = total_days
        self.interests = interests or []
        self.pace = pace
        self.return_to_origin = return_to_origin
        self.must_include = must_include or []
        self.avoid = avoid or []
        self.transport_preferences = transport_preferences or []
        
        # Store any extra kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def get_total_days(self) -> int:
        """Get total trip days from total_days attribute."""
        if self.total_days:
            return self.total_days
        raise ValueError("total_days must be provided")
