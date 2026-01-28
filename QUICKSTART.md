# Weather Daemon - Quick Start Guide

Complete setup guide to get weather data displaying on your website.

## Prerequisites

- Python 3.9+
- Google Maps Weather API key ([Get one here](https://developers.google.com/maps/documentation/weather))
- Root/sudo access to server
- Nginx web server

## Step 1: Deploy Daemon (5 minutes)

```bash
# Clone or copy project to server
cd /opt
sudo git clone <repo-url> weather-daemon
cd weather-daemon

# Run automated setup
sudo ./setup.sh

# When prompted, provide:
# - API key: AIzaSyD-vAbdmb2Zi8ZSbvHyPLCQHq8WdzhmZpw (or yours)
# - Latitude: 30.2672 (Austin, TX - or your location)
# - Longitude: -97.7431
# - Location name: Austin, TX (or your city)
```

Setup script will:
- Install dependencies
- Create system user
- Set up systemd service
- Start daemon

## Step 2: Create Symlink (1 minute)

```bash
# Link daemon output to web root
sudo ln -s /opt/weather-daemon/cache/weather_forecast.json \
           /var/www/bellis.tech/html/weather/weather_forecast.json

# Verify
ls -lh /var/www/bellis.tech/html/weather/weather_forecast.json
```

## Step 3: Configure Nginx (2 minutes)

Add to your nginx server block:

```nginx
location /weather/ {
    alias /var/www/bellis.tech/html/weather/;

    location ~* \.json$ {
        add_header Cache-Control "public, max-age=60";
        add_header Access-Control-Allow-Origin "*";
    }
}
```

Reload nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Step 4: Verify (2 minutes)

```bash
# Check daemon is running
sudo systemctl status weather-daemon

# Check JSON is generated
curl -s /opt/weather-daemon/cache/weather_forecast.json | jq '.now.temp'

# Check web access
curl -s http://bellis.tech/weather/weather_forecast.json | jq '.location'
```

## Step 5: Deploy Frontend (Already Done! ✓)

Your `www-main/html/` directory already has:
- ✅ `js/weather.js` - Fetches and renders weather data
- ✅ `css/weather.css` - Styles weather widget
- ✅ `index.html` - Weather section markup

Just deploy these files to your web root if not already there.

## Verify Integration

Open `http://bellis.tech` in browser and check:
1. Weather section loads (scroll to weather section)
2. Shows "Austin, TX" (or your location)
3. Displays current temperature
4. Shows hourly and daily forecasts
5. Updates timestamp appears

## Configuration

All settings in `/etc/weather-daemon/config.env`:

```bash
# Required
WEATHER_API_KEY=your_key_here
WEATHER_LATITUDE=30.2672
WEATHER_LONGITUDE=-97.7431

# Optional
WEATHER_LOCATION_NAME=Austin, TX
WEATHER_POLL_INTERVAL=3600           # 1 hour
WEATHER_OUTPUT_DIR=/opt/weather-daemon/cache
WEATHER_LOG_FORMAT=text              # or "json" for production
WEATHER_HEALTH_CHECK_ENABLED=true    # Health monitoring
WEATHER_HEALTH_CHECK_PORT=8080       # Health endpoint port
```

After changes:
```bash
sudo systemctl restart weather-daemon
```

## Monitoring

### Check daemon health
```bash
# Via systemd
sudo systemctl status weather-daemon

# Via health endpoint
curl http://localhost:8080/health | jq

# Via logs
journalctl -u weather-daemon -f
```

### Check metrics
```bash
curl http://localhost:8080/metrics | jq
```

### View structured logs (if JSON logging enabled)
```bash
journalctl -u weather-daemon -o json | jq
```

## Troubleshooting

### Weather not showing on website?

```bash
# 1. Is daemon running?
sudo systemctl status weather-daemon

# 2. Is JSON file present?
cat /opt/weather-daemon/cache/weather_forecast.json | jq

# 3. Can nginx access it?
curl http://localhost/weather/weather_forecast.json

# 4. Check browser console (F12)
# Look for network errors or JavaScript errors
```

### JSON file not updating?

```bash
# Check last update time
stat /opt/weather-daemon/cache/weather_forecast.json

# Check daemon logs for errors
journalctl -u weather-daemon -n 50

# Check API key is valid
sudo cat /etc/weather-daemon/config.env | grep API_KEY
```

### Wrong location showing?

```bash
# Update config
sudo nano /etc/weather-daemon/config.env
# Change WEATHER_LATITUDE, WEATHER_LONGITUDE, WEATHER_LOCATION_NAME

# Restart daemon
sudo systemctl restart weather-daemon

# Watch it update
journalctl -u weather-daemon -f
```

## File Locations

| Purpose | Path |
|---------|------|
| Daemon binary | `/opt/weather-daemon/venv/bin/weather-daemon` |
| Configuration | `/etc/weather-daemon/config.env` |
| JSON output | `/opt/weather-daemon/cache/weather_forecast.json` |
| Systemd service | `/etc/systemd/system/weather-daemon.service` |
| Logs | `journalctl -u weather-daemon` |
| Health endpoint | `http://localhost:8080/health` |

## Common Commands

```bash
# Start/stop/restart
sudo systemctl start weather-daemon
sudo systemctl stop weather-daemon
sudo systemctl restart weather-daemon

# View logs
journalctl -u weather-daemon -f        # Follow
journalctl -u weather-daemon -n 100    # Last 100 lines
journalctl -u weather-daemon --since "1 hour ago"

# Test configuration (doesn't start daemon)
/opt/weather-daemon/venv/bin/weather-daemon test \
    --config /etc/weather-daemon/config.env

# Check health
curl http://localhost:8080/health
curl http://localhost:8080/metrics

# View JSON output
curl http://bellis.tech/weather/weather_forecast.json | jq
```

## Next Steps

1. ✅ Daemon running and generating JSON
2. ✅ Frontend displaying weather
3. Configure monitoring alerts (see `ENHANCEMENTS.md`)
4. Enable JSON logging for production (set `WEATHER_LOG_FORMAT=json`)
5. Add uptime monitoring for health endpoint
6. Review logs after 24 hours of operation

## Getting Help

- **Daemon issues**: Check `journalctl -u weather-daemon`
- **Frontend issues**: Check browser console (F12)
- **API issues**: Check Google Cloud Console quotas
- **Full documentation**: See `INSTALLATION.md`, `FRONTEND_INTEGRATION.md`, `ENHANCEMENTS.md`

## Success Criteria

You'll know it's working when:
- ✅ `systemctl status weather-daemon` shows "active (running)"
- ✅ `/opt/weather-daemon/cache/weather_forecast.json` exists and updates hourly
- ✅ `curl http://localhost:8080/health` returns `{"healthy": true}`
- ✅ Website shows live weather data for your location
- ✅ Weather updates automatically without page refresh
- ✅ Mobile and desktop views both work

Enjoy your live weather integration! 🌤️
