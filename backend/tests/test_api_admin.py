"""Tests for the admin API and job polling."""

import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    """GET /api/jobs/{id} returns 404 for non-existent job."""
    resp = await client.get(f"/api/jobs/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_admin_stats_requires_auth(client):
    """GET /api/admin/stats requires authentication."""
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_authenticated(client):
    """GET /api/admin/stats returns stats when authenticated."""
    resp = await client.get("/api/admin/stats", headers={"x-test-user": "1"})
    assert resp.status_code == 200
    assert resp.json()["cities_count"] == 0
