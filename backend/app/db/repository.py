import json
import logging
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.day_plan import DayPlan
from app.models.journey import JourneyPlan
from app.models.trip import TripRequest, TripResponse, TripSummary

from .models import Trip, TripShare, User

logger = logging.getLogger(__name__)


class TripRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_trip(
        self,
        request: TripRequest,
        journey: JourneyPlan,
        trip_id: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Save a new trip. Returns trip ID."""
        # Ensure user exists before saving (defensive against FK constraint)
        if user_id:
            existing = await self.session.get(User, user_id)
            if not existing:
                logger.warning(f"User {user_id} not in DB, creating stub")
                self.session.add(User(
                    id=user_id, email=f"{user_id}@unknown", name="Unknown", provider="unknown"
                ))
                await self.session.flush()

        tid = trip_id or str(uuid.uuid4())
        trip = Trip(
            id=tid,
            user_id=user_id,
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

    async def list_trips(self, user_id: str | None = None, limit: int = 50, offset: int = 0) -> list[TripSummary]:
        """List trips (summaries only). When user_id is provided, filter by owner."""
        query = select(Trip).order_by(Trip.created_at.desc())
        if user_id is not None:
            query = query.where(Trip.user_id == user_id)
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        trips = result.scalars().all()
        return [self._to_summary(t) for t in trips]

    async def delete_trip(self, trip_id: str) -> bool:
        """Delete a trip. Returns True if deleted."""
        result = await self.session.execute(
            delete(Trip).where(Trip.id == trip_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def create_share(self, trip_id: str) -> str:
        """Create a share token for a trip. Returns the token."""
        share_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(9)  # ~12 chars
        share = TripShare(
            id=share_id,
            trip_id=trip_id,
            share_token=token,
        )
        self.session.add(share)
        await self.session.commit()
        return token

    async def get_trip_by_share_token(self, token: str) -> TripResponse | None:
        """Get a trip by its share token. Returns TripResponse or None."""
        result = await self.session.execute(
            select(TripShare).where(TripShare.share_token == token)
        )
        share = result.scalar_one_or_none()
        if not share:
            return None
        return await self.get_trip(share.trip_id)

    async def delete_share(self, trip_id: str) -> bool:
        """Revoke sharing for a trip."""
        result = await self.session.execute(
            delete(TripShare).where(TripShare.trip_id == trip_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def get_trip_user_id(self, trip_id: str) -> str | None:
        """Get the user_id for a trip. Returns None if trip doesn't exist or has no owner."""
        result = await self.session.execute(
            select(Trip.user_id).where(Trip.id == trip_id)
        )
        return result.scalar_one_or_none()

    async def get_share_token(self, trip_id: str) -> str | None:
        """Get existing share token for a trip, if any."""
        result = await self.session.execute(
            select(TripShare.share_token).where(TripShare.trip_id == trip_id)
        )
        return result.scalar_one_or_none()

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
