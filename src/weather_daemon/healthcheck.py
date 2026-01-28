"""Health check HTTP server for monitoring."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""

    daemon_instance: Any = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/metrics":
            self._handle_metrics()
        else:
            self.send_error(404, "Not Found")

    def _handle_health(self) -> None:
        """Return basic health status."""
        try:
            daemon = self.daemon_instance
            if daemon is None:
                self.send_error(503, "Daemon not initialized")
                return

            # Check if output file exists and is recent
            output_file = daemon.output_dir / "weather_forecast.json"
            if output_file.exists():
                mtime = datetime.fromtimestamp(output_file.stat().st_mtime, tz=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - mtime).total_seconds()

                # Healthy if file was updated within 2x poll interval
                healthy = age_seconds < (daemon.poll_interval * 2)
                status_code = 200 if healthy else 503

                response = {
                    "status": "healthy" if healthy else "stale",
                    "last_update": mtime.isoformat(),
                    "age_seconds": int(age_seconds),
                    "poll_interval": daemon.poll_interval,
                }
            else:
                response = {
                    "status": "initializing",
                    "message": "No data file yet - daemon may be starting up",
                }
                status_code = 503

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            logger.error(f"Health check error: {e}")
            self.send_error(500, str(e))

    def _handle_metrics(self) -> None:
        """Return detailed metrics."""
        try:
            daemon = self.daemon_instance
            if daemon is None:
                self.send_error(503, "Daemon not initialized")
                return

            output_file = daemon.output_dir / "weather_forecast.json"

            metrics = {
                "location": daemon.location_name,
                "coordinates": {
                    "latitude": daemon.latitude,
                    "longitude": daemon.longitude,
                },
                "poll_interval_seconds": daemon.poll_interval,
                "timeout_seconds": daemon.timeout,
                "output_file": str(output_file),
                "file_exists": output_file.exists(),
            }

            if output_file.exists():
                stat = output_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                metrics["last_update"] = mtime.isoformat()
                metrics["file_size_bytes"] = stat.st_size
                metrics["age_seconds"] = int((datetime.now(timezone.utc) - mtime).total_seconds())

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(metrics, indent=2).encode())

        except Exception as e:
            logger.error(f"Metrics error: {e}")
            self.send_error(500, str(e))

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger instead of stderr."""
        logger.debug(f"Health check: {format % args}")


class HealthCheckServer:
    """HTTP server for health checks and metrics."""

    def __init__(self, daemon: Any, host: str = "127.0.0.1", port: int = 8080):
        """Initialize health check server.

        Args:
            daemon: WeatherDaemon instance to monitor
            host: Host to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 8080)
        """
        self.daemon = daemon
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: Thread | None = None

    def start(self) -> None:
        """Start the health check server in a background thread."""
        # Set the daemon instance on the handler class
        HealthCheckHandler.daemon_instance = self.daemon

        self.server = HTTPServer((self.host, self.port), HealthCheckHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"Health check server started on http://{self.host}:{self.port}")
        logger.info(f"  - Health: http://{self.host}:{self.port}/health")
        logger.info(f"  - Metrics: http://{self.host}:{self.port}/metrics")

    def stop(self) -> None:
        """Stop the health check server."""
        if self.server:
            self.server.shutdown()
            logger.info("Health check server stopped")
