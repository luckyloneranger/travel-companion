"""Tests for itinerary API endpoints and models."""

import pytest
from datetime import date, timedelta

from app.models import ItineraryRequest, Pace


class TestItineraryRequest:
    """Tests for ItineraryRequest model validation."""

    def test_valid_request(self):
        """Test valid request passes validation."""
        request = ItineraryRequest(
            destination="Paris, France",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            interests=["art", "food"],
            pace=Pace.MODERATE,
        )
        assert request.destination == "Paris, France"
        assert len(request.interests) == 2

    def test_end_date_before_start_raises_error(self):
        """Test that end_date before start_date raises validation error."""
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            ItineraryRequest(
                destination="Paris",
                start_date=date.today() + timedelta(days=10),
                end_date=date.today() + timedelta(days=5),
                interests=["art"],
                pace=Pace.MODERATE,
            )

    def test_trip_duration_exceeds_limit(self):
        """Test that trip over 14 days raises validation error."""
        with pytest.raises(ValueError, match="cannot exceed 14 days"):
            ItineraryRequest(
                destination="Paris",
                start_date=date.today() + timedelta(days=1),
                end_date=date.today() + timedelta(days=20),
                interests=["art"],
                pace=Pace.MODERATE,
            )

    def test_invalid_interest_raises_error(self):
        """Test that invalid interests raise validation error."""
        with pytest.raises(ValueError, match="Invalid interests"):
            ItineraryRequest(
                destination="Paris",
                start_date=date.today() + timedelta(days=1),
                end_date=date.today() + timedelta(days=3),
                interests=["invalid_interest"],
                pace=Pace.MODERATE,
            )


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
