"""Weather daemon that polls Google Maps Weather API and generates static JSON."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class WeatherDaemon:
    """Daemon to fetch weather data and write static JSON files."""

    def __init__(
        self,
        api_key: str,
        output_dir: Path,
        latitude: float,
        longitude: float,
        location_name: str | None = None,
        poll_interval: int = 3600,
        timeout: int = 30,
        api_base_url: str = "https://weather.googleapis.com/v1",
        current_conditions_endpoint: str = "currentConditions:lookup",
        hourly_forecast_endpoint: str = "forecast/hours:lookup",
        daily_forecast_endpoint: str = "forecast/days:lookup",
    ) -> None:
        """Initialize the weather daemon.

        Args:
            api_key: Weather API key
            output_dir: Directory to write weather_forecast.json
            latitude: Latitude for weather location
            longitude: Longitude for weather location
            location_name: Human-readable location name
            poll_interval: Seconds between API polls (default 3600 = 1 hour)
            timeout: HTTP request timeout in seconds
            api_base_url: Base URL for weather API
            current_conditions_endpoint: Endpoint for current conditions
            hourly_forecast_endpoint: Endpoint for hourly forecast
            daily_forecast_endpoint: Endpoint for daily forecast
        """
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.latitude = latitude
        self.longitude = longitude
        self.location_name = location_name or f"{latitude},{longitude}"
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.running = False
        self.health_server = None

        # API endpoints (configurable for different providers)
        self.api_base_url = api_base_url.rstrip('/')
        self.current_conditions_endpoint = current_conditions_endpoint
        self.hourly_forecast_endpoint = hourly_forecast_endpoint
        self.daily_forecast_endpoint = daily_forecast_endpoint

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _build_current_conditions_url(self) -> str:
        """Build the current conditions API URL with location parameters."""
        return (
            f"{self.api_base_url}/{self.current_conditions_endpoint}"
            f"?key={self.api_key}"
            f"&location.latitude={self.latitude}"
            f"&location.longitude={self.longitude}"
        )

    def _build_hourly_forecast_url(self) -> str:
        """Build the hourly forecast API URL with location parameters."""
        return (
            f"{self.api_base_url}/{self.hourly_forecast_endpoint}"
            f"?key={self.api_key}"
            f"&location.latitude={self.latitude}"
            f"&location.longitude={self.longitude}"
        )

    def _build_daily_forecast_url(self) -> str:
        """Build the daily forecast API URL with location parameters."""
        return (
            f"{self.api_base_url}/{self.daily_forecast_endpoint}"
            f"?key={self.api_key}"
            f"&location.latitude={self.latitude}"
            f"&location.longitude={self.longitude}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _fetch_weather(self) -> dict[str, Any] | None:
        """Fetch weather data from Google Maps Weather API with automatic retries.

        Retries up to 3 times with exponential backoff (4s, 8s, 10s) for network errors.

        Returns:
            Combined weather data dict or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Fetching weather for {self.location_name} ({self.latitude}, {self.longitude})")

                # Fetch all three endpoints
                current_url = self._build_current_conditions_url()
                hourly_url = self._build_hourly_forecast_url()
                daily_url = self._build_daily_forecast_url()

                # Make parallel GET requests
                current_resp, hourly_resp, daily_resp = await asyncio.gather(
                    client.get(current_url),
                    client.get(hourly_url),
                    client.get(daily_url),
                    return_exceptions=True
                )

                # Collect results
                result = {}

                if isinstance(current_resp, httpx.Response) and current_resp.is_success:
                    result["current"] = current_resp.json()
                else:
                    error = current_resp if isinstance(current_resp, Exception) else current_resp.text
                    logger.warning(f"Failed to fetch current conditions: {error}")

                if isinstance(hourly_resp, httpx.Response) and hourly_resp.is_success:
                    result["hourly"] = hourly_resp.json()
                else:
                    error = hourly_resp if isinstance(hourly_resp, Exception) else hourly_resp.text
                    logger.warning(f"Failed to fetch hourly forecast: {error}")

                if isinstance(daily_resp, httpx.Response) and daily_resp.is_success:
                    result["daily"] = daily_resp.json()
                else:
                    error = daily_resp if isinstance(daily_resp, Exception) else daily_resp.text
                    logger.warning(f"Failed to fetch daily forecast: {error}")

                if not result:
                    logger.error("All weather API requests failed")
                    return None

                logger.info(f"Successfully fetched weather data")
                return result

        except Exception as e:
            logger.error(f"Unexpected error fetching weather: {e}")
            return None

    def _celsius_to_fahrenheit(self, celsius: float) -> int:
        """Convert Celsius to Fahrenheit and round to integer."""
        return round((celsius * 9/5) + 32)

    def _map_weather_icon(self, weather_type: str) -> str:
        """Map Google Weather API weather type to emoji icon.

        Args:
            weather_type: Weather type from API (e.g., "MOSTLY_CLOUDY")

        Returns:
            Emoji icon string
        """
        icon_map = {
            "CLEAR": "☀️",
            "MOSTLY_CLEAR": "🌤️",
            "PARTLY_CLOUDY": "⛅",
            "MOSTLY_CLOUDY": "☁️",
            "CLOUDY": "☁️",
            "OVERCAST": "☁️",
            "RAIN": "🌧️",
            "SHOWERS": "🌦️",
            "LIGHT_RAIN": "🌦️",
            "HEAVY_RAIN": "🌧️",
            "THUNDERSTORM": "⛈️",
            "SNOW": "🌨️",
            "LIGHT_SNOW": "🌨️",
            "HEAVY_SNOW": "❄️",
            "SLEET": "🌨️",
            "FREEZING_RAIN": "🌨️",
            "FOG": "🌫️",
            "HAZE": "🌫️",
            "WINDY": "💨",
        }
        return icon_map.get(weather_type, "🌤️")

    def _parse_weather_response(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse raw API response into standardized format.

        Args:
            raw_data: Raw response from Google API containing 'current', 'hourly', 'daily'

        Returns:
            Standardized weather data matching frontend expectations
        """
        now = datetime.now(timezone.utc)

        # Parse current conditions
        current = raw_data.get("current", {})
        temp_celsius = current.get("temperature", {}).get("degrees")
        temp_f = self._celsius_to_fahrenheit(temp_celsius) if temp_celsius is not None else None

        weather_condition = current.get("weatherCondition", {})
        weather_type = weather_condition.get("type", "")
        weather_desc = weather_condition.get("description", {}).get("text", "")

        # Get high/low from current conditions history
        history = current.get("currentConditionsHistory", {})
        high_celsius = history.get("maxTemperature", {}).get("degrees")
        low_celsius = history.get("minTemperature", {}).get("degrees")
        high_f = self._celsius_to_fahrenheit(high_celsius) if high_celsius is not None else None
        low_f = self._celsius_to_fahrenheit(low_celsius) if low_celsius is not None else None

        # Get precipitation probability
        precip = current.get("precipitation", {})
        precip_prob = precip.get("probability", {}).get("percent", 0)

        # Parse hourly forecast
        hourly_list = []
        hourly_data = raw_data.get("hourly", {}).get("forecastHours", [])
        for hour in hourly_data[:12]:  # Next 12 hours
            hour_temp_celsius = hour.get("temperature", {}).get("degrees")
            hour_temp_f = self._celsius_to_fahrenheit(hour_temp_celsius) if hour_temp_celsius is not None else None
            hour_condition = hour.get("weatherCondition", {})
            hour_type = hour_condition.get("type", "")

            # Parse time from displayDateTime
            display_time = hour.get("displayDateTime", {})
            hour_val = display_time.get("hours", 0)
            minute_val = display_time.get("minutes", 0)

            # Convert to 12-hour format
            if hour_val == 0:
                time_display = "12 AM"
            elif hour_val < 12:
                time_display = f"{hour_val} AM"
            elif hour_val == 12:
                time_display = "12 PM"
            else:
                time_display = f"{hour_val - 12} PM"

            hourly_list.append({
                "time": time_display,
                "temp": hour_temp_f,
                "icon": self._map_weather_icon(hour_type)
            })

        # Parse daily forecast
        daily_list = []
        daily_data = raw_data.get("daily", {}).get("forecastDays", [])
        for day in daily_data[:7]:  # Next 7 days
            # Get daytime forecast for condition and icon
            daytime = day.get("daytimeForecast", {})
            day_condition = daytime.get("weatherCondition", {})
            day_type = day_condition.get("type", "")
            day_desc = day_condition.get("description", {}).get("text", "")

            # Get max/min temperatures from day object
            max_temp_celsius = day.get("maxTemperature", {}).get("degrees")
            min_temp_celsius = day.get("minTemperature", {}).get("degrees")
            day_high_f = self._celsius_to_fahrenheit(max_temp_celsius) if max_temp_celsius is not None else None
            day_low_f = self._celsius_to_fahrenheit(min_temp_celsius) if min_temp_celsius is not None else None

            # Parse date from displayDate
            display_date = day.get("displayDate", {})
            year = display_date.get("year", 2026)
            month = display_date.get("month", 1)
            day_num = display_date.get("day", 1)

            try:
                day_date = datetime(year, month, day_num)
                day_name = day_date.strftime("%A")  # "Monday"
            except (ValueError, AttributeError):
                day_name = ""

            daily_list.append({
                "day": day_name,
                "high": day_high_f,
                "low": day_low_f,
                "summary": day_desc,
                "icon": self._map_weather_icon(day_type)
            })

        return {
            "location": self.location_name,
            "updated": now.isoformat(),
            "updated_display": f"Updated {now.strftime('%-I:%M %p %Z')}",
            "coordinates": {
                "lat": self.latitude,
                "lon": self.longitude,
            },
            "now": {
                "temp": temp_f,
                "summary": weather_desc,
                "icon": self._map_weather_icon(weather_type),
                "high": high_f,
                "low": low_f,
                "precip_chance": precip_prob,
            },
            "hourly": hourly_list,
            "daily": daily_list,
            "feed": {
                "path": "/weather/weather_forecast.json"
            }
        }

    def _write_json_atomic(self, filepath: Path, data: dict[str, Any]) -> None:
        """Write JSON file atomically using temp file.

        Args:
            filepath: Target file path
            data: Data to write as JSON
        """
        # Write to temp file first, then atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=filepath.parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp"
        )

        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            os.replace(temp_path, filepath)
            logger.info(f"Wrote {filepath}")
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise e

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch and write weather data."""
        try:
            raw_data = await self._fetch_weather()

            if raw_data is None:
                logger.warning("Failed to fetch weather data, skipping update")
                if self.health_server:
                    self.health_server.record_error("Failed to fetch weather data")
                return

            # Parse and format the data
            weather_data = self._parse_weather_response(raw_data)

            # Write to output file
            output_file = self.output_dir / "weather_forecast.json"
            self._write_json_atomic(output_file, weather_data)

            # Record success in health check
            if self.health_server:
                self.health_server.record_success()

        except Exception as e:
            logger.error(f"Error in poll cycle: {e}", exc_info=True)
            if self.health_server:
                self.health_server.record_error(str(e))

    async def run(self) -> None:
        """Run the daemon polling loop."""
        self.running = True

        logger.info(
            f"Starting weather daemon (polling every {self.poll_interval}s, "
            f"output: {self.output_dir}/weather_forecast.json)"
        )

        # Do initial poll immediately
        await self._poll_once()

        # Then poll on interval
        while self.running:
            try:
                await asyncio.sleep(self.poll_interval)
                if self.running:
                    await self._poll_once()
            except asyncio.CancelledError:
                logger.info("Daemon cancelled")
                break
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                # Continue running despite errors

    def stop(self) -> None:
        """Stop the daemon."""
        logger.info("Stopping weather daemon")
        self.running = False

        # Stop health check server
        if self.health_server:
            self.health_server.stop()
