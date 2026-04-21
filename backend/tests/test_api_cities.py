"""Tests for the cities catalog API."""

import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_list_cities_empty(client):
    """GET /api/cities returns empty list when no cities exist."""
    resp = await client.get("/api/cities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cities"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_city_not_found(client):
    """GET /api/cities/{id} returns 404 for non-existent city."""
    resp = await client.get(f"/api/cities/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "City not found"


@pytest.mark.asyncio
async def test_get_variant_not_found(client):
    """GET /api/cities/{id}/variants/{id} returns 404."""
    resp = await client.get(f"/api/cities/{uuid4()}/variants/{uuid4()}")
    assert resp.status_code == 404
