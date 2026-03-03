import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    destination = Column(String, nullable=False)
    theme = Column(String, default="")
    total_days = Column(Float, default=0)
    cities_count = Column(Float, default=0)
    request_json = Column(Text, nullable=False)  # Serialized TripRequest
    journey_json = Column(Text, nullable=False)  # Serialized JourneyPlan
    day_plans_json = Column(Text, nullable=True)  # Serialized list[DayPlan]
    quality_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
