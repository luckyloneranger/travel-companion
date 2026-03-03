import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.day_plan import DayPlan
from app.models.journey import JourneyPlan
from app.models.trip import TripRequest, TripResponse, TripSummary

from .models import Trip

logger = logging.getLogger(__name__)


class TripRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_trip(
        self,
        request: TripRequest,
        journey: JourneyPlan,
        trip_id: str | None = None,
    ) -> str:
        """Save a new trip. Returns trip ID."""
        tid = trip_id or str(uuid.uuid4())
        trip = Trip(
            id=tid,
            destination=request.destination,
            theme=journey.theme,
            total_days=journey.total_days,
            cities_count=len(journey.cities),
            request_json=request.model_dump_json(),
            journey_json=journey.model_dump_json(),
        )
        self.session.add(trip)
        await self.session.commit()
        logger.info(f"Saved trip {tid}")
        return tid

    async def update_day_plans(
        self,
        trip_id: str,
        day_plans: list[DayPlan],
        quality_score: float | None = None,
    ) -> None:
        """Update trip with day plans."""
        result = await self.session.get(Trip, trip_id)
        if not result:
            raise ValueError(f"Trip {trip_id} not found")
        result.day_plans_json = json.dumps([dp.model_dump() for dp in day_plans])
        if quality_score is not None:
            result.quality_score = quality_score
        result.updated_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def update_journey(self, trip_id: str, journey: JourneyPlan) -> None:
        """Update trip's journey plan (e.g., after chat edit)."""
        result = await self.session.get(Trip, trip_id)
        if not result:
            raise ValueError(f"Trip {trip_id} not found")
        result.journey_json = journey.model_dump_json()
        result.theme = journey.theme
        result.total_days = journey.total_days
        result.cities_count = len(journey.cities)
        result.updated_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def get_trip(self, trip_id: str) -> TripResponse | None:
        """Get a complete trip by ID."""
        trip = await self.session.get(Trip, trip_id)
        if not trip:
            return None
        return self._to_response(trip)

    async def list_trips(self) -> list[TripSummary]:
        """List all trips (summaries only)."""
        result = await self.session.execute(
            select(Trip).order_by(Trip.created_at.desc())
        )
        trips = result.scalars().all()
        return [self._to_summary(t) for t in trips]

    async def delete_trip(self, trip_id: str) -> bool:
        """Delete a trip. Returns True if deleted."""
        result = await self.session.execute(
            delete(Trip).where(Trip.id == trip_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    def _to_response(self, trip: Trip) -> TripResponse:
        """Convert ORM model to API response."""
        day_plans = None
        if trip.day_plans_json:
            raw = json.loads(trip.day_plans_json)
            day_plans = [DayPlan.model_validate(dp) for dp in raw]

        return TripResponse(
            id=trip.id,
            request=TripRequest.model_validate_json(trip.request_json),
            journey=JourneyPlan.model_validate_json(trip.journey_json),
            day_plans=day_plans,
            quality_score=trip.quality_score,
            created_at=trip.created_at,
            updated_at=trip.updated_at,
        )

    def _to_summary(self, trip: Trip) -> TripSummary:
        """Convert ORM model to summary."""
        return TripSummary(
            id=trip.id,
            theme=trip.theme or "",
            destination=trip.destination,
            total_days=int(trip.total_days or 0),
            cities_count=int(trip.cities_count or 0),
            created_at=trip.created_at,
            has_day_plans=trip.day_plans_json is not None,
        )
