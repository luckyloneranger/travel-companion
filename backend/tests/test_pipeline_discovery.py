"""Tests for the discovery pipeline."""

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.common import Location
from app.models.internal import PlaceCandidate
from app.pipelines.discovery import DiscoveryPipeline, DiscoveryResult


def _make_candidate(
    place_id: str,
    name: str = "Test Place",
    rating: float = 4.5,
    user_ratings_total: int = 500,
    types: list[str] | None = None,
) -> PlaceCandidate:
    return PlaceCandidate(
        place_id=place_id,
        name=name,
        address="123 Test St",
        location=Location(lat=35.6762, lng=139.6503),
        types=types or ["tourist_attraction"],
        rating=rating,
        user_ratings_total=user_ratings_total,
    )


def _make_lodging_candidate(place_id: str, name: str = "Test Hotel") -> PlaceCandidate:
    return _make_candidate(
        place_id=place_id,
        name=name,
        types=["lodging", "hotel"],
    )


def _mock_places_service() -> AsyncMock:
    svc = AsyncMock()
    svc.geocode.return_value = {
        "name": "Tokyo",
        "place_id": "geo_tokyo",
        "lat": 35.6762,
        "lng": 139.6503,
        "country": "JP",
        "timezone": "UTC+09:00",
        "utc_offset_minutes": 540,
    }
    svc.discover_places.return_value = [
        _make_candidate("place_1", "Senso-ji"),
        _make_candidate("place_2", "Tokyo Tower"),
    ]
    svc.text_search_places.return_value = [
        _make_candidate("place_3", "Meiji Shrine"),
    ]
    svc.search_lodging.return_value = _make_lodging_candidate("hotel_1", "Park Hyatt")
    return svc


@pytest.mark.asyncio
async def test_discover_returns_candidates():
    """Discovery returns activity candidates and lodging separately."""
    svc = _mock_places_service()
    pipeline = DiscoveryPipeline(svc)

    result = await pipeline.discover("Tokyo", interests=["culture"])

    assert isinstance(result, DiscoveryResult)
    assert result.city_metadata["name"] == "Tokyo"
    assert len(result.candidates) > 0
    assert len(result.lodging_candidates) > 0
    assert result.data_hash  # non-empty hash

    # All candidates have place_id
    for c in result.candidates:
        assert "place_id" in c
        assert c["place_id"]


@pytest.mark.asyncio
async def test_discover_deduplicates():
    """Same place_id appearing in multiple results is counted only once."""
    svc = _mock_places_service()
    # Return the same place from both discover_places and text_search
    dup = _make_candidate("place_dup", "Duplicate Place")
    svc.discover_places.return_value = [dup]
    svc.text_search_places.return_value = [dup]

    pipeline = DiscoveryPipeline(svc)
    result = await pipeline.discover("Tokyo")

    place_ids = [c["place_id"] for c in result.candidates]
    assert place_ids.count("place_dup") == 1


@pytest.mark.asyncio
async def test_discover_separates_lodging():
    """Lodging types go to lodging_candidates, not activity candidates."""
    svc = _mock_places_service()
    # Include a lodging type in discover_places results
    hotel_in_activities = _make_lodging_candidate("hotel_mixed", "Rogue Hotel")
    activity = _make_candidate("act_1", "Museum")
    svc.discover_places.return_value = [hotel_in_activities, activity]
    svc.text_search_places.return_value = []
    svc.search_lodging.return_value = None

    pipeline = DiscoveryPipeline(svc)
    result = await pipeline.discover("Tokyo")

    candidate_ids = [c["place_id"] for c in result.candidates]
    lodging_ids = [c["place_id"] for c in result.lodging_candidates]

    assert "hotel_mixed" not in candidate_ids
    assert "hotel_mixed" in lodging_ids
    assert "act_1" in candidate_ids


@pytest.mark.asyncio
async def test_discover_quality_filter():
    """Low-rated places are filtered out by adaptive quality filters."""
    svc = _mock_places_service()
    low_rated = _make_candidate("low_1", "Bad Place", rating=2.0, user_ratings_total=5)
    high_rated = _make_candidate("high_1", "Great Place", rating=4.8, user_ratings_total=1000)
    svc.discover_places.return_value = [low_rated, high_rated]
    svc.text_search_places.return_value = []

    pipeline = DiscoveryPipeline(svc)
    result = await pipeline.discover("Tokyo")

    candidate_ids = [c["place_id"] for c in result.candidates]
    assert "low_1" not in candidate_ids
    assert "high_1" in candidate_ids


@pytest.mark.asyncio
async def test_discover_computes_hash():
    """data_hash is consistent for the same set of place_ids."""
    svc = _mock_places_service()
    pipeline = DiscoveryPipeline(svc)

    result1 = await pipeline.discover("Tokyo")
    result2 = await pipeline.discover("Tokyo")

    assert result1.data_hash == result2.data_hash
    assert len(result1.data_hash) == 64  # SHA-256 hex length
