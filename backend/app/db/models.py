import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    destination = Column(String, nullable=False)
    theme = Column(String, default="")
    total_days = Column(Float, default=0)
    cities_count = Column(Float, default=0)
    request_json = Column(Text, nullable=False)  # Serialized TripRequest
    journey_json = Column(Text, nullable=False)  # Serialized JourneyPlan
    day_plans_json = Column(Text, nullable=True)  # Serialized list[DayPlan]
    quality_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    provider = Column(String, nullable=False)  # "google" or "github"
    created_at = Column(DateTime(timezone=True), default=func.now())


class TripShare(Base):
    __tablename__ = "trip_shares"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    share_token = Column(String, unique=True, nullable=False)
    access_level = Column(String, default="view")  # "view" or "edit"
    created_at = Column(DateTime(timezone=True), default=func.now())
