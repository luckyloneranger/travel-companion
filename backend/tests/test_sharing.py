"""Tests for trip sharing endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestSharing:
    @pytest.mark.asyncio
    async def test_shared_trip_not_found(self, client: AsyncClient):
        """GET /api/shared/<token> with a bad token returns 404."""
        response = await client.get("/api/shared/nonexistent-token")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_share_requires_auth(self, client: AsyncClient):
        """POST /api/trips/<id>/share without auth returns 401."""
        response = await client.post("/api/trips/some-id/share")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unshare_requires_auth(self, client: AsyncClient):
        """DELETE /api/trips/<id>/share without auth returns 401."""
        response = await client.delete("/api/trips/some-id/share")
        assert response.status_code == 401
