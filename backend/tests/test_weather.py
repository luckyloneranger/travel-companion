"""Unit tests for GoogleWeatherService and business status filtering."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.common import Location
from app.models.internal import PlaceCandidate
from app.services.google.weather import GoogleWeatherService, WeatherForecast, _celsius, _to_kmh


# ═══════════════════════════════════════════════════════════════════════════════
# Weather service tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCelsiusParser:
    def test_celsius_field(self):
        assert _celsius({"celsius": 25.5}) == 25.5

    def test_degrees_fallback(self):
        assert _celsius({"degrees": 30.0}) == 30.0

    def test_empty(self):
        assert _celsius({}) == 0.0

    def test_none(self):
        assert _celsius(None) == 0.0


class TestToKmh:
    def test_kmh_field(self):
        assert _to_kmh({"kilometersPerHour": 15.5}) == 15.5

    def test_empty(self):
        assert _to_kmh({}) == 0.0


class TestWeatherForecast:
    def test_attributes(self):
        f = WeatherForecast(
            date=date(2026, 7, 1),
            temperature_high_c=32.0,
            temperature_low_c=22.0,
            condition="Partly Cloudy",
            precipitation_chance_percent=20,
            wind_speed_kmh=10.0,
            humidity_percent=65,
            uv_index=7,
        )
        assert f.temperature_high_c == 32.0
        assert f.condition == "Partly Cloudy"
        assert f.uv_index == 7


class TestGoogleWeatherService:
    @pytest.mark.asyncio
    async def test_parse_daily_forecasts(self):
        """Parse a mock daily forecast response matching real API structure."""
        service = GoogleWeatherService(api_key="fake", client=MagicMock())

        mock_response = {
            "forecastDays": [
                {
                    "displayDate": {"year": 2026, "month": 7, "day": 1},
                    "maxTemperature": {"degrees": 30.0, "unit": "CELSIUS"},
                    "minTemperature": {"degrees": 20.0, "unit": "CELSIUS"},
                    "daytimeForecast": {
                        "weatherCondition": {
                            "description": {"text": "Sunny"},
                            "type": "CLEAR",
                        },
                        "precipitation": {
                            "probability": {"percent": 10},
                        },
                        "wind": {
                            "speed": {"value": 12, "unit": "KILOMETERS_PER_HOUR"},
                        },
                        "relativeHumidity": 55,
                        "uvIndex": 6,
                    },
                    "nighttimeForecast": {},
                }
            ]
        }

        forecasts = service._parse_daily_forecasts(mock_response)
        assert len(forecasts) == 1
        f = forecasts[0]
        assert f.date == date(2026, 7, 1)
        assert f.temperature_high_c == 30.0
        assert f.temperature_low_c == 20.0
        assert f.condition == "Sunny"
        assert f.precipitation_chance_percent == 10
        assert f.wind_speed_kmh == 12.0
        assert f.humidity_percent == 55
        assert f.uv_index == 6

    @pytest.mark.asyncio
    async def test_get_forecast_for_date_found(self):
        """get_forecast_for_date returns matching forecast."""
        service = GoogleWeatherService(api_key="fake", client=MagicMock())

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "forecastDays": [
                {
                    "displayDate": {"year": 2026, "month": 7, "day": 1},
                    "maxTemperature": {"degrees": 28.0, "unit": "CELSIUS"},
                    "minTemperature": {"degrees": 18.0, "unit": "CELSIUS"},
                    "daytimeForecast": {
                        "weatherCondition": {"type": "RAIN"},
                        "precipitation": {"probability": {"percent": 80}},
                        "wind": {"speed": {"value": 20, "unit": "KILOMETERS_PER_HOUR"}},
                        "relativeHumidity": 85,
                        "uvIndex": 3,
                    },
                    "nighttimeForecast": {},
                },
                {
                    "displayDate": {"year": 2026, "month": 7, "day": 2},
                    "maxTemperature": {"degrees": 32.0, "unit": "CELSIUS"},
                    "minTemperature": {"degrees": 22.0, "unit": "CELSIUS"},
                    "daytimeForecast": {
                        "weatherCondition": {"type": "CLEAR"},
                        "precipitation": {"probability": {"percent": 5}},
                        "wind": {"speed": {"value": 8, "unit": "KILOMETERS_PER_HOUR"}},
                        "relativeHumidity": 40,
                        "uvIndex": 9,
                    },
                    "nighttimeForecast": {},
                },
            ]
        }

        service.client = MagicMock()
        service.client.get = AsyncMock(return_value=mock_resp)

        result = await service.get_forecast_for_date(
            Location(lat=35.0, lng=135.0),
            date(2026, 7, 2),
        )
        assert result is not None
        assert result.temperature_high_c == 32.0
        assert result.uv_index == 9

    @pytest.mark.asyncio
    async def test_get_forecast_for_date_not_found(self):
        """get_forecast_for_date returns None for out-of-range date."""
        service = GoogleWeatherService(api_key="fake", client=MagicMock())

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"forecastDays": []}

        service.client = MagicMock()
        service.client.get = AsyncMock(return_value=mock_resp)

        result = await service.get_forecast_for_date(
            Location(lat=35.0, lng=135.0),
            date(2026, 12, 25),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_api_failure_returns_empty(self):
        """API failure returns empty list gracefully."""
        import httpx

        service = GoogleWeatherService(api_key="fake", client=MagicMock())
        service.client = MagicMock()
        service.client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))

        forecasts = await service.get_daily_forecast(Location(lat=0, lng=0))
        assert forecasts == []


# ═══════════════════════════════════════════════════════════════════════════════
# Business status filtering tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestBusinessStatusFiltering:
    """Test that closed places are filtered out."""

    def _make_place(self, name: str, rating: float = 4.5, status: str | None = None) -> PlaceCandidate:
        return PlaceCandidate(
            place_id=f"place_{name}",
            name=name,
            address=f"{name} address",
            location=Location(lat=48.0, lng=2.0),
            types=["tourist_attraction"],
            rating=rating,
            user_ratings_total=100,
            business_status=status,
        )

    def test_operational_places_kept(self):
        from app.services.google.places import GooglePlacesService
        candidates = [
            self._make_place("Open", status="OPERATIONAL"),
            self._make_place("NoStatus", status=None),
        ]
        result = GooglePlacesService._filter_and_rank_by_quality(candidates)
        assert len(result) == 2

    def test_temporarily_closed_filtered(self):
        from app.services.google.places import GooglePlacesService
        candidates = [
            self._make_place("Open", status="OPERATIONAL"),
            self._make_place("TempClosed", status="CLOSED_TEMPORARILY"),
        ]
        result = GooglePlacesService._filter_and_rank_by_quality(candidates)
        assert len(result) == 1
        assert result[0].name == "Open"

    def test_permanently_closed_filtered(self):
        from app.services.google.places import GooglePlacesService
        candidates = [
            self._make_place("Open", status="OPERATIONAL"),
            self._make_place("PermClosed", status="CLOSED_PERMANENTLY"),
        ]
        result = GooglePlacesService._filter_and_rank_by_quality(candidates)
        assert len(result) == 1
        assert result[0].name == "Open"


# ═══════════════════════════════════════════════════════════════════════════════
# Weather warnings tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeatherWarnings:
    """Test the weather warning logic in the orchestrator."""

    def _make_activity(self, name: str, category: str) -> "Activity":
        from app.models.day_plan import Activity, Place
        return Activity(
            time_start="10:00",
            time_end="11:00",
            duration_minutes=60,
            place=Place(
                place_id=f"place_{name}",
                name=name,
                address="test",
                location=Location(lat=48.0, lng=2.0),
                category=category,
            ),
        )

    def test_no_warnings_in_good_weather(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        forecast = WeatherForecast(
            date=date(2026, 7, 1),
            temperature_high_c=25.0,
            temperature_low_c=18.0,
            condition="Sunny",
            precipitation_chance_percent=10,
            wind_speed_kmh=8.0,
            humidity_percent=50,
            uv_index=5,
        )
        activities = [self._make_activity("City Park", "park")]
        result = DayPlanOrchestrator._add_weather_warnings(activities, forecast)
        assert result[0].weather_warning is None

    def test_rain_warning_for_outdoor(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        forecast = WeatherForecast(
            date=date(2026, 7, 1),
            temperature_high_c=22.0,
            temperature_low_c=15.0,
            condition="Rain",
            precipitation_chance_percent=80,
            wind_speed_kmh=15.0,
            humidity_percent=90,
            uv_index=2,
        )
        activities = [self._make_activity("City Park", "park")]
        result = DayPlanOrchestrator._add_weather_warnings(activities, forecast)
        assert result[0].weather_warning is not None
        assert "Rain likely" in result[0].weather_warning

    def test_no_warning_for_indoor(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        forecast = WeatherForecast(
            date=date(2026, 7, 1),
            temperature_high_c=22.0,
            temperature_low_c=15.0,
            condition="Rain",
            precipitation_chance_percent=90,
            wind_speed_kmh=50.0,
            humidity_percent=90,
            uv_index=2,
        )
        activities = [self._make_activity("Louvre Museum", "museum")]
        result = DayPlanOrchestrator._add_weather_warnings(activities, forecast)
        assert result[0].weather_warning is None

    def test_heat_warning(self):
        from app.orchestrators.day_plan import DayPlanOrchestrator
        forecast = WeatherForecast(
            date=date(2026, 7, 1),
            temperature_high_c=40.0,
            temperature_low_c=28.0,
            condition="Sunny",
            precipitation_chance_percent=0,
            wind_speed_kmh=5.0,
            humidity_percent=30,
            uv_index=10,
        )
        activities = [self._make_activity("Beach Walk", "beach")]
        result = DayPlanOrchestrator._add_weather_warnings(activities, forecast)
        assert result[0].weather_warning is not None
        assert "Extreme heat" in result[0].weather_warning
        assert "UV" in result[0].weather_warning
