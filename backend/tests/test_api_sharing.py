"""Tests for the sharing API."""

import pytest


@pytest.mark.asyncio
async def test_get_shared_not_found(client):
    """GET /api/shared/{token} returns 404 for invalid token."""
    resp = await client.get("/api/shared/invalid-token-abc")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Shared journey not found"
