"""Tests for the journey assembler module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import date

from app.assembler.allocator import CityAllocator, CityAllocationOutput
from app.assembler.lookup import VariantLookup, LookupResult
from app.assembler.connector import CityConnector
from app.assembler.assembler import JourneyAssembler


# ── CityAllocator ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allocator_splits_days():
    """Mock LLM returns city allocations, verify total days match."""
    mock_llm = AsyncMock()
    mock_llm.generate_structured.return_value = CityAllocationOutput(
        cities=[
            {"name": "Tokyo", "country": "Japan", "day_count": 4, "order": 1},
            {"name": "Kyoto", "country": "Japan", "day_count": 3, "order": 2},
            {"name": "Osaka", "country": "Japan", "day_count": 3, "order": 3},
        ]
    )

    allocator = CityAllocator(llm_service=mock_llm)
    result = await allocator.allocate("Japan", total_days=10, pace="moderate", budget="moderate")

    assert len(result) == 3
    assert sum(c["day_count"] for c in result) == 10
    assert result[0]["name"] == "Tokyo"
    mock_llm.generate_structured.assert_called_once()


@pytest.mark.asyncio
async def test_allocator_adjusts_mismatched_days():
    """When LLM allocates wrong total, last city is adjusted."""
    mock_llm = AsyncMock()
    mock_llm.generate_structured.return_value = CityAllocationOutput(
        cities=[
            {"name": "Paris", "country": "France", "day_count": 3, "order": 1},
            {"name": "Lyon", "country": "France", "day_count": 2, "order": 2},
        ]
    )

    allocator = CityAllocator(llm_service=mock_llm)
    result = await allocator.allocate("France", total_days=7)

    # 3 + 2 = 5, but requested 7, so Lyon should become 2 + 2 = 4
    assert sum(c["day_count"] for c in result) == 7
    assert result[1]["day_count"] == 4


# ── VariantLookup ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lookup_finds_variant():
    """When city and published variant exist, returns them."""
    city_id = uuid4()
    variant_id = uuid4()

    mock_city = MagicMock()
    mock_city.id = city_id
    mock_city.name = "Tokyo"

    mock_variant = MagicMock()
    mock_variant.id = variant_id

    city_repo = AsyncMock()
    city_repo.list.return_value = ([mock_city], 1)

    variant_repo = AsyncMock()
    variant_repo.lookup.return_value = mock_variant

    lookup = VariantLookup(city_repo=city_repo, variant_repo=variant_repo)
    result = await lookup.find("Tokyo", country="Japan", pace="moderate", budget="moderate", day_count=3)

    assert result.city_id == city_id
    assert result.variant_id == variant_id
    assert result.needs_generation is False


@pytest.mark.asyncio
async def test_lookup_city_not_found():
    """When city doesn't exist in DB, returns needs_generation=True."""
    city_repo = AsyncMock()
    city_repo.list.return_value = ([], 0)

    variant_repo = AsyncMock()

    lookup = VariantLookup(city_repo=city_repo, variant_repo=variant_repo)
    result = await lookup.find("Atlantis", country="Ocean", pace="moderate", budget="moderate", day_count=3)

    assert result.city_id is None
    assert result.needs_generation is True
    variant_repo.lookup.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_falls_back_to_draft():
    """When no published variant, falls back to draft."""
    city_id = uuid4()
    variant_id = uuid4()

    mock_city = MagicMock()
    mock_city.id = city_id
    mock_city.name = "Kyoto"

    mock_variant = MagicMock()
    mock_variant.id = variant_id

    city_repo = AsyncMock()
    city_repo.list.return_value = ([mock_city], 1)

    variant_repo = AsyncMock()
    # First call (published) returns None, second call (draft) returns variant
    variant_repo.lookup.side_effect = [None, mock_variant]

    lookup = VariantLookup(city_repo=city_repo, variant_repo=variant_repo)
    result = await lookup.find("Kyoto", country="Japan", pace="moderate", budget="moderate", day_count=3)

    assert result.variant_id == variant_id
    assert result.needs_generation is False
    assert variant_repo.lookup.call_count == 2


# ── CityConnector ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connector_single_city():
    """Single city returns no legs."""
    directions = AsyncMock()
    connector = CityConnector(directions_service=directions)
    result = await connector.connect([{"city_name": "Tokyo", "location": {"lat": 35.6, "lng": 139.7}}])
    assert result == []


@pytest.mark.asyncio
async def test_connector_handles_failure():
    """When directions API fails, returns unknown mode leg."""
    directions = AsyncMock()
    directions.get_all_transport_options.side_effect = Exception("API down")

    connector = CityConnector(directions_service=directions)
    result = await connector.connect([
        {"city_name": "Tokyo", "location": {"lat": 35.6, "lng": 139.7}},
        {"city_name": "Kyoto", "location": {"lat": 35.0, "lng": 135.7}},
    ])

    assert len(result) == 1
    assert result[0]["mode"] == "unknown"
    assert result[0]["from_city"] == "Tokyo"
    assert result[0]["to_city"] == "Kyoto"


# ── JourneyAssembler ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assembler_complete_journey():
    """All cities cached — status=complete, no job_ids."""
    city_id = uuid4()
    variant_id = uuid4()
    journey_id = uuid4()

    allocator = AsyncMock()
    allocator.allocate.return_value = [
        {"name": "Paris", "country": "France", "day_count": 3, "order": 1},
    ]

    lookup = AsyncMock()
    lookup.find.return_value = LookupResult(
        city_id=city_id, city_name="Paris",
        variant_id=variant_id, variant=MagicMock(),
        needs_generation=False,
    )

    connector = AsyncMock()
    weather = AsyncMock()

    journey_repo = AsyncMock()
    mock_journey = MagicMock()
    mock_journey.id = journey_id
    journey_repo.create.return_value = mock_journey

    job_repo = AsyncMock()
    variant_repo = AsyncMock()

    assembler = JourneyAssembler(
        allocator=allocator, lookup=lookup, connector=connector,
        weather=weather, journey_repo=journey_repo,
        job_repo=job_repo, variant_repo=variant_repo,
    )

    result = await assembler.assemble(
        user_id=uuid4(), destination="France", origin="London",
        start_date=date(2026, 6, 1), total_days=3,
        pace="moderate", budget="moderate",
    )

    assert result["status"] == "complete"
    assert result["job_ids"] is None
    assert len(result["city_sequence"]) == 1
    assert result["city_sequence"][0]["variant_id"] == str(variant_id)
    journey_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_assembler_generating_journey():
    """Cache miss — status=generating with job_ids."""
    journey_id = uuid4()
    job_id = uuid4()

    allocator = AsyncMock()
    allocator.allocate.return_value = [
        {"name": "Bangkok", "country": "Thailand", "day_count": 4, "order": 1},
    ]

    lookup = AsyncMock()
    lookup.find.return_value = LookupResult(
        city_id=uuid4(), city_name="Bangkok",
        variant_id=None, variant=None,
        needs_generation=True,
    )

    connector = AsyncMock()
    weather = AsyncMock()

    journey_repo = AsyncMock()
    mock_journey = MagicMock()
    mock_journey.id = journey_id
    journey_repo.create.return_value = mock_journey

    job_repo = AsyncMock()
    mock_job = MagicMock()
    mock_job.id = job_id
    job_repo.create.return_value = mock_job

    variant_repo = AsyncMock()

    assembler = JourneyAssembler(
        allocator=allocator, lookup=lookup, connector=connector,
        weather=weather, journey_repo=journey_repo,
        job_repo=job_repo, variant_repo=variant_repo,
    )

    result = await assembler.assemble(
        user_id=uuid4(), destination="Thailand", origin=None,
        start_date=date(2026, 7, 1), total_days=4,
        pace="relaxed", budget="budget",
    )

    assert result["status"] == "generating"
    assert result["job_ids"] == [str(job_id)]
    assert result["city_sequence"][0]["variant_id"] is None
    job_repo.create.assert_called_once()
