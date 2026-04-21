"""Repository classes for content library database operations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from .models import (
    Activity,
    City,
    DayPlan,
    GenerationJob,
    Journey,
    JourneyShare,
    Place,
    PlanVariant,
    Route,
    User,
)

logger = logging.getLogger(__name__)


class CityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        country: str,
        country_code: str,
        location: dict,
        timezone: str,
        currency: str,
        population_tier: str,
        region: str | None = None,
    ) -> City:
        city = City(
            name=name,
            country=country,
            country_code=country_code,
            location=location,
            timezone=timezone,
            currency=currency,
            population_tier=population_tier,
            region=region,
        )
        self.session.add(city)
        await self.session.commit()
        await self.session.refresh(city)
        return city

    async def get(self, city_id: UUID) -> City | None:
        return await self.session.get(City, city_id)

    async def get_by_name(self, name: str, country_code: str) -> City | None:
        result = await self.session.execute(
            select(City).where(City.name == name, City.country_code == country_code)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        region: str | None = None,
        sort: str = "name",
    ) -> tuple[list[City], int]:
        query = select(City)
        count_query = select(func.count()).select_from(City)

        if region:
            query = query.where(City.region == region)
            count_query = count_query.where(City.region == region)

        sort_col = City.name if sort == "name" else City.created_at
        query = query.order_by(sort_col).limit(limit).offset(offset)

        result = await self.session.execute(query)
        cities = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return cities, total

    async def update(self, city_id: UUID, **kwargs) -> City | None:
        city = await self.get(city_id)
        if not city:
            return None
        for key, value in kwargs.items():
            setattr(city, key, value)
        await self.session.commit()
        await self.session.refresh(city)
        return city


class PlaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_from_google(
        self, city_id: UUID, google_place_id: str, **place_data
    ) -> Place:
        existing = await self.get_by_google_id(google_place_id)
        if existing:
            for key, value in place_data.items():
                setattr(existing, key, value)
            existing.city_id = city_id
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        place = Place(
            city_id=city_id,
            google_place_id=google_place_id,
            **place_data,
        )
        self.session.add(place)
        await self.session.commit()
        await self.session.refresh(place)
        return place

    async def get_by_city(
        self, city_id: UUID, lodging_only: bool = False
    ) -> list[Place]:
        query = select(Place).where(Place.city_id == city_id)
        if lodging_only:
            query = query.where(Place.is_lodging.is_(True))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get(self, place_id: UUID) -> Place | None:
        return await self.session.get(Place, place_id)

    async def get_by_google_id(self, google_place_id: str) -> Place | None:
        result = await self.session.execute(
            select(Place).where(Place.google_place_id == google_place_id)
        )
        return result.scalar_one_or_none()


class VariantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, city_id: UUID, pace: str, budget: str, day_count: int, **kwargs
    ) -> PlanVariant:
        variant = PlanVariant(
            city_id=city_id,
            pace=pace,
            budget=budget,
            day_count=day_count,
            **kwargs,
        )
        self.session.add(variant)
        await self.session.commit()
        await self.session.refresh(variant)
        return variant

    async def lookup(
        self,
        city_id: UUID,
        pace: str,
        budget: str,
        day_count: int,
        status: str = "published",
    ) -> PlanVariant | None:
        result = await self.session.execute(
            select(PlanVariant).where(
                PlanVariant.city_id == city_id,
                PlanVariant.pace == pace,
                PlanVariant.budget == budget,
                PlanVariant.day_count == day_count,
                PlanVariant.status == status,
            )
        )
        return result.scalar_one_or_none()

    async def get_detail(self, variant_id: UUID) -> PlanVariant | None:
        result = await self.session.execute(
            select(PlanVariant)
            .where(PlanVariant.id == variant_id)
            .options(
                selectinload(PlanVariant.day_plans)
                .selectinload(DayPlan.activities)
                .joinedload(Activity.place),
                selectinload(PlanVariant.day_plans)
                .selectinload(DayPlan.routes),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_city(
        self, city_id: UUID, pace: str | None = None, budget: str | None = None
    ) -> list[PlanVariant]:
        query = select(PlanVariant).where(PlanVariant.city_id == city_id)
        if pace:
            query = query.where(PlanVariant.pace == pace)
        if budget:
            query = query.where(PlanVariant.budget == budget)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self, variant_id: UUID, status: str, **kwargs
    ) -> PlanVariant | None:
        variant = await self.session.get(PlanVariant, variant_id)
        if not variant:
            return None
        variant.status = status
        for key, value in kwargs.items():
            setattr(variant, key, value)
        await self.session.commit()
        await self.session.refresh(variant)
        return variant


class DayPlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_with_activities(
        self,
        variant_id: UUID,
        day_number: int,
        theme: str,
        theme_description: str | None,
        activities: list[dict],
        routes: list[dict],
    ) -> DayPlan:
        day_plan = DayPlan(
            variant_id=variant_id,
            day_number=day_number,
            theme=theme,
            theme_description=theme_description,
        )
        self.session.add(day_plan)
        await self.session.flush()

        # Create activities and collect them by sequence for route wiring
        created_activities = []
        for act_data in activities:
            activity = Activity(day_plan_id=day_plan.id, **act_data)
            self.session.add(activity)
            created_activities.append(activity)
        await self.session.flush()  # assigns IDs to activities

        # Create routes, wiring from/to activity IDs by sequence
        activity_by_seq = {a.sequence: a for a in created_activities}
        for route_data in routes:
            from_seq = route_data.pop("from_sequence", None)
            to_seq = route_data.pop("to_sequence", None)
            # Also handle from_activity_id/to_activity_id if already set
            from_id = route_data.pop("from_activity_id", None)
            to_id = route_data.pop("to_activity_id", None)

            if not from_id and from_seq is not None and from_seq in activity_by_seq:
                from_id = activity_by_seq[from_seq].id
            if not to_id and to_seq is not None and to_seq in activity_by_seq:
                to_id = activity_by_seq[to_seq].id

            # Skip routes without valid activity references
            if not from_id or not to_id:
                continue

            route = Route(
                day_plan_id=day_plan.id,
                from_activity_id=from_id,
                to_activity_id=to_id,
                **route_data,
            )
            self.session.add(route)

        await self.session.commit()
        await self.session.refresh(day_plan)
        return day_plan


class JourneyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        destination: str,
        start_date: str,
        total_days: int,
        pace: str,
        budget: str,
        city_sequence: list[dict],
        **kwargs,
    ) -> Journey:
        journey = Journey(
            user_id=user_id,
            destination=destination,
            start_date=start_date,
            total_days=total_days,
            pace=pace,
            budget=budget,
            city_sequence=city_sequence,
            **kwargs,
        )
        self.session.add(journey)
        await self.session.commit()
        await self.session.refresh(journey)
        return journey

    async def get(self, journey_id: UUID) -> Journey | None:
        return await self.session.get(Journey, journey_id)

    async def list_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[Journey], int]:
        query = (
            select(Journey)
            .where(Journey.user_id == user_id)
            .order_by(Journey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        journeys = list(result.scalars().all())

        count_result = await self.session.execute(
            select(func.count()).select_from(Journey).where(Journey.user_id == user_id)
        )
        total = count_result.scalar_one()

        return journeys, total

    async def delete(self, journey_id: UUID) -> bool:
        journey = await self.get(journey_id)
        if not journey:
            return False
        await self.session.delete(journey)
        await self.session.commit()
        return True


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        job_type: str,
        city_id: UUID | None = None,
        parameters: dict | None = None,
        priority: int = 0,
    ) -> GenerationJob:
        job = GenerationJob(
            job_type=job_type,
            city_id=city_id,
            parameters=parameters or {},
            priority=priority,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def pick_next(self, worker_id: str) -> GenerationJob | None:
        """Pick the next queued job using SELECT FOR UPDATE SKIP LOCKED."""
        query = (
            select(GenerationJob)
            .where(GenerationJob.status == "queued")
            .order_by(GenerationJob.priority.desc(), GenerationJob.created_at.asc())
            .limit(1)
        )
        # FOR UPDATE SKIP LOCKED is PostgreSQL-specific; skip for SQLite
        dialect = self.session.bind.dialect.name if self.session.bind else ""
        if dialect != "sqlite":
            query = query.with_for_update(skip_locked=True)
        result = await self.session.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            return None

        now = datetime.now(timezone.utc)
        job.status = "running"
        job.locked_by = worker_id
        job.locked_at = now
        job.started_at = now
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def complete(self, job_id: UUID, result: dict | None = None) -> None:
        job = await self.session.get(GenerationJob, job_id)
        if not job:
            return
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.progress_pct = 100
        job.result = result
        await self.session.commit()

    async def fail(self, job_id: UUID, error: str) -> None:
        job = await self.session.get(GenerationJob, job_id)
        if not job:
            return
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        job.error = error
        await self.session.commit()

    async def update_progress(self, job_id: UUID, progress_pct: int) -> None:
        job = await self.session.get(GenerationJob, job_id)
        if not job:
            return
        job.progress_pct = progress_pct
        await self.session.commit()

    async def get(self, job_id: UUID) -> GenerationJob | None:
        return await self.session.get(GenerationJob, job_id)

    async def recover_stale(self, timeout_minutes: int = 15) -> int:
        """Reset running jobs that have been locked longer than timeout."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        result = await self.session.execute(
            update(GenerationJob)
            .where(
                GenerationJob.status == "running",
                GenerationJob.locked_at < cutoff,
            )
            .values(
                status="queued",
                locked_by=None,
                locked_at=None,
                started_at=None,
            )
        )
        await self.session.commit()
        return result.rowcount


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self,
        provider: str,
        provider_id: str,
        email: str | None,
        name: str | None,
        avatar_url: str | None,
    ) -> User:
        result = await self.session.execute(
            select(User).where(User.provider == provider, User.provider_id == provider_id)
        )
        user = result.scalar_one_or_none()
        if user:
            if name:
                user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            await self.session.commit()
            await self.session.refresh(user)
            return user

        user = User(
            email=email,
            name=name,
            avatar_url=avatar_url,
            provider=provider,
            provider_id=provider_id,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)


class JourneyShareRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, journey_id: UUID, token: str) -> JourneyShare:
        share = JourneyShare(journey_id=journey_id, token=token)
        self.session.add(share)
        await self.session.commit()
        await self.session.refresh(share)
        return share

    async def get_by_token(self, token: str) -> JourneyShare | None:
        result = await self.session.execute(
            select(JourneyShare).where(JourneyShare.token == token)
        )
        return result.scalar_one_or_none()

    async def delete_by_journey(self, journey_id: UUID) -> bool:
        result = await self.session.execute(
            select(JourneyShare).where(JourneyShare.journey_id == journey_id)
        )
        share = result.scalar_one_or_none()
        if not share:
            return False
        await self.session.delete(share)
        await self.session.commit()
        return True
