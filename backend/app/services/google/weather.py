"""Google Weather API service.

Fetches daily weather forecasts for travel destinations using the
Google Weather API (``https://weather.googleapis.com``).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from app.models.common import Location

logger = logging.getLogger(__name__)

BASE_URL = "https://weather.googleapis.com/v1"
from app.config.planning import WEATHER_API_TIMEOUT as REQUEST_TIMEOUT


class WeatherForecast:
    """Parsed daily weather forecast."""

    def __init__(
        self,
        date: date,
        temperature_high_c: float,
        temperature_low_c: float,
        condition: str,
        precipitation_chance_percent: int,
        wind_speed_kmh: float,
        humidity_percent: int,
        uv_index: int | None = None,
    ):
        self.date = date
        self.temperature_high_c = temperature_high_c
        self.temperature_low_c = temperature_low_c
        self.condition = condition
        self.precipitation_chance_percent = precipitation_chance_percent
        self.wind_speed_kmh = wind_speed_kmh
        self.humidity_percent = humidity_percent
        self.uv_index = uv_index


class GoogleWeatherService:
    """Async wrapper around the Google Weather API.

    Parameters
    ----------
    api_key:
        Google API key with Weather API enabled.
    client:
        Shared ``httpx.AsyncClient`` — the caller owns its lifecycle.
    """

    def __init__(self, api_key: str, client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.client = client

    async def get_daily_forecast(
        self,
        location: Location,
        days: int = 10,
    ) -> list[WeatherForecast]:
        """Fetch daily forecasts for a location.

        Args:
            location: Latitude/longitude to fetch weather for.
            days: Number of forecast days (max 10).

        Returns:
            List of WeatherForecast objects, one per day.
        """
        url = f"{BASE_URL}/forecast/days:lookup"
        params = {
            "key": self.api_key,
            "location.latitude": str(location.lat),
            "location.longitude": str(location.lng),
            "days": str(min(days, 10)),
        }

        try:
            resp = await self.client.get(
                url, params=params, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning(
                "Weather forecast failed for (%s, %s): %s",
                location.lat,
                location.lng,
                exc,
            )
            return []

        return self._parse_daily_forecasts(data)

    async def get_forecast_for_date(
        self,
        location: Location,
        target_date: date,
    ) -> WeatherForecast | None:
        """Get forecast for a specific date.

        Fetches the daily forecast and returns the matching day,
        or None if the date is out of range or the API fails.
        """
        forecasts = await self.get_daily_forecast(location)
        for f in forecasts:
            if f.date == target_date:
                return f
        return None

    def _parse_daily_forecasts(
        self, data: dict[str, Any]
    ) -> list[WeatherForecast]:
        """Parse the daily forecast response."""
        forecasts: list[WeatherForecast] = []

        for day_data in data.get("forecastDays", []):
            try:
                forecast = self._parse_day(day_data)
                if forecast:
                    forecasts.append(forecast)
            except Exception as exc:
                logger.warning("Failed to parse forecast day: %s", exc)

        return forecasts

    @staticmethod
    def _parse_day(day_data: dict[str, Any]) -> WeatherForecast | None:
        """Parse a single day's forecast data."""
        date_info = day_data.get("displayDate", {})
        if not date_info:
            return None

        year = date_info.get("year")
        month = date_info.get("month")
        day = date_info.get("day")
        if not all([year, month, day]):
            return None

        forecast_date = date(year, month, day)

        # Day-time forecast has the main condition
        daytime = day_data.get("daytimeForecast", {})

        # Temperature — top-level maxTemperature/minTemperature
        temp_high = day_data.get("maxTemperature", {})
        temp_low = day_data.get("minTemperature", {})
        high_c = temp_high.get("degrees", 0.0)
        low_c = temp_low.get("degrees", 0.0)

        # Condition from daytime forecast
        condition_data = daytime.get("weatherCondition", {})
        condition = condition_data.get("description", {}).get("text", "")
        if not condition:
            condition = condition_data.get("type", "UNKNOWN").replace("_", " ").title()

        # Precipitation
        precip = daytime.get("precipitation", {})
        precip_chance = precip.get("probability", {}).get("percent", 0)

        # Wind — speed.value (not maxSpeed.kilometersPerHour)
        wind = daytime.get("wind", {})
        wind_speed = wind.get("speed", {})
        wind_kmh = float(wind_speed.get("value", 0))

        # Humidity
        humidity = daytime.get("relativeHumidity", 0)

        # UV Index — from daytime forecast
        uv = daytime.get("uvIndex")

        return WeatherForecast(
            date=forecast_date,
            temperature_high_c=high_c,
            temperature_low_c=low_c,
            condition=condition,
            precipitation_chance_percent=int(precip_chance),
            wind_speed_kmh=wind_kmh,
            humidity_percent=int(humidity),
            uv_index=int(uv) if uv is not None else None,
        )


def _celsius(temp_data: dict[str, Any]) -> float:
    """Extract temperature in Celsius from API response."""
    if not temp_data:
        return 0.0
    # API returns celsius and fahrenheit
    celsius = temp_data.get("celsius")
    if celsius is not None:
        return float(celsius)
    # Fallback: convert from degrees (unit-aware)
    degrees = temp_data.get("degrees")
    if degrees is not None:
        return float(degrees)
    return 0.0


def _to_kmh(speed_data: dict[str, Any]) -> float:
    """Extract wind speed in km/h from API response."""
    if not speed_data:
        return 0.0
    kmh = speed_data.get("kilometersPerHour")
    if kmh is not None:
        return float(kmh)
    return 0.0
