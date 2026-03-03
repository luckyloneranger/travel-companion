"""End-to-end API tests for the Travel Companion V2 backend.

All external services (LLM, Google APIs) are mocked via dependency overrides
defined in conftest.py. The database is an in-memory SQLite instance that is
created and torn down for every test.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.dependencies import get_journey_orchestrator
from app.models.journey import CityStop, JourneyPlan, TravelLeg
from app.models.progress import ProgressEvent
from app.models.trip import TripRequest
from app.orchestrators.journey import JourneyOrchestrator


# ── Helpers ────────────────────────────────────────────────────────────


def _make_trip_request(**overrides) -> dict:
    """Return a valid TripRequest body as a dict."""
    base = {
        "destination": "Tokyo, Japan",
        "total_days": 3,
        "start_date": str(date(2026, 6, 1)),
        "interests": ["culture", "food"],
        "pace": "moderate",
        "travel_mode": "WALK",
    }
    base.update(overrides)
    return base


def _make_journey_plan() -> JourneyPlan:
    """Build a minimal but valid JourneyPlan for mocking."""
    return JourneyPlan(
        theme="Cultural Discovery",
        summary="A 3-day Tokyo adventure",
        origin="",
        cities=[
            CityStop(
                name="Tokyo",
                country="Japan",
                days=3,
                why_visit="World-class culture and cuisine",
            ),
        ],
        travel_legs=[],
        total_days=3,
        review_score=85,
        route="Tokyo",
    )


def _parse_sse_events(body: str) -> list[dict]:
    """Parse a raw SSE body into a list of JSON dicts."""
    events: list[dict] = []
    for line in body.strip().splitlines():
        if line.startswith("data: "):
            raw = line[len("data: "):]
            events.append(json.loads(raw))
    return events


# ── Tests ──────────────────────────────────────────────────────────────


class TestHealthCheck:
    async def test_returns_200_with_status(self, client: AsyncClient):
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"


class TestListTrips:
    async def test_empty_list(self, client: AsyncClient):
        """An empty database should return an empty list."""
        response = await client.get("/api/trips")

        assert response.status_code == 200
        assert response.json() == []


class TestGetTrip:
    async def test_not_found(self, client: AsyncClient):
        """Requesting a non-existent trip should return 404."""
        response = await client.get("/api/trips/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestPlanTripStream:
    async def test_stream_returns_sse_events(self, client: AsyncClient, app):
        """POST /api/trips/plan/stream should yield SSE progress events
        followed by a completion event containing the journey plan."""

        plan = _make_journey_plan()

        # Build a mock orchestrator whose plan_stream yields known events
        mock_orchestrator = AsyncMock(spec=JourneyOrchestrator)

        async def _fake_plan_stream(request: TripRequest) -> AsyncGenerator[ProgressEvent, None]:
            yield ProgressEvent(phase="scouting", message="Creating your journey...", progress=10)
            yield ProgressEvent(phase="enriching", message="Validating with real data...", progress=40)
            yield ProgressEvent(
                phase="complete",
                message="Journey planned! Score: 85",
                progress=100,
                data=plan.model_dump(),
            )

        mock_orchestrator.plan_stream = _fake_plan_stream

        # Override the orchestrator dependency
        app.dependency_overrides[get_journey_orchestrator] = lambda: mock_orchestrator

        response = await client.post(
            "/api/trips/plan/stream",
            json=_make_trip_request(),
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = _parse_sse_events(response.text)
        assert len(events) >= 2  # at least progress + complete

        # First event should be progress
        assert events[0]["phase"] == "scouting"
        assert events[0]["progress"] == 10

        # Last event should be completion with a trip_id injected by the router
        complete_event = events[-1]
        assert complete_event["phase"] == "complete"
        assert complete_event["progress"] == 100
        # The router saves the trip and injects trip_id into the data
        assert "data" in complete_event
        assert complete_event["data"] is not None

    async def test_stream_handles_error(self, client: AsyncClient, app):
        """If the orchestrator raises, the stream should emit an error event."""

        mock_orchestrator = AsyncMock(spec=JourneyOrchestrator)

        async def _failing_plan_stream(request: TripRequest) -> AsyncGenerator[ProgressEvent, None]:
            yield ProgressEvent(phase="scouting", message="Starting...", progress=10)
            raise RuntimeError("LLM quota exceeded")

        mock_orchestrator.plan_stream = _failing_plan_stream

        app.dependency_overrides[get_journey_orchestrator] = lambda: mock_orchestrator

        response = await client.post(
            "/api/trips/plan/stream",
            json=_make_trip_request(),
        )

        assert response.status_code == 200  # SSE always returns 200; errors are in the stream
        events = _parse_sse_events(response.text)

        # Should contain an error event
        error_events = [e for e in events if e.get("phase") == "error"]
        assert len(error_events) == 1
        assert "quota" in error_events[0]["message"].lower()


class TestDeleteTrip:
    async def test_delete_not_found(self, client: AsyncClient):
        """Deleting a non-existent trip should return 404."""
        response = await client.delete("/api/trips/nonexistent-id")
        assert response.status_code == 404
