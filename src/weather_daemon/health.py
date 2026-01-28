"""Simple health check HTTP server for monitoring."""
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

    output_file: Path | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    success_count: int = 0
    error_count: int = 0

    def do_GET(self) -> None:
        """Handle GET requests to /health endpoint."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/metrics":
            self._handle_metrics()
        else:
            self.send_error(404, "Not Found")

    def _handle_health(self) -> None:
        """Return basic health status."""
        status = self._get_health_status()

        if status["healthy"]:
            self.send_response(200)
        else:
            self.send_response(503)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())

    def _handle_metrics(self) -> None:
        """Return detailed metrics."""
        metrics = self._get_metrics()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(metrics, indent=2).encode())

    def _get_health_status(self) -> dict[str, Any]:
        """Get basic health status."""
        now = datetime.now(timezone.utc)

        # Check if output file exists and is recent (< 2 hours old)
        file_exists = False
        file_age_seconds = None

        if self.output_file and self.output_file.exists():
            file_exists = True
            file_mtime = datetime.fromtimestamp(
                self.output_file.stat().st_mtime,
                tz=timezone.utc
            )
            file_age_seconds = (now - file_mtime).total_seconds()

        # Healthy if file exists and is less than 2 hours old
        healthy = file_exists and file_age_seconds is not None and file_age_seconds < 7200

        status = {
            "healthy": healthy,
            "timestamp": now.isoformat(),
            "output_file_exists": file_exists,
            "output_file_age_seconds": file_age_seconds,
        }

        if self.last_success:
            status["last_success"] = self.last_success.isoformat()

        if self.last_error:
            status["last_error"] = self.last_error

        return status

    def _get_metrics(self) -> dict[str, Any]:
        """Get detailed metrics."""
        metrics = {
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.output_file:
            metrics["output_file"] = str(self.output_file)
            if self.output_file.exists():
                metrics["output_file_size"] = self.output_file.stat().st_size
                metrics["output_file_mtime"] = datetime.fromtimestamp(
                    self.output_file.stat().st_mtime,
                    tz=timezone.utc
                ).isoformat()

        return metrics

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP logging."""
        pass


class HealthCheckServer:
    """Simple HTTP server for health checks."""

    def __init__(self, port: int = 8080, output_file: Path | None = None):
        """Initialize health check server.

        Args:
            port: Port to listen on (default 8080)
            output_file: Path to output JSON file to monitor
        """
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: Thread | None = None

        # Set class variables for handler
        HealthCheckHandler.output_file = output_file
        HealthCheckHandler.last_success = None
        HealthCheckHandler.last_error = None
        HealthCheckHandler.success_count = 0
        HealthCheckHandler.error_count = 0

    def start(self) -> None:
        """Start the health check server in a background thread."""
        self.server = HTTPServer(("127.0.0.1", self.port), HealthCheckHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"Health check server listening on http://127.0.0.1:{self.port}")
        logger.info(f"  - Health: http://127.0.0.1:{self.port}/health")
        logger.info(f"  - Metrics: http://127.0.0.1:{self.port}/metrics")

    def stop(self) -> None:
        """Stop the health check server."""
        if self.server:
            self.server.shutdown()
            logger.info("Health check server stopped")

    def record_success(self) -> None:
        """Record a successful API fetch."""
        HealthCheckHandler.last_success = datetime.now(timezone.utc)
        HealthCheckHandler.success_count += 1

    def record_error(self, error: str) -> None:
        """Record an error."""
        HealthCheckHandler.last_error = error
        HealthCheckHandler.error_count += 1
