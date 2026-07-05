---
name: weather-validator-skill
description: >
  Weather & COMM Console Agent skill. Fetches real-time and forecast
  weather data from the Open-Meteo API to assess visual observation
  feasibility for satellite passes. Classifies visibility based on
  cloud cover layers and atmospheric conditions. Applies Weather
  Fallback Rule (R-005) on API failure.
---

# Weather & COMM Console — Weather Validator Skill

## Console Designation
**Weather & COMM (Weather and Communications)** — The environmental assessment
authority. Responsible for all meteorological data acquisition, cloud cover
analysis, and visual observation feasibility classification.

## Trigger Conditions
Activate this skill when:
- The Flight Director dispatches a `WEATHER_CHECK` intent
- A satellite pass window has been computed and needs visibility assessment
- The user explicitly asks about observation conditions or "can I see"

Do NOT activate when:
- The request is purely orbital/positional without observation context
- Weather data has already been fetched for the requested time window
- The intent is `SATELLITE_POSITION` without visibility keywords

## Execution Protocol

### Step 1: Resolve Observer Coordinates

If the observer location is a city name (not yet geocoded):

**Geocoding Endpoint**:
```
GET https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json
```

**Response Example**:
```json
{
  "results": [
    {
      "id": 1277333,
      "name": "Bengaluru",
      "latitude": 12.9716,
      "longitude": 77.5946,
      "elevation": 920.0,
      "timezone": "Asia/Kolkata",
      "country": "India",
      "admin1": "Karnataka"
    }
  ]
}
```

**Validation**:
- If `results` array is empty → return `GEOCODE_FAILED` error
- If multiple results → use the first (highest relevance)
- **Default fallback**: Bengaluru, India (12.9716°N, 77.5946°E)

### Step 2: Fetch Weather Forecast from Open-Meteo

**Forecast Endpoint**:
```
GET https://api.open-meteo.com/v1/forecast
```

**Required Parameters**:
```
latitude={lat}
longitude={lon}
hourly=cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,
       temperature_2m,relative_humidity_2m,visibility,weather_code
timezone=UTC
forecast_days=3
```

**Response Structure**:
```json
{
  "latitude": 12.97,
  "longitude": 77.59,
  "generationtime_ms": 0.5,
  "utc_offset_seconds": 0,
  "timezone": "GMT",
  "hourly_units": {
    "time": "iso8601",
    "cloud_cover": "%",
    "cloud_cover_low": "%",
    "cloud_cover_mid": "%",
    "cloud_cover_high": "%",
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "visibility": "m"
  },
  "hourly": {
    "time": ["2026-07-01T00:00", "2026-07-01T01:00", "..."],
    "cloud_cover": [25, 30, 45],
    "cloud_cover_low": [10, 15, 20],
    "cloud_cover_mid": [15, 20, 30],
    "cloud_cover_high": [5, 10, 15],
    "temperature_2m": [28.5, 27.8, 26.2],
    "relative_humidity_2m": [65, 70, 75],
    "visibility": [24140, 22000, 18000]
  }
}
```

**API Details**:
- **Free tier**: No API key required
- **Rate limit**: 10,000 requests/day (generous for our use case)
- **Timeout**: Set 10-second timeout
- **On failure**: Apply Weather Fallback Rule (R-005)

See `references/open_meteo_api.md` for full API documentation.

### Step 3: Interpolate Weather to Pass Times

The Open-Meteo API returns hourly data. For precise pass-time weather:
1. Find the two hourly data points bracketing the pass `culmination_utc`
2. Linear-interpolate cloud cover percentages between them
3. Use the interpolated values for classification

### Step 4: Classify Visibility (Layered Cloud Analysis)

#### Simple Classification (Total Cloud Cover)

| Total Cloud Cover % | Classification | Emoji | Observation Likelihood |
|---------------------|---------------|-------|----------------------|
| 0 – 25 | `CLEAR` | ☀️ | Excellent |
| 26 – 50 | `MOSTLY_CLEAR` | 🌤️ | Good |
| 51 – 75 | `PARTIAL` | ⛅ | Possible |
| 76 – 90 | `MOSTLY_CLOUDY` | 🌥️ | Unlikely |
| 91 – 100 | `OBSTRUCTED` | ☁️ | Very Unlikely |

#### Advanced Classification (Layered Cloud Impact)

Different cloud layers have varying impact on satellite visibility:

| Layer | Altitude | Impact Factor | Reason |
|-------|----------|--------------|--------|
| Low clouds (stratus, <2km) | `cloud_cover_low` | ×1.0 (full) | Dense, fully blocks |
| Mid clouds (alto, 2-6km) | `cloud_cover_mid` | ×0.8 | Moderate blockage |
| High clouds (cirrus, >6km) | `cloud_cover_high` | ×0.4 | Thin, may allow observation |

**Effective Cloud Cover Computation**:
```python
effective_cover = max(
    cloud_cover_low * 1.0,
    cloud_cover_mid * 0.8,
    cloud_cover_high * 0.4
)
```

Use `effective_cover` for classification instead of raw `cloud_cover` when
layered data is available.

#### Elevation-Adjusted Assessment
Higher-elevation passes are more forgiving of partial cloud cover:
- Pass at 70° elevation → visible through breaks in scattered clouds
- Pass at 15° elevation → long atmospheric path, more affected by any clouds

```python
elevation_factor = 1.0 - (max_elevation_deg / 90.0) * 0.3
adjusted_cover = effective_cover * elevation_factor
```

### Step 5: Generate Visibility Report

Return a JSON response to the Flight Director:

```json
{
  "status": "SUCCESS",
  "data_source": "Open-Meteo",
  "observer": {
    "city": "Bengaluru",
    "latitude": 12.9716,
    "longitude": 77.5946
  },
  "reports": [
    {
      "check_time_utc": "2026-07-02T01:27:12Z",
      "cloud_cover_total_pct": 15,
      "cloud_cover_low_pct": 5,
      "cloud_cover_mid_pct": 10,
      "cloud_cover_high_pct": 8,
      "effective_cover_pct": 10,
      "visibility_class": "CLEAR",
      "temperature_c": 22.4,
      "humidity_pct": 65,
      "visibility_m": 24140,
      "recommendation": "☀️ Excellent viewing conditions expected. Clear skies with minimal cloud cover.",
      "observation_likelihood": "Excellent"
    }
  ]
}
```

### Step 6: Weather Fallback (Rule R-005)

If the Open-Meteo API fails or times out:

```json
{
  "status": "FALLBACK",
  "data_source": "FALLBACK_CLEAR_SKY",
  "fallback_reason": "Open-Meteo API timeout after 10 seconds",
  "reports": [
    {
      "check_time_utc": "2026-07-02T01:27:12Z",
      "cloud_cover_total_pct": 0,
      "visibility_class": "CLEAR",
      "recommendation": "ℹ️ TELEMETRY NOTICE: Weather data temporarily unavailable. Assuming clear-sky conditions. Verify local weather independently before planning your observation session.",
      "observation_likelihood": "Unknown (weather data unavailable)"
    }
  ]
}
```

## Recommendation Templates

### CLEAR (0-25%)
```
☀️ Excellent viewing conditions expected. Clear skies with {cover}% cloud cover.
Recommended for visual satellite observation.
```

### MOSTLY_CLEAR (26-50%)
```
🌤️ Good viewing conditions with {cover}% cloud cover.
Satellite should be visible during clear intervals.
```

### PARTIAL (51-75%)
```
⛅ Partial cloud cover ({cover}%) may intermittently obscure the satellite.
Observation is possible but not guaranteed. Best viewing during breaks
in cloud cover near the culmination point.
```

### MOSTLY_CLOUDY (76-90%)
```
🌥️ Significant cloud cover ({cover}%) expected during this pass.
Visual observation is unlikely but not impossible. Consider monitoring
conditions closer to pass time for potential clearing.
```

### OBSTRUCTED (91-100%)
```
☁️ Heavy cloud cover ({cover}%) is expected during this pass.
Visual observation is very unlikely. Consider monitoring the next
available pass window or using radio tracking instead.
```

## Guardrails

- **NEVER** fabricate weather data — if API fails, use Fallback Rule R-005
- Always timestamp weather data and note that forecasts carry uncertainty
- Do **NOT** suppress satellite pass data due to bad weather (Rule R-006)
- Weather recommendations are **advisory only** — state this in output
- Include `data_source` field in every response (Rule R-004)

## Tool Access Requirements
- HTTP GET access to `api.open-meteo.com` (weather forecast)
- HTTP GET access to `geocoding-api.open-meteo.com` (city geocoding)
- No API key required (free tier, no authentication)
