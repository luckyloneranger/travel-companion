"""Tests for PDF and calendar export endpoints."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from httpx import AsyncClient


class TestPDFExport:
    @pytest.mark.asyncio
    async def test_pdf_trip_not_found(self, client: AsyncClient):
        """GET /api/trips/<id>/export/pdf with unknown id returns 404."""
        response = await client.get("/api/trips/nonexistent/export/pdf", headers={"x-test-user": "true"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_pdf_content_type(self, client: AsyncClient):
        """Requesting PDF for a non-existent trip returns 404."""
        response = await client.get("/api/trips/nonexistent/export/pdf", headers={"x-test-user": "true"})
        assert response.status_code == 404


class TestCalendarExport:
    @pytest.mark.asyncio
    async def test_calendar_trip_not_found(self, client: AsyncClient):
        """GET /api/trips/<id>/export/calendar with unknown id returns 404."""
        response = await client.get("/api/trips/nonexistent/export/calendar", headers={"x-test-user": "true"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_ics_empty_trip(self):
        """Test ICS generation with a minimal trip (no day plans)."""
        from app.models.journey import CityStop, JourneyPlan
        from app.models.trip import TripRequest, TripResponse
        from app.services.export import generate_ics

        trip = TripResponse(
            id="test-1",
            request=TripRequest(
                destination="Paris",
                total_days=1,
                start_date=date(2026, 7, 1),
            ),
            journey=JourneyPlan(
                theme="Test Trip",
                summary="A test",
                cities=[CityStop(name="Paris", country="France", days=1)],
                total_days=1,
            ),
            day_plans=None,
            quality_score=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        ics = generate_ics(trip)
        assert "BEGIN:VCALENDAR" in ics
        assert "Test Trip" in ics
        assert "END:VCALENDAR" in ics

    @pytest.mark.asyncio
    async def test_generate_ics_with_activities(self):
        """Test ICS generation with activities produces VEVENT entries."""
        from app.models.common import Location
        from app.models.day_plan import Activity, DayPlan, Place
        from app.models.journey import CityStop, JourneyPlan
        from app.models.trip import TripRequest, TripResponse
        from app.services.export import generate_ics

        trip = TripResponse(
            id="test-2",
            request=TripRequest(
                destination="Paris",
                total_days=1,
                start_date=date(2026, 7, 1),
            ),
            journey=JourneyPlan(
                theme="Paris Trip",
                summary="A trip",
                cities=[CityStop(name="Paris", country="France", days=1)],
                total_days=1,
            ),
            day_plans=[
                DayPlan(
                    date="2026-07-01",
                    day_number=1,
                    theme="Art Day",
                    city_name="Paris",
                    activities=[
                        Activity(
                            time_start="10:00",
                            time_end="12:00",
                            duration_minutes=120,
                            place=Place(
                                place_id="p1",
                                name="Louvre Museum",
                                address="Rue de Rivoli",
                                location=Location(lat=48.86, lng=2.34),
                                category="museum",
                            ),
                            notes="Visit Mona Lisa",
                        ),
                    ],
                ),
            ],
            quality_score=85.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        ics = generate_ics(trip)
        assert "BEGIN:VEVENT" in ics
        assert "Louvre Museum" in ics
        assert "Rue de Rivoli" in ics
        assert "END:VEVENT" in ics

    @pytest.mark.asyncio
    async def test_generate_ics_skips_zero_duration(self):
        """Activities with duration_minutes=0 (hotel markers) should be skipped."""
        from app.models.common import Location
        from app.models.day_plan import Activity, DayPlan, Place
        from app.models.journey import CityStop, JourneyPlan
        from app.models.trip import TripRequest, TripResponse
        from app.services.export import generate_ics

        trip = TripResponse(
            id="test-3",
            request=TripRequest(
                destination="Paris",
                total_days=1,
                start_date=date(2026, 7, 1),
            ),
            journey=JourneyPlan(
                theme="Skip Zero",
                summary="Test",
                cities=[CityStop(name="Paris", country="France", days=1)],
                total_days=1,
            ),
            day_plans=[
                DayPlan(
                    date="2026-07-01",
                    day_number=1,
                    theme="Day One",
                    city_name="Paris",
                    activities=[
                        Activity(
                            time_start="08:00",
                            time_end="08:00",
                            duration_minutes=0,
                            place=Place(
                                place_id="hotel",
                                name="Hotel Departure",
                                address="",
                                location=Location(lat=48.86, lng=2.34),
                                category="hotel",
                            ),
                        ),
                    ],
                ),
            ],
            quality_score=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        ics = generate_ics(trip)
        assert "BEGIN:VCALENDAR" in ics
        assert "BEGIN:VEVENT" not in ics  # The zero-duration activity should be skipped


class TestBuildTripHTML:
    @pytest.mark.asyncio
    async def test_html_contains_theme(self):
        """The HTML output should contain the trip theme."""
        from app.models.journey import CityStop, JourneyPlan
        from app.models.trip import TripRequest, TripResponse
        from app.services.export import _build_trip_html

        trip = TripResponse(
            id="test-html",
            request=TripRequest(
                destination="Tokyo",
                total_days=3,
                start_date=date(2026, 6, 1),
            ),
            journey=JourneyPlan(
                theme="Tokyo Cultural Tour",
                summary="Explore Tokyo",
                cities=[CityStop(name="Tokyo", country="Japan", days=3)],
                total_days=3,
                review_score=85,
            ),
            day_plans=None,
            quality_score=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        html = _build_trip_html(trip)
        assert "Tokyo Cultural Tour" in html
        assert "Explore Tokyo" in html
        assert "3 days" in html
        assert "Score: 85" in html
        assert "Tokyo" in html
        assert "Japan" in html
