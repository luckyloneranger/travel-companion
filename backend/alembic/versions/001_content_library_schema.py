"""content library schema

Revision ID: 001
Revises:
Create Date: 2026-04-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- cities ---
    op.create_table(
        "cities",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(3), nullable=False),
        sa.Column("location", JSONB, nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("population_tier", sa.String(20), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("data_hash", sa.String(64), nullable=True),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", "country_code", name="uq_cities_name_country"),
    )

    # --- places ---
    op.create_table(
        "places",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("city_id", UUID(as_uuid=True), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("google_place_id", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("address", sa.String(1000), nullable=True),
        sa.Column("location", JSONB, nullable=False),
        sa.Column("types", ARRAY(sa.String), nullable=False),
        sa.Column("rating", sa.Float, nullable=True),
        sa.Column("user_rating_count", sa.Integer, nullable=True),
        sa.Column("price_level", sa.SmallInteger, nullable=True),
        sa.Column("opening_hours", JSONB, nullable=True),
        sa.Column("photo_references", ARRAY(sa.String), nullable=True),
        sa.Column("editorial_summary", sa.Text, nullable=True),
        sa.Column("website_url", sa.String(1000), nullable=True),
        sa.Column("is_lodging", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("business_status", sa.String(50), server_default=sa.text("'OPERATIONAL'"), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_places_city", "places", ["city_id"])
    op.create_index(
        "idx_places_lodging", "places", ["city_id", "is_lodging"],
        postgresql_where=sa.text("is_lodging = true"),
    )

    # --- plan_variants ---
    op.create_table(
        "plan_variants",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("city_id", UUID(as_uuid=True), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pace", sa.String(20), nullable=False),
        sa.Column("budget", sa.String(20), nullable=False),
        sa.Column("day_count", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'generating'"), nullable=False),
        sa.Column("quality_score", sa.SmallInteger, nullable=True),
        sa.Column("accommodation_id", UUID(as_uuid=True), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("accommodation_alternatives", JSONB, nullable=True),
        sa.Column("booking_hint", sa.Text, nullable=True),
        sa.Column("cost_breakdown", JSONB, nullable=True),
        sa.Column("generation_metadata", JSONB, nullable=True),
        sa.Column("data_hash", sa.String(64), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "idx_variants_lookup", "plan_variants",
        ["city_id", "pace", "budget", "day_count", "status"],
    )

    # --- day_plans ---
    op.create_table(
        "day_plans",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("plan_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_number", sa.SmallInteger, nullable=False),
        sa.Column("theme", sa.String(255), nullable=False),
        sa.Column("theme_description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("variant_id", "day_number", name="uq_day_plans_variant_day"),
    )

    # --- activities ---
    op.create_table(
        "activities",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("day_plan_id", UUID(as_uuid=True), sa.ForeignKey("day_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("place_id", UUID(as_uuid=True), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("sequence", sa.SmallInteger, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_meal", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("day_plan_id", "sequence", name="uq_activities_day_seq"),
    )
    op.create_index("idx_activities_day", "activities", ["day_plan_id"])

    # --- routes ---
    op.create_table(
        "routes",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("day_plan_id", UUID(as_uuid=True), sa.ForeignKey("day_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_activity_id", UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("to_activity_id", UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("travel_mode", sa.String(20), nullable=False),
        sa.Column("distance_meters", sa.Integer, nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column("polyline", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_routes_day", "routes", ["day_plan_id"])

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider", "provider_id", name="uq_users_provider"),
    )

    # --- journeys ---
    op.create_table(
        "journeys",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.String(500), nullable=False),
        sa.Column("origin", sa.String(500), nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("total_days", sa.SmallInteger, nullable=False),
        sa.Column("pace", sa.String(20), nullable=False),
        sa.Column("budget", sa.String(20), nullable=False),
        sa.Column("travelers", JSONB, nullable=True),
        sa.Column("city_sequence", JSONB, nullable=False),
        sa.Column("transport_legs", JSONB, nullable=True),
        sa.Column("weather_forecasts", JSONB, nullable=True),
        sa.Column("cost_breakdown", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'complete'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_journeys_user", "journeys", ["user_id"])

    # --- journey_shares ---
    op.create_table(
        "journey_shares",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("journey_id", UUID(as_uuid=True), sa.ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- generation_jobs ---
    op.create_table(
        "generation_jobs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("city_id", UUID(as_uuid=True), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("priority", sa.SmallInteger, server_default=sa.text("0"), nullable=False),
        sa.Column("progress_pct", sa.SmallInteger, server_default=sa.text("0"), nullable=False),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("locked_by", sa.String(100), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "idx_jobs_queue", "generation_jobs",
        ["status", sa.text("priority DESC"), "created_at"],
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index("idx_jobs_city", "generation_jobs", ["city_id", "job_type"])


def downgrade() -> None:
    op.drop_table("generation_jobs")
    op.drop_table("journey_shares")
    op.drop_table("journeys")
    op.drop_table("users")
    op.drop_table("routes")
    op.drop_table("activities")
    op.drop_table("day_plans")
    op.drop_table("plan_variants")
    op.drop_table("places")
    op.drop_table("cities")
