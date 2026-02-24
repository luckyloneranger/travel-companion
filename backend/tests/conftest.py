"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_itinerary_request():
    """Sample valid itinerary request."""
    return {
        "destination": "Paris, France",
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "interests": ["art", "food"],
        "pace": "moderate",
    }
