.PHONY: help install dev test clean format lint setup-service logs status restart

help:
	@echo "Weather Daemon - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        Install package and dependencies"
	@echo "  make dev            Install in development mode with dev dependencies"
	@echo "  make test           Run tests"
	@echo "  make format         Format code with black"
	@echo "  make lint           Run linters"
	@echo "  make clean          Remove build artifacts and cache files"
	@echo ""
	@echo "Deployment (requires sudo):"
	@echo "  make setup-service  Run automated setup script"
	@echo "  make status         Show systemd service status"
	@echo "  make logs           Follow service logs"
	@echo "  make restart        Restart the service"
	@echo ""

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest

format:
	black src/ tests/

lint:
	ruff check src/
	mypy src/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf test_output/
	rm -f weather_forecast.json

setup-service:
	@echo "Running setup script (requires root)..."
	sudo ./setup.sh

status:
	sudo systemctl status weather-daemon

logs:
	sudo journalctl -u weather-daemon -f

restart:
	sudo systemctl restart weather-daemon
	@echo "Waiting for service to start..."
	@sleep 2
	@sudo systemctl status weather-daemon
