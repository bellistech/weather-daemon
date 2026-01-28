"""Tests for configuration."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from weather_daemon.config import WeatherConfig


def test_config_from_env_success(tmp_path, monkeypatch):
    """Test successful configuration loading from environment."""
    monkeypatch.setenv("WEATHER_API_KEY", "test-key")
    monkeypatch.setenv("WEATHER_LATITUDE", "37.4220")
    monkeypatch.setenv("WEATHER_LONGITUDE", "-122.0841")
    monkeypatch.setenv("WEATHER_LOCATION_NAME", "Test Location")
    monkeypatch.setenv("WEATHER_OUTPUT_DIR", str(tmp_path))

    config = WeatherConfig.from_env()

    assert config.api_key == "test-key"
    assert config.latitude == 37.4220
    assert config.longitude == -122.0841
    assert config.location_name == "Test Location"
    assert config.output_dir == tmp_path


def test_config_missing_api_key(monkeypatch):
    """Test configuration fails without API key."""
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="WEATHER_API_KEY"):
        WeatherConfig.from_env()


def test_config_missing_coordinates(monkeypatch):
    """Test configuration fails without coordinates."""
    monkeypatch.setenv("WEATHER_API_KEY", "test-key")
    monkeypatch.delenv("WEATHER_LATITUDE", raising=False)
    monkeypatch.delenv("WEATHER_LONGITUDE", raising=False)

    with pytest.raises(ValueError, match="WEATHER_LATITUDE"):
        WeatherConfig.from_env()


def test_config_validate_latitude():
    """Test latitude validation."""
    config = WeatherConfig(
        api_key="test-key",
        output_dir=Path("/tmp"),
        latitude=100.0,  # Invalid
        longitude=-122.0,
    )

    with pytest.raises(ValueError, match="Invalid latitude"):
        config.validate()


def test_config_validate_longitude():
    """Test longitude validation."""
    config = WeatherConfig(
        api_key="test-key",
        output_dir=Path("/tmp"),
        latitude=37.0,
        longitude=200.0,  # Invalid
    )

    with pytest.raises(ValueError, match="Invalid longitude"):
        config.validate()


def test_config_validate_poll_interval():
    """Test poll interval validation."""
    config = WeatherConfig(
        api_key="test-key",
        output_dir=Path("/tmp"),
        latitude=37.0,
        longitude=-122.0,
        poll_interval=30,  # Too short
    )

    with pytest.raises(ValueError, match="Poll interval"):
        config.validate()


def test_config_validate_api_url():
    """Test API URL validation."""
    config = WeatherConfig(
        api_key="test-key",
        output_dir=Path("/tmp"),
        latitude=37.0,
        longitude=-122.0,
        api_base_url="not-a-url",
    )

    with pytest.raises(ValueError, match="API base URL"):
        config.validate()


def test_config_defaults():
    """Test default configuration values."""
    config = WeatherConfig(
        api_key="test-key",
        output_dir=Path("/tmp"),
        latitude=37.0,
        longitude=-122.0,
    )

    assert config.poll_interval == 3600
    assert config.timeout == 30
    assert config.log_level == "INFO"
    assert config.log_format == "text"
    assert config.health_check_enabled is True
    assert config.health_check_port == 8080
