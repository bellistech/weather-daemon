# Recent Changes - API Configuration

## What Changed

Made API endpoints fully configurable to avoid hardcoding and enable flexibility.

### Configuration Changes

**New Environment Variables:**
- `WEATHER_API_BASE_URL` - Base URL for weather API (default: https://weather.googleapis.com/v1)
- `WEATHER_CURRENT_ENDPOINT` - Current conditions endpoint (default: currentConditions:lookup)
- `WEATHER_HOURLY_ENDPOINT` - Hourly forecast endpoint (default: forecast/hours:lookup)
- `WEATHER_DAILY_ENDPOINT` - Daily forecast endpoint (default: forecast/days:lookup)

### Code Changes

1. **config.py** - Added endpoint configuration fields with sensible defaults
2. **daemon.py** - Removed hardcoded URLs, now builds from configuration
3. **cli.py** - Passes endpoint configuration to daemon
4. **.env.example** - Documented new optional configuration
5. **README.md** - Added section on using alternative weather APIs

### Benefits

- No hardcoded API endpoints
- Easy to switch weather providers
- Testable with mock endpoints
- Configuration follows 12-factor app principles
- Backwards compatible (uses defaults if not specified)

### Security

- API keys remain in environment variables (never hardcoded)
- `.env` files are gitignored
- Clear warnings in .env.example about not committing keys

### Example: Using a Different Provider

```bash
# Example for a hypothetical alternative API
WEATHER_API_BASE_URL=https://api.weatherprovider.com/v2
WEATHER_CURRENT_ENDPOINT=current
WEATHER_HOURLY_ENDPOINT=forecast/hourly
WEATHER_DAILY_ENDPOINT=forecast/daily
```

Note: If using a different provider, you may also need to adapt the `_fetch_weather()` 
method in daemon.py to match their request/response format.
