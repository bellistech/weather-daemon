# weather-daemon

A Python daemon that polls the Google Maps Weather API and generates static JSON files for web consumption.

## Overview

The weather-daemon is designed similar to [rss-daemon](https://github.com/bellistech/rss-daemon), creating static JSON files that can be served by nginx and consumed by frontend JavaScript.

## Features

- **Weather Data**: Polls Google Maps Weather API hourly (configurable) for current conditions, hourly forecast, and daily forecast
- **Reliability**: Automatic retry with exponential backoff for transient failures
- **Atomic Writes**: Prevents file corruption during updates
- **Health Monitoring**: Built-in HTTP health check endpoint for service monitoring
- **Flexible Logging**: Structured JSON logging for production or human-readable text for development
- **Security**: Systemd service with extensive security hardening (read-only filesystem, capability restrictions, etc.)
- **Configuration**: Environment-based configuration with validation
- **Testing**: Comprehensive unit test suite with mocked API responses

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install
python -m pip install -U pip
pip install -e ".[dev]"

# Create config
cp .env.example .env
# Edit .env with your API key and location

# Test configuration
weather-daemon test --config .env

# Run daemon
weather-daemon run --config .env
```

### Using Make (Optional)

Common tasks are available via Makefile:

```bash
make help          # Show all available commands
make dev           # Install in development mode
make test          # Run tests
make format        # Format code
make clean         # Remove build artifacts
```

## Configuration

Configuration is managed via environment variables, typically in a `.env` file:

```bash
# Required
WEATHER_API_KEY=your_google_maps_api_key
WEATHER_LATITUDE=40.7128
WEATHER_LONGITUDE=-74.0060

# Optional
WEATHER_LOCATION_NAME=New York, NY
WEATHER_OUTPUT_DIR=/opt/weather-daemon/cache  # Symlink to web root as needed
WEATHER_POLL_INTERVAL=3600  # seconds (default: 1 hour, min 60s, <300s triggers warning)
WEATHER_TIMEOUT=30          # HTTP timeout in seconds
WEATHER_LOG_LEVEL=INFO      # DEBUG, INFO, WARNING, ERROR
WEATHER_LOG_FORMAT=text     # text or json (use json for production log aggregation)

# Health Check Server (optional)
WEATHER_HEALTH_CHECK_ENABLED=true      # Enable HTTP health endpoint
WEATHER_HEALTH_CHECK_HOST=127.0.0.1    # Bind to localhost only
WEATHER_HEALTH_CHECK_PORT=8080         # Health check port

# API Endpoints (optional - defaults to Google Weather API)
# Customize these to use alternative weather providers
WEATHER_API_BASE_URL=https://weather.googleapis.com/v1
WEATHER_CURRENT_ENDPOINT=currentConditions:lookup
WEATHER_HOURLY_ENDPOINT=forecast/hours:lookup
WEATHER_DAILY_ENDPOINT=forecast/days:lookup
```

### Getting an API Key

1. Visit [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the "Weather API" for your project
4. Create credentials (API key)
5. Set up billing (Weather API requires billing enabled)
6. Add the API key to your `.env` file

Reference: https://developers.google.com/maps/documentation/weather

### Using Alternative Weather APIs

The daemon supports configurable API endpoints, making it easy to swap weather providers. The default configuration uses Google Weather API, but you can customize the endpoints for services like OpenWeatherMap, WeatherAPI, or any other provider.

To use a different provider:
1. Update `WEATHER_API_BASE_URL` to the provider's base URL
2. Configure the endpoint paths for current, hourly, and daily forecasts
3. Modify `daemon.py`'s `_fetch_weather()` method if the request/response format differs

This flexibility allows you to:
- Switch providers without changing core code
- Test different APIs during development
- Use mock/stub endpoints for testing

## Output Format

The daemon generates `/weather/weather_forecast.json` with structure matching the frontend JavaScript expectations:

```json
{
  "location": "New York, NY",
  "updated": "2026-01-27T10:30:00Z",
  "updated_display": "Updated 10:30 AM EST",
  "coordinates": {
    "lat": 40.7128,
    "lon": -74.0060
  },
  "now": {
    "temp": 45,
    "summary": "Partly Cloudy",
    "icon": "⛅",
    "high": 52,
    "low": 38,
    "precip_chance": 20
  },
  "hourly": [
    {
      "time": "11 AM",
      "temp": 46,
      "icon": "⛅"
    }
  ],
  "daily": [
    {
      "day": "Monday",
      "high": 52,
      "low": 38,
      "summary": "Partly Cloudy",
      "icon": "⛅"
    }
  ],
  "feed": {
    "path": "/weather/weather_forecast.json"
  }
}
```

## Frontend Integration

The included `weather.js` frontend script (in www-main/) automatically:
- Fetches `/weather/weather_forecast.json` every 30 seconds
- Displays current conditions, hourly forecast, and 6-day forecast
- Updates when browser tab becomes visible
- Gracefully handles missing data

Include in your HTML:
```html
<div data-weather>
  <div data-weather-location></div>
  <div data-weather-now-temp></div>
  <!-- See weather.js for full markup -->
</div>
<script src="/js/weather.js"></script>
```

## Health Check & Monitoring

The daemon includes a built-in HTTP health check server for service monitoring:

### Health Check Endpoint

```bash
curl http://localhost:8080/health
```

Response when healthy:
```json
{
  "status": "healthy",
  "last_update": "2026-01-27T20:30:00Z",
  "age_seconds": 45,
  "poll_interval": 3600
}
```

Response when stale (file older than 2x poll interval):
```json
{
  "status": "stale",
  "last_update": "2026-01-27T10:00:00Z",
  "age_seconds": 10845,
  "poll_interval": 3600
}
```

### Metrics Endpoint

```bash
curl http://localhost:8080/metrics
```

Returns detailed daemon metrics:
```json
{
  "location": "Austin, TX",
  "coordinates": {"latitude": 30.2672, "longitude": -97.7431},
  "poll_interval_seconds": 3600,
  "timeout_seconds": 30,
  "output_file": "/opt/weather-daemon/cache/weather_forecast.json",
  "file_exists": true,
  "last_update": "2026-01-27T20:30:00Z",
  "file_size_bytes": 2048,
  "age_seconds": 45
}
```

### Monitoring Integration

**Uptime Kuma / Prometheus**
```yaml
# Add to your monitoring config
- job_name: 'weather-daemon'
  static_configs:
    - targets: ['localhost:8080']
  metrics_path: '/health'
```

**Nagios / Icinga**
```bash
# Check health endpoint returns 200 OK
check_http -H localhost -p 8080 -u /health
```

**systemd monitoring** (built-in)
```bash
# Check service status
systemctl status weather-daemon

# View logs
journalctl -u weather-daemon -f
```

## Deployment

### Automated Setup (Recommended)

Use the included setup script for quick installation:

```bash
# Clone or copy repository to server
cd weather-daemon

# Run setup script (requires root)
sudo ./setup.sh
```

The setup script will:
- Install system dependencies (python3, pip, gcc)
- Create dedicated service user
- Install daemon to `/opt/weather-daemon`
- Create configuration directory at `/etc/weather-daemon`
- Create cache directory at `/opt/weather-daemon/cache`
- Install and enable systemd service

After running setup.sh:
1. Edit `/etc/weather-daemon/config.env` with your API key
2. Create symlink to web root: `sudo ln -s /opt/weather-daemon/cache /var/www/yoursite.com/html/weather`
3. Restart service: `sudo systemctl restart weather-daemon`
4. Check status: `sudo systemctl status weather-daemon`

### Manual Setup

If you prefer manual installation:

#### 1. Copy files to server
```bash
sudo mkdir -p /opt/weather-daemon
sudo cp -r . /opt/weather-daemon/
```

#### 2. Create service user
```bash
sudo useradd -r -s /bin/false weather-daemon
```

#### 3. Create cache directory
```bash
sudo mkdir -p /opt/weather-daemon/cache
sudo chown weather-daemon:weather-daemon /opt/weather-daemon/cache
```

#### 4. Setup configuration
```bash
sudo mkdir -p /etc/weather-daemon
sudo cp .env.example /etc/weather-daemon/config.env
# Edit /etc/weather-daemon/config.env with your settings
sudo chown -R weather-daemon:weather-daemon /etc/weather-daemon
```

#### 5. Install Python dependencies
```bash
cd /opt/weather-daemon
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -e .
sudo chown -R weather-daemon:weather-daemon /opt/weather-daemon
```

#### 6. Install systemd service
```bash
sudo cp deploy/systemd/weather-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable weather-daemon
sudo systemctl start weather-daemon
```

#### 7. Check status
```bash
sudo systemctl status weather-daemon
sudo journalctl -u weather-daemon -f
```

### Nginx Configuration

1. Create symlink to web root:
```bash
sudo ln -s /opt/weather-daemon/cache /var/www/yoursite.com/html/weather
```

2. Include the nginx configuration in your server block:
```bash
sudo cp deploy/nginx/weather-locations.conf /etc/nginx/sites-available/
```

3. In your main nginx config:
```nginx
server {
    # ... your existing config ...

    include /etc/nginx/sites-available/weather-locations.conf;
}
```

4. Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Security

The systemd service includes hardening features:
- Dedicated user with no shell
- Read-only root filesystem
- Network isolation (outbound only)
- Syscall filtering
- Memory protection
- Capability stripping

Output directory is the only writable location.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Format code
black src/
```

## Project Structure

```
weather-daemon/
├── src/weather_daemon/
│   ├── __init__.py
│   ├── cli.py           # CLI entrypoint
│   ├── config.py        # Configuration management
│   └── daemon.py        # Main polling daemon
├── deploy/
│   ├── systemd/
│   │   └── weather-daemon.service
│   └── nginx/
│       └── weather-locations.conf
├── www-main/            # Frontend reference (temp dev location)
│   └── html/js/weather.js
├── pyproject.toml
├── .env.example
└── README.md
```

## Troubleshooting

### API Key Not Working

Ensure:
1. Weather API is enabled in Google Cloud Console
2. Billing is set up (required for Weather API)
3. API key has no restrictions or includes Weather API
4. You're within API quotas

### Permission Errors

Check:
```bash
sudo ls -la /opt/weather-daemon/cache/
sudo journalctl -u weather-daemon -n 50
```

Ensure cache directory is writable by daemon user:
```bash
sudo chown weather-daemon:weather-daemon /opt/weather-daemon/cache
```

### Test API Connection

```bash
weather-daemon test --config /path/to/.env
```

## Related Projects

- [rss-daemon](https://github.com/bellistech/rss-daemon) - RSS aggregation daemon (similar architecture)
- [www](https://github.com/bellistech/www) - Main website repository

## Package Details

- Package: `weather_daemon`
- Entrypoint: `weather-daemon` → `weather_daemon.cli:main`
