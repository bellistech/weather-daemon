# Weather Daemon Installation Guide

Complete guide for installing and deploying the weather-daemon service.

## Table of Contents

- [Quick Start (Development)](#quick-start-development)
- [Production Deployment](#production-deployment)
- [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Quick Start (Development)

For local development and testing:

```bash
# Clone repository
git clone https://github.com/yourusername/weather-daemon.git
cd weather-daemon

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
make dev
# Or: pip install -e ".[dev]"

# Create configuration
cp .env.example .env
nano .env  # Add your API key and coordinates

# Test configuration
weather-daemon test --config .env

# Run daemon (polls hourly)
weather-daemon run --config .env
```

Output will be written to `./test_output/weather_forecast.json` by default.

## Production Deployment

### Automated Setup (Recommended)

The automated setup script handles all installation steps:

```bash
# On your server
cd /tmp
git clone https://github.com/yourusername/weather-daemon.git
cd weather-daemon

# Run setup script
sudo ./setup.sh
```

The script will:
1. ✓ Check system requirements (Python 3.9+, systemd)
2. ✓ Install system dependencies (python3-pip, gcc, etc.)
3. ✓ Create dedicated `weather-daemon` service user
4. ✓ Install daemon to `/opt/weather-daemon`
5. ✓ Create virtual environment and install dependencies
6. ✓ Setup configuration directory at `/etc/weather-daemon`
7. ✓ Create output directory at `/var/www/html/weather`
8. ✓ Install and enable systemd service

### Post-Installation Steps

After running `setup.sh`:

1. **Configure API key and location:**
```bash
sudo nano /etc/weather-daemon/config.env
```

Add your Google Maps API key and location:
```bash
WEATHER_API_KEY=your_actual_api_key_here
WEATHER_LATITUDE=40.7128
WEATHER_LONGITUDE=-74.0060
WEATHER_LOCATION_NAME=New York, NY
```

2. **Start the service:**
```bash
sudo systemctl restart weather-daemon
```

3. **Verify it's running:**
```bash
sudo systemctl status weather-daemon
sudo journalctl -u weather-daemon -f
```

4. **Check output file:**
```bash
cat /var/www/html/weather/weather_forecast.json
```

### Nginx Configuration

To serve the weather data via HTTP:

```bash
# Copy nginx configuration
sudo cp /opt/weather-daemon/deploy/nginx/weather-locations.conf /etc/nginx/sites-available/

# Include in your main nginx config
# Add this line to your server block:
#   include /etc/nginx/sites-available/weather-locations.conf;

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

Now weather data will be available at: `http://yourserver.com/weather/weather_forecast.json`

## Manual Installation

If you prefer step-by-step manual installation:

### 1. Prerequisites

- Linux server with systemd
- Python 3.9 or higher
- Root/sudo access
- Python development headers (`python3-dev`)

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev gcc
```

**RHEL/CentOS/Fedora:**
```bash
sudo yum install -y python3 python3-pip python3-devel gcc
# Or on newer systems:
sudo dnf install -y python3 python3-pip python3-devel gcc
```

### 3. Create Service User

```bash
sudo useradd -r -s /bin/false weather-daemon
```

- `-r`: System account
- `-s /bin/false`: No shell access (security)

### 4. Install Daemon

```bash
# Create installation directory
sudo mkdir -p /opt/weather-daemon

# Copy files
sudo cp -r /path/to/weather-daemon/* /opt/weather-daemon/

# Create virtual environment
cd /opt/weather-daemon
sudo python3 -m venv venv

# Install package
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -e .

# Set ownership
sudo chown -R weather-daemon:weather-daemon /opt/weather-daemon
```

### 5. Setup Configuration

```bash
# Create config directory
sudo mkdir -p /etc/weather-daemon

# Copy example config
sudo cp /opt/weather-daemon/.env.example /etc/weather-daemon/config.env

# Edit configuration
sudo nano /etc/weather-daemon/config.env

# Secure permissions
sudo chown -R weather-daemon:weather-daemon /etc/weather-daemon
sudo chmod 600 /etc/weather-daemon/config.env
```

### 6. Create Output Directory

```bash
sudo mkdir -p /var/www/html/weather
sudo chown weather-daemon:weather-daemon /var/www/html/weather
sudo chmod 755 /var/www/html/weather
```

### 7. Install Systemd Service

```bash
sudo cp /opt/weather-daemon/deploy/systemd/weather-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable weather-daemon
sudo systemctl start weather-daemon
```

### 8. Verify Installation

```bash
# Check service status
sudo systemctl status weather-daemon

# View logs
sudo journalctl -u weather-daemon -n 50

# Check output file
ls -la /var/www/html/weather/
cat /var/www/html/weather/weather_forecast.json
```

## Configuration

### Required Settings

```bash
# Google Maps API key (required)
WEATHER_API_KEY=your_api_key_here

# Location coordinates (required)
WEATHER_LATITUDE=40.7128
WEATHER_LONGITUDE=-74.0060
```

### Optional Settings

```bash
# Human-readable location name
WEATHER_LOCATION_NAME=New York, NY

# Output directory (default: /var/www/html/weather)
WEATHER_OUTPUT_DIR=/var/www/html/weather

# Poll interval in seconds (default: 3600 = 1 hour)
WEATHER_POLL_INTERVAL=3600

# HTTP timeout (default: 30 seconds)
WEATHER_TIMEOUT=30

# Log level (default: INFO)
WEATHER_LOG_LEVEL=INFO
```

### API Endpoint Configuration

For using alternative weather providers:

```bash
# Base URL for weather API
WEATHER_API_BASE_URL=https://weather.googleapis.com/v1

# Endpoint paths
WEATHER_CURRENT_ENDPOINT=currentConditions:lookup
WEATHER_HOURLY_ENDPOINT=forecast/hours:lookup
WEATHER_DAILY_ENDPOINT=forecast/days:lookup
```

## Service Management

### Starting/Stopping

```bash
# Start service
sudo systemctl start weather-daemon

# Stop service
sudo systemctl stop weather-daemon

# Restart service
sudo systemctl restart weather-daemon

# Enable on boot
sudo systemctl enable weather-daemon

# Disable on boot
sudo systemctl disable weather-daemon
```

### Monitoring

```bash
# Check status
sudo systemctl status weather-daemon

# Follow logs
sudo journalctl -u weather-daemon -f

# View recent logs
sudo journalctl -u weather-daemon -n 100

# View logs since boot
sudo journalctl -u weather-daemon -b
```

### Using Make Commands

If installed via git clone:

```bash
make status    # Show service status
make logs      # Follow service logs
make restart   # Restart service
```

## Troubleshooting

### Service Won't Start

1. **Check configuration:**
```bash
sudo /opt/weather-daemon/venv/bin/weather-daemon test --config /etc/weather-daemon/config.env
```

2. **Check logs:**
```bash
sudo journalctl -u weather-daemon -n 50 --no-pager
```

3. **Verify permissions:**
```bash
ls -la /etc/weather-daemon/
ls -la /var/www/html/weather/
```

### API Key Issues

**Error: "WEATHER_API_KEY environment variable is required"**
- Edit `/etc/weather-daemon/config.env` and add your API key
- Restart service: `sudo systemctl restart weather-daemon`

**Error: "403 Forbidden" or "404 Not Found"**
- Verify API key is correct
- Ensure Weather API is enabled in Google Cloud Console
- Check that billing is set up (Weather API requires it)
- Verify API key has permissions for Weather API

### Permission Errors

**Error: "Permission denied" writing to output directory**

```bash
# Fix ownership
sudo chown weather-daemon:weather-daemon /var/www/html/weather

# Fix permissions
sudo chmod 755 /var/www/html/weather
```

### Output File Not Created

1. Check service is running:
```bash
sudo systemctl status weather-daemon
```

2. Check logs for errors:
```bash
sudo journalctl -u weather-daemon -f
```

3. Manually test:
```bash
sudo -u weather-daemon /opt/weather-daemon/venv/bin/weather-daemon test --config /etc/weather-daemon/config.env
```

### Nginx Not Serving File

1. Verify file exists:
```bash
ls -la /var/www/html/weather/weather_forecast.json
```

2. Check nginx configuration:
```bash
sudo nginx -t
```

3. Verify include statement in nginx config:
```bash
grep -r "weather-locations.conf" /etc/nginx/
```

4. Check nginx logs:
```bash
sudo tail -f /var/log/nginx/error.log
```

## Updating

To update the daemon:

```bash
# Stop service
sudo systemctl stop weather-daemon

# Pull latest code
cd /opt/weather-daemon
sudo git pull

# Update dependencies
sudo venv/bin/pip install -e . --upgrade

# Restart service
sudo systemctl start weather-daemon
```

## Uninstalling

To completely remove the weather-daemon:

```bash
# Stop and disable service
sudo systemctl stop weather-daemon
sudo systemctl disable weather-daemon

# Remove service file
sudo rm /etc/systemd/system/weather-daemon.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/weather-daemon

# Remove configuration
sudo rm -rf /etc/weather-daemon

# Remove output directory (optional)
sudo rm -rf /var/www/html/weather

# Remove service user (optional)
sudo userdel weather-daemon
```

## Getting Help

- **Documentation:** See README.md for full documentation
- **Issues:** Report bugs at https://github.com/yourusername/weather-daemon/issues
- **Logs:** Always check `journalctl -u weather-daemon` first

## Security Considerations

- API key is stored in `/etc/weather-daemon/config.env` with 600 permissions
- Service runs as unprivileged `weather-daemon` user
- Systemd service has extensive security hardening:
  - No new privileges
  - Read-only root filesystem
  - Only `/var/www/html/weather` is writable
  - Network restricted to outbound HTTP/HTTPS only
  - Syscall filtering enabled
- Never commit `.env` files to version control
