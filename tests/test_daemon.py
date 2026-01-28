"""Tests for weather daemon."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from weather_daemon.daemon import WeatherDaemon


@pytest.fixture
def mock_api_responses():
    """Mock API responses from Google Weather API."""
    current_conditions = {
        "currentTime": "2026-01-27T20:00:00Z",
        "weatherCondition": {
            "type": "CLOUDY",
            "description": {"text": "Cloudy"},
        },
        "temperature": {"degrees": 16.9, "unit": "CELSIUS"},
        "feelsLikeTemperature": {"degrees": 16.9, "unit": "CELSIUS"},
        "relativeHumidity": 48,
        "precipitation": {
            "probability": {"percent": 10, "type": "RAIN"}
        },
        "currentConditionsHistory": {
            "maxTemperature": {"degrees": 15.9, "unit": "CELSIUS"},
            "minTemperature": {"degrees": 4.8, "unit": "CELSIUS"},
        },
    }

    hourly_forecast = {
        "forecastHours": [
            {
                "displayDateTime": {"hours": 14, "minutes": 0},
                "weatherCondition": {"type": "CLOUDY"},
                "temperature": {"degrees": 7.2, "unit": "CELSIUS"},
            },
            {
                "displayDateTime": {"hours": 15, "minutes": 0},
                "weatherCondition": {"type": "PARTLY_CLOUDY"},
                "temperature": {"degrees": 8.0, "unit": "CELSIUS"},
            },
        ]
    }

    daily_forecast = {
        "forecastDays": [
            {
                "displayDate": {"year": 2026, "month": 1, "day": 28},
                "daytimeForecast": {
                    "weatherCondition": {
                        "type": "SUNNY",
                        "description": {"text": "Sunny"},
                    }
                },
                "maxTemperature": {"degrees": 20.0, "unit": "CELSIUS"},
                "minTemperature": {"degrees": 10.0, "unit": "CELSIUS"},
            },
            {
                "displayDate": {"year": 2026, "month": 1, "day": 29},
                "daytimeForecast": {
                    "weatherCondition": {
                        "type": "RAIN",
                        "description": {"text": "Rain"},
                    }
                },
                "maxTemperature": {"degrees": 15.0, "unit": "CELSIUS"},
                "minTemperature": {"degrees": 8.0, "unit": "CELSIUS"},
            },
        ]
    }

    return {
        "current": current_conditions,
        "hourly": hourly_forecast,
        "daily": daily_forecast,
    }


@pytest.fixture
def daemon(tmp_path):
    """Create a WeatherDaemon instance for testing."""
    return WeatherDaemon(
        api_key="test-key",
        output_dir=tmp_path,
        latitude=37.4220,
        longitude=-122.0841,
        location_name="Test Location",
        poll_interval=3600,
        timeout=30,
        health_check_port=8081,
    )


@pytest.mark.asyncio
async def test_fetch_weather_success(daemon, mock_api_responses):
    """Test successful weather data fetch."""
    mock_current_resp = Mock(spec=httpx.Response)
    mock_current_resp.is_success = True
    mock_current_resp.json.return_value = mock_api_responses["current"]

    mock_hourly_resp = Mock(spec=httpx.Response)
    mock_hourly_resp.is_success = True
    mock_hourly_resp.json.return_value = mock_api_responses["hourly"]

    mock_daily_resp = Mock(spec=httpx.Response)
    mock_daily_resp.is_success = True
    mock_daily_resp.json.return_value = mock_api_responses["daily"]

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=[
        mock_current_resp,
        mock_hourly_resp,
        mock_daily_resp,
    ])

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await daemon._fetch_weather()

    assert result is not None
    assert "current" in result
    assert "hourly" in result
    assert "daily" in result


def test_celsius_to_fahrenheit(daemon):
    """Test temperature conversion."""
    assert daemon._celsius_to_fahrenheit(0) == 32
    assert daemon._celsius_to_fahrenheit(100) == 212
    assert daemon._celsius_to_fahrenheit(-40) == -40
    assert daemon._celsius_to_fahrenheit(20) == 68


def test_map_weather_icon(daemon):
    """Test weather icon mapping."""
    assert daemon._map_weather_icon("CLEAR") == "☀️"
    assert daemon._map_weather_icon("CLOUDY") == "☁️"
    assert daemon._map_weather_icon("RAIN") == "🌧️"
    assert daemon._map_weather_icon("SNOW") == "🌨️"
    assert daemon._map_weather_icon("UNKNOWN") == "🌤️"


def test_parse_weather_response(daemon, mock_api_responses):
    """Test parsing of weather API response."""
    result = daemon._parse_weather_response(mock_api_responses)

    assert "location" in result
    assert "updated" in result
    assert "coordinates" in result
    assert "now" in result
    assert "hourly" in result
    assert "daily" in result

    assert result["now"]["temp"] == 62
    assert result["now"]["summary"] == "Cloudy"
    assert result["now"]["icon"] == "☁️"
    assert result["now"]["precip_chance"] == 10

    assert len(result["hourly"]) == 2
    assert result["hourly"][0]["time"] == "2 PM"
    assert result["hourly"][0]["temp"] == 45

    assert len(result["daily"]) == 2
    assert result["daily"][0]["day"] == "Wednesday"
    assert result["daily"][0]["high"] == 68
    assert result["daily"][0]["low"] == 50


def test_write_json_atomic(daemon, tmp_path):
    """Test atomic file writing."""
    test_data = {"test": "data", "number": 123}
    output_file = tmp_path / "test.json"

    daemon._write_json_atomic(output_file, test_data)

    assert output_file.exists()
    with open(output_file) as f:
        loaded_data = json.load(f)

    assert loaded_data == test_data
