"""Tests for the new content library repository classes.

Uses aiosqlite for local testing (no Docker needed).
PostgreSQL-specific features (FOR UPDATE SKIP LOCKED) are tested via
behavioral assertions rather than SQL-level verification.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, User
from app.db.repository import (
    CityRepository,
    DayPlanRepository,
    JobRepository,
    JourneyRepository,
    JourneyShareRepository,
    PlaceRepository,
    UserRepository,
    VariantRepository,
)

# ── Test DB setup (SQLite async) ─────────────────────────────────────

TEST_USER_ID = "repo-test-user"

_engine = None
_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False, future=True
        )
    return _engine


def _get_factory():
    global _factory
    if _factory is None:
        _factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _factory


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _factory = None

    engine = _get_engine()

    # SQLite needs foreign keys enabled per connection
    @event.listens_for(engine.sync_engine, "connect")
    def _set_fk(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _get_factory()() as session:
        session.add(User(
            id=TEST_USER_ID,
            email="repo-test@example.com",
            name="Repo Test User",
            provider="test",
        ))
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _engine = None
    _factory = None


@pytest_asyncio.fixture
async def db_session():
    async with _get_factory()() as session:
        yield session


# ── City tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_city(db_session: AsyncSession):
    repo = CityRepository(db_session)
    city = await repo.create(
        name="Tokyo",
        country="Japan",
        country_code="JP",
        location={"lat": 35.6762, "lng": 139.6503},
        timezone="Asia/Tokyo",
        currency="JPY",
        population_tier="mega",
        region="East Asia",
    )
    assert city.id is not None
    assert city.name == "Tokyo"

    fetched = await repo.get(city.id)
    assert fetched is not None
    assert fetched.country_code == "JP"


@pytest.mark.asyncio
async def test_get_city_by_name(db_session: AsyncSession):
    repo = CityRepository(db_session)
    await repo.create(
        name="Paris",
        country="France",
        country_code="FR",
        location={"lat": 48.8566, "lng": 2.3522},
        timezone="Europe/Paris",
        currency="EUR",
        population_tier="large",
    )
    found = await repo.get_by_name("Paris", "FR")
    assert found is not None
    assert found.name == "Paris"

    not_found = await repo.get_by_name("Paris", "US")
    assert not_found is None


@pytest.mark.asyncio
async def test_list_cities_with_pagination(db_session: AsyncSession):
    repo = CityRepository(db_session)
    for i, (name, cc) in enumerate([
        ("Alpha", "AA"), ("Bravo", "BB"), ("Charlie", "CC"),
    ]):
        await repo.create(
            name=name, country=name, country_code=cc,
            location={"lat": 0.0, "lng": float(i)},
            timezone="UTC", currency="USD", population_tier="small",
        )

    cities, total = await repo.list(limit=2, offset=0)
    assert len(cities) == 2
    assert total == 3

    cities2, _ = await repo.list(limit=2, offset=2)
    assert len(cities2) == 1


# ── Place tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_place(db_session: AsyncSession):
    city_repo = CityRepository(db_session)
    city = await city_repo.create(
        name="Rome", country="Italy", country_code="IT",
        location={"lat": 41.9, "lng": 12.5},
        timezone="Europe/Rome", currency="EUR", population_tier="large",
    )

    place_repo = PlaceRepository(db_session)
    p1 = await place_repo.upsert_from_google(
        city_id=city.id, google_place_id="gp_colosseum",
        name="Colosseum", lat=41.89, lng=12.49, rating=4.8,
    )
    assert p1.name == "Colosseum"

    p2 = await place_repo.upsert_from_google(
        city_id=city.id, google_place_id="gp_colosseum",
        name="Colosseum", lat=41.89, lng=12.49, rating=4.9,
    )
    assert p2.id == p1.id
    assert p2.rating == 4.9


@pytest.mark.asyncio
async def test_get_places_by_city(db_session: AsyncSession):
    city_repo = CityRepository(db_session)
    city = await city_repo.create(
        name="Bangkok", country="Thailand", country_code="TH",
        location={"lat": 13.75, "lng": 100.5},
        timezone="Asia/Bangkok", currency="THB", population_tier="mega",
    )

    place_repo = PlaceRepository(db_session)
    await place_repo.upsert_from_google(
        city_id=city.id, google_place_id="gp_temple",
        name="Wat Arun", lat=13.74, lng=100.49,
    )
    await place_repo.upsert_from_google(
        city_id=city.id, google_place_id="gp_hotel",
        name="Hilton", lat=13.75, lng=100.51, is_lodging=1,
    )

    all_places = await place_repo.get_by_city(city.id)
    assert len(all_places) == 2

    lodging = await place_repo.get_by_city(city.id, lodging_only=True)
    assert len(lodging) == 1
    assert lodging[0].name == "Hilton"


# ── Variant tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_variant_and_lookup(db_session: AsyncSession):
    city_repo = CityRepository(db_session)
    city = await city_repo.create(
        name="Kyoto", country="Japan", country_code="JP",
        location={"lat": 35.01, "lng": 135.77},
        timezone="Asia/Tokyo", currency="JPY", population_tier="large",
    )

    variant_repo = VariantRepository(db_session)
    variant = await variant_repo.create(
        city_id=city.id, pace="relaxed", budget="moderate", day_count=3,
        status="published",
    )
    assert variant.id is not None

    found = await variant_repo.lookup(city.id, "relaxed", "moderate", 3)
    assert found is not None
    assert found.id == variant.id


@pytest.mark.asyncio
async def test_lookup_variant_not_found(db_session: AsyncSession):
    variant_repo = VariantRepository(db_session)
    result = await variant_repo.lookup(uuid.uuid4(), "relaxed", "moderate", 3)
    assert result is None


# ── Job tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_pick_job(db_session: AsyncSession):
    repo = JobRepository(db_session)
    job = await repo.create(job_type="variant_generation", parameters={"pace": "relaxed"})
    assert job.status == "queued"

    picked = await repo.pick_next("worker-1")
    assert picked is not None
    assert picked.id == job.id
    assert picked.status == "running"
    assert picked.locked_by == "worker-1"


@pytest.mark.asyncio
async def test_pick_job_skip_locked(db_session: AsyncSession):
    """After picking the only queued job, second pick returns None."""
    repo = JobRepository(db_session)
    await repo.create(job_type="test_job")

    picked1 = await repo.pick_next("worker-1")
    assert picked1 is not None

    picked2 = await repo.pick_next("worker-2")
    assert picked2 is None


@pytest.mark.asyncio
async def test_complete_job(db_session: AsyncSession):
    repo = JobRepository(db_session)
    await repo.create(job_type="test_job")
    picked = await repo.pick_next("worker-1")

    await repo.complete(picked.id, result={"ok": True})
    completed = await repo.get(picked.id)
    assert completed.status == "completed"
    assert completed.progress_pct == 100
    assert completed.result == {"ok": True}


@pytest.mark.asyncio
async def test_fail_job(db_session: AsyncSession):
    repo = JobRepository(db_session)
    await repo.create(job_type="test_job")
    picked = await repo.pick_next("worker-1")

    await repo.fail(picked.id, error="something broke")
    failed = await repo.get(picked.id)
    assert failed.status == "failed"
    assert failed.error == "something broke"


@pytest.mark.asyncio
async def test_recover_stale_jobs(db_session: AsyncSession):
    repo = JobRepository(db_session)
    await repo.create(job_type="test_job")
    picked = await repo.pick_next("worker-1")

    # Backdate locked_at to simulate stale job
    picked.locked_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    await db_session.commit()

    count = await repo.recover_stale(timeout_minutes=15)
    assert count == 1

    recovered = await repo.get(picked.id)
    assert recovered.status == "queued"
    assert recovered.locked_by is None


# ── Journey tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_journey(db_session: AsyncSession):
    repo = JourneyRepository(db_session)
    journey = await repo.create(
        user_id=TEST_USER_ID,
        destination="Japan",
        start_date="2026-05-01",
        total_days=10,
        pace="relaxed",
        budget="moderate",
        city_sequence=[{"city": "Tokyo", "days": 4}, {"city": "Kyoto", "days": 3}],
    )
    assert journey.id is not None

    fetched = await repo.get(journey.id)
    assert fetched is not None
    assert fetched.destination == "Japan"
    assert len(fetched.city_sequence) == 2


@pytest.mark.asyncio
async def test_list_journeys_by_user(db_session: AsyncSession):
    repo = JourneyRepository(db_session)
    for dest in ["Japan", "France", "Italy"]:
        await repo.create(
            user_id=TEST_USER_ID, destination=dest,
            start_date="2026-06-01", total_days=5,
            pace="moderate", budget="moderate", city_sequence=[],
        )

    journeys, total = await repo.list_by_user(TEST_USER_ID)
    assert total == 3
    assert len(journeys) == 3


@pytest.mark.asyncio
async def test_delete_journey(db_session: AsyncSession):
    repo = JourneyRepository(db_session)
    journey = await repo.create(
        user_id=TEST_USER_ID, destination="Spain",
        start_date="2026-07-01", total_days=5,
        pace="packed", budget="budget", city_sequence=[],
    )

    deleted = await repo.delete(journey.id)
    assert deleted is True

    fetched = await repo.get(journey.id)
    assert fetched is None

    assert await repo.delete(uuid.uuid4()) is False
