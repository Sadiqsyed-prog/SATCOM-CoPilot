# Open-Meteo API Reference

## Overview
Open-Meteo is a free, open-source weather API. No API key required.
Free tier supports 10,000 requests/day — more than sufficient for our use case.

## Endpoints

### Weather Forecast
```
GET https://api.open-meteo.com/v1/forecast
```

### Geocoding (City → Coordinates)
```
GET https://geocoding-api.open-meteo.com/v1/search
```

---

## Forecast API Parameters

### Required
| Parameter | Type | Description |
|-----------|------|-------------|
| `latitude` | float | Location latitude (-90 to 90) |
| `longitude` | float | Location longitude (-180 to 180) |

### Hourly Variables (for satellite observation)
| Variable | Unit | Relevance |
|----------|------|-----------|
| `cloud_cover` | % | **PRIMARY** — total sky cover |
| `cloud_cover_low` | % | Low clouds (<2km) — dense, blocks fully |
| `cloud_cover_mid` | % | Mid clouds (2-6km) — moderate blocking |
| `cloud_cover_high` | % | High clouds (>6km) — thin, partial blocking |
| `temperature_2m` | °C | Comfort for ground observer |
| `relative_humidity_2m` | % | Dew/fog risk indicator |
| `visibility` | m | Horizontal visibility (atmospheric clarity) |
| `weather_code` | WMO code | Weather condition classification |

### Optional
| Parameter | Default | Description |
|-----------|---------|-------------|
| `timezone` | `GMT` | Use `UTC` or `auto` |
| `forecast_days` | 7 | Number of days (1-16) |
| `forecast_hours` | — | Limit to N hours instead of days |
| `past_days` | 0 | Include past weather (0-92) |

### Example Request
```
https://api.open-meteo.com/v1/forecast
  ?latitude=12.9716
  &longitude=77.5946
  &hourly=cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,
          temperature_2m,relative_humidity_2m,visibility
  &timezone=UTC
  &forecast_days=3
```

---

## Geocoding API Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | City name to search |
| `count` | int | Max results to return (default 10) |
| `language` | string | Response language (e.g., `en`) |
| `format` | string | `json` (default) |

### Example Request
```
https://geocoding-api.open-meteo.com/v1/search
  ?name=Bengaluru
  &count=1
  &language=en
  &format=json
```

### Response
```json
{
  "results": [
    {
      "id": 1277333,
      "name": "Bengaluru",
      "latitude": 12.97194,
      "longitude": 77.59369,
      "elevation": 920.0,
      "feature_code": "PPLA",
      "country_code": "IN",
      "country": "India",
      "admin1": "Karnataka",
      "timezone": "Asia/Kolkata",
      "population": 8443675
    }
  ]
}
```

---

## WMO Weather Codes (Subset)

| Code | Description | Impact on Observation |
|------|-------------|----------------------|
| 0 | Clear sky | ☀️ Excellent |
| 1 | Mainly clear | 🌤️ Good |
| 2 | Partly cloudy | ⛅ Moderate |
| 3 | Overcast | ☁️ Poor |
| 45, 48 | Fog | 🌫️ Very Poor |
| 51-55 | Drizzle | 🌧️ Poor |
| 61-65 | Rain | 🌧️ Poor |
| 71-75 | Snowfall | ❄️ Poor |
| 80-82 | Rain showers | 🌧️ Variable |
| 95-99 | Thunderstorm | ⛈️ Very Poor |

---

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Parse response normally |
| 400 | Bad request | Check parameters (invalid lat/lon) |
| 429 | Rate limited | Retry after 60 seconds |
| 500+ | Server error | Apply Fallback Rule R-005 |
| Timeout | No response in 10s | Apply Fallback Rule R-005 |

## Rate Limits (Free Tier)
- **Daily**: 10,000 requests
- **Concurrent**: No explicit limit
- **Recommendation**: Cache responses for 1 hour per location
