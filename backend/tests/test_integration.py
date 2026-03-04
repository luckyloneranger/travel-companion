"""Integration tests for trip lifecycle via API endpoints."""

import pytest
from httpx import AsyncClient


class TestTripApiLifecycle:
    """Test the trip lifecycle via API endpoints."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient):
        """List trips returns empty initially."""
        response = await client.get("/api/trips", headers={"x-test-user": "true"})
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client: AsyncClient):
        """Get non-existent trip returns 404."""
        response = await client.get("/api/trips/does-not-exist", headers={"x-test-user": "true"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient):
        """Delete for non-existent trip returns 404."""
        response = await client.delete(
            "/api/trips/does-not-exist",
            headers={"x-test-user": "true"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_nonexistent_trip(self, client: AsyncClient):
        """Chat on nonexistent trip returns 404."""
        response = await client.post(
            "/api/trips/nonexistent-id/chat",
            json={"message": "change destination", "context": "journey"},
            headers={"x-test-user": "true"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_day_plans_nonexistent_trip(self, client: AsyncClient):
        """Day plans for nonexistent trip returns 404."""
        response = await client.post(
            "/api/trips/nonexistent-id/days/stream",
            json={},
            headers={"x-test-user": "true"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tips_nonexistent_trip(self, client: AsyncClient):
        """Tips on nonexistent trip returns 404."""
        response = await client.post(
            "/api/trips/nonexistent-id/tips",
            json=[],
            headers={"x-test-user": "true"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Health check returns all expected fields."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "llm_provider" in data
