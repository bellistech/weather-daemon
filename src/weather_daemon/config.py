"""Configuration management for weather daemon."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class WeatherConfig:
    """Configuration for weather daemon."""

    api_key: str
    output_dir: Path
    latitude: float
    longitude: float
    location_name: str | None = None
    poll_interval: int = 3600  # 1 hour default
    timeout: int = 30
    log_level: str = "INFO"
    log_format: str = "text"  # "text" or "json"

    # API endpoints (configurable for different weather providers)
    api_base_url: str = "https://weather.googleapis.com/v1"
    current_conditions_endpoint: str = "currentConditions:lookup"
    hourly_forecast_endpoint: str = "forecast/hours:lookup"
    daily_forecast_endpoint: str = "forecast/days:lookup"

    # Health check server configuration
    health_check_enabled: bool = True
    health_check_host: str = "127.0.0.1"
    health_check_port: int = 8080

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> WeatherConfig:
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file

        Returns:
            WeatherConfig instance

        Raises:
            ValueError: If required config is missing
        """
        if env_file and env_file.exists():
            load_dotenv(env_file)

        # Required fields
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            raise ValueError(
                "WEATHER_API_KEY environment variable is required. "
                "Set it in environment or .env file."
            )

        output_dir = os.getenv("WEATHER_OUTPUT_DIR", "/opt/weather-daemon/cache")
        latitude = os.getenv("WEATHER_LATITUDE")
        longitude = os.getenv("WEATHER_LONGITUDE")

        if not latitude or not longitude:
            raise ValueError(
                "WEATHER_LATITUDE and WEATHER_LONGITUDE are required. "
                "Set them in environment or .env file."
            )

        try:
            latitude_float = float(latitude)
            longitude_float = float(longitude)
        except ValueError as e:
            raise ValueError(f"Invalid latitude/longitude values: {e}")

        # Optional fields
        location_name = os.getenv("WEATHER_LOCATION_NAME")
        poll_interval = int(os.getenv("WEATHER_POLL_INTERVAL", "3600"))
        timeout = int(os.getenv("WEATHER_TIMEOUT", "30"))
        log_level = os.getenv("WEATHER_LOG_LEVEL", "INFO")
        log_format = os.getenv("WEATHER_LOG_FORMAT", "text")  # "text" or "json"

        # API endpoint configuration (for different weather providers)
        api_base_url = os.getenv("WEATHER_API_BASE_URL", "https://weather.googleapis.com/v1")
        current_conditions_endpoint = os.getenv("WEATHER_CURRENT_ENDPOINT", "currentConditions:lookup")
        hourly_forecast_endpoint = os.getenv("WEATHER_HOURLY_ENDPOINT", "forecast/hours:lookup")
        daily_forecast_endpoint = os.getenv("WEATHER_DAILY_ENDPOINT", "forecast/days:lookup")

        # Health check configuration
        health_check_enabled = os.getenv("WEATHER_HEALTH_CHECK_ENABLED", "true").lower() in ("true", "1", "yes")
        health_check_host = os.getenv("WEATHER_HEALTH_CHECK_HOST", "127.0.0.1")
        health_check_port = int(os.getenv("WEATHER_HEALTH_CHECK_PORT", "8080"))

        return cls(
            api_key=api_key,
            output_dir=Path(output_dir),
            latitude=latitude_float,
            longitude=longitude_float,
            location_name=location_name,
            poll_interval=poll_interval,
            timeout=timeout,
            log_level=log_level,
            log_format=log_format,
            api_base_url=api_base_url,
            current_conditions_endpoint=current_conditions_endpoint,
            hourly_forecast_endpoint=hourly_forecast_endpoint,
            daily_forecast_endpoint=daily_forecast_endpoint,
            health_check_enabled=health_check_enabled,
            health_check_host=health_check_host,
            health_check_port=health_check_port,
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.api_key:
            raise ValueError("API key cannot be empty")

        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")

        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")

        if self.poll_interval < 60:
            raise ValueError("Poll interval must be at least 60 seconds")

        # Warn if poll interval is very short (potential rate limiting)
        if self.poll_interval < 300:
            logger.warning(
                f"Poll interval ({self.poll_interval}s) is less than 5 minutes. "
                "This may trigger API rate limits. Consider using 300s (5 min) or higher."
            )

        if self.timeout < 1:
            raise ValueError("Timeout must be at least 1 second")

        # Validate API base URL
        try:
            parsed = urlparse(self.api_base_url)
            if not parsed.scheme in ("http", "https"):
                raise ValueError(f"API base URL must use http or https: {self.api_base_url}")
            if not parsed.netloc:
                raise ValueError(f"API base URL must include a hostname: {self.api_base_url}")
        except Exception as e:
            raise ValueError(f"Invalid API base URL '{self.api_base_url}': {e}")

        # Validate health check port
        if not 1 <= self.health_check_port <= 65535:
            raise ValueError(f"Health check port must be between 1-65535: {self.health_check_port}")
