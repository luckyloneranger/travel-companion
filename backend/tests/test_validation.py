"""Edge case tests for API endpoint validation."""

from datetime import date

import pytest
from httpx import AsyncClient


class TestPlanTripValidation:
    """Test request validation for the plan endpoint."""

    @pytest.mark.asyncio
    async def test_missing_destination(self, client: AsyncClient):
        """Request without destination should fail."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "total_days": 3,
                "start_date": "2026-06-15",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_destination(self, client: AsyncClient):
        """Empty destination string should fail validation."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "",
                "total_days": 3,
                "start_date": "2026-06-15",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_short_destination(self, client: AsyncClient):
        """Single-char destination should fail (min_length=2)."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "X",
                "total_days": 3,
                "start_date": "2026-06-15",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_zero_days(self, client: AsyncClient):
        """Zero days should fail validation (ge=1)."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "Paris",
                "total_days": 0,
                "start_date": "2026-06-15",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_too_many_days(self, client: AsyncClient):
        """More than 21 days should fail validation (le=21)."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "Paris",
                "total_days": 22,
                "start_date": "2026-06-15",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_date(self, client: AsyncClient):
        """Invalid date string should fail."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "Paris",
                "total_days": 3,
                "start_date": "not-a-date",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_pace(self, client: AsyncClient):
        """Invalid pace value should fail."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "Paris",
                "total_days": 3,
                "start_date": "2026-06-15",
                "pace": "extreme",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_travel_mode(self, client: AsyncClient):
        """Invalid travel mode should fail."""
        response = await client.post(
            "/api/trips/plan/stream",
            json={
                "destination": "Paris",
                "total_days": 3,
                "start_date": "2026-06-15",
                "travel_mode": "HELICOPTER",
            },
        )
        assert response.status_code == 422


class TestChatValidation:
    """Test request validation for the chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_trip_not_found(self, client: AsyncClient):
        """Chat on nonexistent trip returns 404."""
        response = await client.post(
            "/api/trips/nonexistent/chat",
            json={"message": "change destination", "context": "journey"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_missing_message(self, client: AsyncClient):
        """Chat without message field should fail."""
        response = await client.post(
            "/api/trips/some-id/chat",
            json={"context": "journey"},
        )
        assert response.status_code == 422


class TestTipsValidation:
    """Test request validation for the tips endpoint."""

    @pytest.mark.asyncio
    async def test_tips_trip_not_found(self, client: AsyncClient):
        """Tips on nonexistent trip returns 404."""
        response = await client.post(
            "/api/trips/nonexistent/tips",
            json=[],
        )
        assert response.status_code == 404


class TestDayPlanValidation:
    """Test day plan generation validation."""

    @pytest.mark.asyncio
    async def test_day_plans_trip_not_found(self, client: AsyncClient):
        """Day plans for nonexistent trip returns 404."""
        response = await client.post(
            "/api/trips/nonexistent/days/stream",
            json={},
        )
        assert response.status_code == 404


class TestPlacesSearch:
    """Test places search endpoint."""

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client: AsyncClient):
        """Search without query should fail."""
        response = await client.get("/api/places/search")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_short_query(self, client: AsyncClient):
        """Search with too-short query should fail (min_length=2)."""
        response = await client.get("/api/places/search?query=x")
        assert response.status_code == 422
