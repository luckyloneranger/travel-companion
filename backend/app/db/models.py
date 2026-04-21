"""SQLAlchemy ORM models for the content library schema."""

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("name", "country_code", name="uq_cities_name_country"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(255))
    country_code: Mapped[str] = mapped_column(String(3))
    location: Mapped[dict] = mapped_column(JSONB)
    timezone: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(10))
    population_tier: Mapped[str] = mapped_column(String(20))
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    places: Mapped[list["Place"]] = relationship(back_populates="city", cascade="all, delete-orphan")
    variants: Mapped[list["PlanVariant"]] = relationship(back_populates="city", cascade="all, delete-orphan")


class Place(Base):
    __tablename__ = "places"
    __table_args__ = (
        Index("idx_places_city", "city_id"),
        Index("idx_places_lodging", "city_id", "is_lodging", postgresql_where="is_lodging = true"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    city_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE")
    )
    google_place_id: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    location: Mapped[dict] = mapped_column(JSONB)
    types: Mapped[list[str]] = mapped_column(ARRAY(String))
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    opening_hours: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    photo_references: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    editorial_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_lodging: Mapped[bool] = mapped_column(Boolean, server_default="false")
    business_status: Mapped[str] = mapped_column(String(50), server_default="'OPERATIONAL'")
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    city: Mapped["City"] = relationship(back_populates="places")


class PlanVariant(Base):
    __tablename__ = "plan_variants"
    __table_args__ = (
        Index("idx_variants_lookup", "city_id", "pace", "budget", "day_count", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    city_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE")
    )
    pace: Mapped[str] = mapped_column(String(20))
    budget: Mapped[str] = mapped_column(String(20))
    day_count: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20), server_default="'generating'")
    quality_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    accommodation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id"), nullable=True
    )
    accommodation_alternatives: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    booking_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    city: Mapped["City"] = relationship(back_populates="variants")
    accommodation: Mapped["Place | None"] = relationship(foreign_keys=[accommodation_id])
    day_plans: Mapped[list["DayPlan"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan",
        order_by="DayPlan.day_number",
    )


class DayPlan(Base):
    __tablename__ = "day_plans"
    __table_args__ = (
        UniqueConstraint("variant_id", "day_number", name="uq_day_plans_variant_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan_variants.id", ondelete="CASCADE")
    )
    day_number: Mapped[int] = mapped_column(SmallInteger)
    theme: Mapped[str] = mapped_column(String(255))
    theme_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    variant: Mapped["PlanVariant"] = relationship(back_populates="day_plans")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="day_plan", cascade="all, delete-orphan",
        order_by="Activity.sequence",
    )
    routes: Mapped[list["Route"]] = relationship(
        back_populates="day_plan", cascade="all, delete-orphan",
    )


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("day_plan_id", "sequence", name="uq_activities_day_seq"),
        Index("idx_activities_day", "day_plan_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    day_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("day_plans.id", ondelete="CASCADE")
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id")
    )
    sequence: Mapped[int] = mapped_column(SmallInteger)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_meal: Mapped[bool] = mapped_column(Boolean, server_default="false")
    meal_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    day_plan: Mapped["DayPlan"] = relationship(back_populates="activities")
    place: Mapped["Place"] = relationship()


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        Index("idx_routes_day", "day_plan_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    day_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("day_plans.id", ondelete="CASCADE")
    )
    from_activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id")
    )
    to_activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id")
    )
    travel_mode: Mapped[str] = mapped_column(String(20))
    distance_meters: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    polyline: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    day_plan: Mapped["DayPlan"] = relationship(back_populates="routes")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_users_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    provider: Mapped[str] = mapped_column(String(20))
    provider_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )


class Journey(Base):
    __tablename__ = "journeys"
    __table_args__ = (
        Index("idx_journeys_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    destination: Mapped[str] = mapped_column(String(500))
    origin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    total_days: Mapped[int] = mapped_column(SmallInteger)
    pace: Mapped[str] = mapped_column(String(20))
    budget: Mapped[str] = mapped_column(String(20))
    travelers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    city_sequence: Mapped[dict] = mapped_column(JSONB)
    transport_legs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    weather_forecasts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cost_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default="'complete'")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    user: Mapped["User"] = relationship()


class JourneyShare(Base):
    __tablename__ = "journey_shares"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journeys.id", ondelete="CASCADE")
    )
    token: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    journey: Mapped["Journey"] = relationship()


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index(
            "idx_jobs_queue", "status", "priority", "created_at",
            postgresql_where="status = 'queued'",
        ),
        Index("idx_jobs_city", "city_id", "job_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    job_type: Mapped[str] = mapped_column(String(30))
    city_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cities.id"), nullable=True
    )
    parameters: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), server_default="'queued'")
    priority: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    progress_pct: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
