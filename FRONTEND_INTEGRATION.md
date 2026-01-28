# Frontend Integration Guide

This guide explains how to integrate the weather-daemon with the www-main website.

## Overview

The weather daemon generates a JSON file at `/opt/weather-daemon/cache/weather_forecast.json` which the frontend reads via JavaScript. The frontend is already set up and ready to use the daemon's output.

## ✅ Frontend Status

The `www-main/html/` directory is **already configured** to work with the weather daemon:

### JavaScript (`js/weather.js`)
- ✅ Fetches from `/weather/weather_forecast.json`
- ✅ Parses all required fields (location, temp, hourly, daily)
- ✅ Auto-refreshes every 30 seconds
- ✅ Handles missing data gracefully
- ✅ Compatible with daemon output format

### HTML (`index.html`)
- ✅ Weather section with proper data attributes
- ✅ Placeholder content for graceful degradation
- ✅ Semantic HTML structure
- ✅ Accessibility labels

### CSS (`css/weather.css`)
- ✅ Responsive design (mobile and desktop)
- ✅ Dark theme styling
- ✅ Clean, modern layout
- ✅ Grid-based responsive layout

## Integration Steps

### 1. Deploy the Weather Daemon

Follow the installation guide in `INSTALLATION.md`:

```bash
# On your production server
cd /opt/weather-daemon
sudo ./setup.sh
```

This will:
- Install the daemon to `/opt/weather-daemon/`
- Create output directory at `/opt/weather-daemon/cache/`
- Configure systemd service
- Start polling Google Weather API

### 2. Create Symlink to Web Root

The daemon writes to `/opt/weather-daemon/cache/`, but the frontend expects `/weather/weather_forecast.json`. Create a symlink:

```bash
# Create weather directory in web root if it doesn't exist
sudo mkdir -p /var/www/yoursite.com/html/weather

# Create symlink from daemon cache to web root
sudo ln -s /opt/weather-daemon/cache/weather_forecast.json \
           /var/www/yoursite.com/html/weather/weather_forecast.json

# Verify symlink
ls -lh /var/www/yoursite.com/html/weather/
```

### 3. Configure Nginx (if needed)

If you're using nginx, ensure it can serve the JSON file:

```nginx
# In your nginx server block
location /weather/ {
    alias /var/www/yoursite.com/html/weather/;

    # Cache control for JSON
    location ~* \.json$ {
        add_header Cache-Control "public, max-age=60"; # Cache for 1 minute
        add_header Access-Control-Allow-Origin "*";    # CORS if needed
    }
}
```

Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Deploy Frontend Files

Copy the `www-main/html/` files to your web root:

```bash
# Copy files to production server
rsync -avz --exclude='.DS_Store' \
    www-main/html/ \
    user@server:/var/www/yoursite.com/html/

# Or if files are already there, just verify
ls -lh /var/www/yoursite.com/html/js/weather.js
ls -lh /var/www/yoursite.com/html/css/weather.css
```

### 5. Verify Integration

1. **Check daemon is running:**
   ```bash
   sudo systemctl status weather-daemon
   ```

2. **Check JSON file exists:**
   ```bash
   cat /opt/weather-daemon/cache/weather_forecast.json | jq
   ```

3. **Check symlink works:**
   ```bash
   curl http://localhost/weather/weather_forecast.json | jq
   ```

4. **Check frontend loads:**
   - Open `http://yoursite.com` in browser
   - Scroll to weather section
   - Open browser console (F12)
   - Should see weather data loading
   - Check for JavaScript errors

## Output Format Compatibility

The daemon outputs JSON in exactly the format the frontend expects:

```json
{
  "location": "Austin, TX",
  "updated": "2026-01-27T20:56:22.504425+00:00",
  "updated_display": "Updated 8:56 PM UTC",
  "coordinates": {
    "lat": 30.2672,
    "lon": -97.7431
  },
  "now": {
    "temp": 46,
    "summary": "Cloudy",
    "icon": "☁️",
    "high": 44,
    "low": 20,
    "precip_chance": 10
  },
  "hourly": [
    {"time": "2 PM", "temp": 45, "icon": "☁️"},
    {"time": "3 PM", "temp": 46, "icon": "☁️"}
  ],
  "daily": [
    {
      "day": "Tuesday",
      "high": 47,
      "low": 20,
      "summary": "Cloudy",
      "icon": "☁️"
    }
  ],
  "feed": {
    "path": "/weather/weather_forecast.json"
  }
}
```

### Field Mapping

| Daemon Output | Frontend Usage |
|---------------|----------------|
| `location` | Location name display |
| `updated_display` | Last update timestamp |
| `now.temp` | Current temperature (large display) |
| `now.summary` | Current conditions text |
| `now.icon` | Weather emoji icon |
| `now.high` / `now.low` | Today's high/low |
| `now.precip_chance` | Precipitation probability |
| `hourly[].time` | Hour label (e.g., "2 PM") |
| `hourly[].temp` | Hourly temperature |
| `hourly[].icon` | Hourly weather icon |
| `daily[].day` | Day name (e.g., "Monday") |
| `daily[].high` / `daily[].low` | Daily high/low temps |
| `daily[].summary` | Daily conditions |
| `daily[].icon` | Daily weather icon |

## Frontend Behavior

### Auto-Refresh
The frontend automatically refreshes weather data:
- Every 30 seconds while page is visible
- When tab becomes visible again (after being hidden)
- Cache-busting with timestamp parameter

### Error Handling
- Fails silently if JSON unavailable
- Shows placeholder content (from HTML)
- Logs warnings to browser console
- Doesn't break page layout

### Performance
- Async fetch (non-blocking)
- Small JSON payload (~2-3 KB)
- Client-side rendering
- Minimal DOM updates

## Troubleshooting

### Weather section shows placeholder data

**Check 1: Daemon running?**
```bash
sudo systemctl status weather-daemon
```

**Check 2: JSON file exists?**
```bash
ls -lh /opt/weather-daemon/cache/weather_forecast.json
```

**Check 3: Symlink correct?**
```bash
ls -lh /var/www/yoursite.com/html/weather/weather_forecast.json
```

**Check 4: Nginx serving it?**
```bash
curl http://localhost/weather/weather_forecast.json
```

**Check 5: Browser console?**
Open F12 developer tools → Console tab → Look for errors

### Weather data not updating

**Check daemon logs:**
```bash
journalctl -u weather-daemon -n 50
```

**Check file modification time:**
```bash
stat /opt/weather-daemon/cache/weather_forecast.json
```

Should update every hour (or whatever `WEATHER_POLL_INTERVAL` is set to).

### CORS errors in browser

If loading from different domain, add CORS headers to nginx:

```nginx
location /weather/ {
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
}
```

### JSON shows wrong location

Update daemon configuration:
```bash
sudo nano /etc/weather-daemon/config.env
# Change WEATHER_LATITUDE, WEATHER_LONGITUDE, WEATHER_LOCATION_NAME
sudo systemctl restart weather-daemon
```

## Testing

### Test with curl
```bash
# Fetch JSON
curl -s http://yoursite.com/weather/weather_forecast.json | jq

# Check specific fields
curl -s http://yoursite.com/weather/weather_forecast.json | jq '.now.temp'
curl -s http://yoursite.com/weather/weather_forecast.json | jq '.hourly[0]'
```

### Test frontend JavaScript
Open browser console and run:
```javascript
// Manually trigger refresh
fetch('/weather/weather_forecast.json?t=' + Date.now())
  .then(r => r.json())
  .then(d => console.table(d))
  .catch(e => console.error('Failed:', e));
```

## Development Testing

To test locally without deploying:

```bash
# Start daemon in test mode (outputs to ./test_output/)
cd /Users/govan/weather-daemon
source venv/bin/activate
weather-daemon test --config .env

# Serve test output via Python HTTP server
cd test_output
python3 -m http.server 8000

# Access at http://localhost:8000/weather_forecast.json
```

Then update `www-main/html/js/weather.js` line 2 temporarily:
```javascript
const WEATHER_URL = 'http://localhost:8000/weather_forecast.json';
```

## Performance Notes

- **JSON Size**: ~2-3 KB (minified)
- **Fetch Frequency**: Every 30 seconds (frontend)
- **Update Frequency**: Every hour (daemon, configurable)
- **Browser Caching**: Disabled via cache-busting
- **Server Caching**: 60 seconds (nginx, optional)

## Security Notes

- JSON file is world-readable (required for web serving)
- No sensitive data in JSON output
- API key stored securely in `/etc/weather-daemon/config.env` (root-only)
- Health check endpoint only on localhost (127.0.0.1:8080)

## Next Steps

Once integrated:
1. Monitor daemon logs for first 24 hours
2. Check weather updates every hour
3. Verify frontend displays correctly on mobile/desktop
4. Set up monitoring alerts for daemon health endpoint
5. Consider adding weather data to your sitemap/robots.txt

## Support

For issues:
- Check daemon logs: `journalctl -u weather-daemon -f`
- Check nginx logs: `tail -f /var/log/nginx/error.log`
- Check browser console for JavaScript errors
- Verify JSON format with `jq`
- Review `ENHANCEMENTS.md` for health check monitoring
