"""Tests for health check server."""
import json
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from http.client import HTTPConnection

from weather_daemon.healthcheck import HealthCheckServer
from weather_daemon.daemon import WeatherDaemon


@pytest.fixture
def daemon(tmp_path):
    """Create a test daemon instance."""
    return WeatherDaemon(
        api_key="test_key",
        output_dir=tmp_path,
        latitude=30.0,
        longitude=-97.0,
        location_name="Test City",
        poll_interval=60,
        timeout=10
    )


@pytest.fixture
def health_server(daemon):
    """Create and start a health check server."""
    server = HealthCheckServer(daemon, host="127.0.0.1", port=18080)
    server.start()
    time.sleep(0.1)  # Give server time to start
    yield server
    server.stop()


def test_health_endpoint_no_file(health_server):
    """Test health endpoint when no data file exists yet."""
    conn = HTTPConnection("127.0.0.1", 18080)
    conn.request("GET", "/health")
    response = conn.getresponse()

    assert response.status == 503  # Service unavailable
    data = json.loads(response.read().decode())
    assert data["status"] == "initializing"
    conn.close()


def test_health_endpoint_with_file(health_server, daemon, tmp_path):
    """Test health endpoint when data file exists."""
    # Create a recent weather file
    weather_file = tmp_path / "weather_forecast.json"
    weather_file.write_text(json.dumps({"test": "data"}))

    conn = HTTPConnection("127.0.0.1", 18080)
    conn.request("GET", "/health")
    response = conn.getresponse()

    assert response.status == 200
    data = json.loads(response.read().decode())
    assert data["status"] == "healthy"
    assert "last_update" in data
    assert "age_seconds" in data
    conn.close()


def test_health_endpoint_stale_file(health_server, daemon, tmp_path):
    """Test health endpoint when data file is stale."""
    # Create an old weather file
    weather_file = tmp_path / "weather_forecast.json"
    weather_file.write_text(json.dumps({"test": "data"}))

    # Make the file appear old by setting mtime
    old_time = time.time() - (daemon.poll_interval * 3)
    Path(weather_file).touch()
    import os
    os.utime(weather_file, (old_time, old_time))

    conn = HTTPConnection("127.0.0.1", 18080)
    conn.request("GET", "/health")
    response = conn.getresponse()

    assert response.status == 503
    data = json.loads(response.read().decode())
    assert data["status"] == "stale"
    conn.close()


def test_metrics_endpoint(health_server, daemon):
    """Test metrics endpoint."""
    conn = HTTPConnection("127.0.0.1", 18080)
    conn.request("GET", "/metrics")
    response = conn.getresponse()

    assert response.status == 200
    data = json.loads(response.read().decode())

    assert data["location"] == "Test City"
    assert data["coordinates"]["latitude"] == 30.0
    assert data["coordinates"]["longitude"] == -97.0
    assert data["poll_interval_seconds"] == 60
    assert "file_exists" in data
    conn.close()


def test_invalid_endpoint(health_server):
    """Test invalid endpoint returns 404."""
    conn = HTTPConnection("127.0.0.1", 18080)
    conn.request("GET", "/invalid")
    response = conn.getresponse()

    assert response.status == 404
    conn.close()


def test_server_start_stop(daemon):
    """Test server start and stop."""
    server = HealthCheckServer(daemon, host="127.0.0.1", port=18081)

    # Start server
    server.start()
    time.sleep(0.1)
    assert server.thread is not None
    assert server.thread.is_alive()

    # Stop server
    server.stop()
    time.sleep(0.1)
    assert not server.thread.is_alive()
