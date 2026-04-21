"""Tests for the journeys API."""

import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_journey_requires_auth(client):
    """POST /api/journeys returns 401 without auth."""
    resp = await client.post("/api/journeys", json={
        "destination": "Japan",
        "start_date": "2026-05-01",
        "total_days": 7,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_journeys_empty(client):
    """GET /api/journeys returns empty list for authenticated user."""
    resp = await client.get("/api/journeys", headers={"x-test-user": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["journeys"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_journey_not_found(client):
    """GET /api/journeys/{id} returns 404 for non-existent journey."""
    resp = await client.get(f"/api/journeys/{uuid4()}", headers={"x-test-user": "1"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Journey not found"
