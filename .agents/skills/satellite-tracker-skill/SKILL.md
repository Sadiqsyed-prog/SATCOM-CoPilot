---
name: satellite-tracker-skill
description: >
  GNC Console (Guidance, Navigation, and Control) Agent skill. Fetches
  live Two-Line Element (TLE) data from CelesTrak and computes satellite
  pass windows over an observer location using SGP4 propagation via the
  Skyfield library. Triggered when the Flight Director identifies a
  TRACK_PASS or SATELLITE_POSITION intent.
---

# GNC Console — Satellite Tracker Skill

## Console Designation
**GNC (Guidance, Navigation, and Control)** — The orbital mechanics authority.
Responsible for all satellite position computations, trajectory propagation,
and pass window predictions using verified ephemeris data.

## Trigger Conditions
Activate this skill when:
- The Flight Director dispatches a `TRACK_PASS` intent
- The Flight Director dispatches a `SATELLITE_POSITION` intent
- The request contains a satellite identifier (name or NORAD ID)
- The request contains an observer location (city name or lat/lon)

Do NOT activate when:
- The query is purely about weather without satellite context
- The query is about non-orbital objects (aircraft, drones, balloons)
- The query is a HELP or UNKNOWN intent

## Execution Protocol

### Step 1: Resolve Satellite Identity
1. Receive satellite name/ID from Flight Director
2. Normalize against the alias table (see `copilot-router-skill/references/intent_taxonomy.md`)
3. If not in alias table → query CelesTrak search endpoint
4. If unresolvable → return `SATELLITE_NOT_FOUND` error to Flight Director
5. **Default**: ISS (ZARYA), NORAD ID 25544

### Step 2: Fetch TLE Data from CelesTrak

**Primary Endpoint** (by NORAD Catalog Number):
```
GET https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE
```

**Fallback Endpoint** (by satellite name):
```
GET https://celestrak.org/NORAD/elements/gp.php?NAME={sat_name}&FORMAT=TLE
```

**Response Format** — Plain text, 3 lines per satellite:
```
ISS (ZARYA)
1 25544U 98067A   26182.50000000  .00016717  00000-0  10270-3 0  9025
2 25544  51.6400 200.1234 0007500  50.1234 310.5678 15.48919755123456
```

**TLE Validation Checks** (all must pass):
- [ ] Line 1 starts with `1 ` and is exactly 69 characters
- [ ] Line 2 starts with `2 ` and is exactly 69 characters
- [ ] NORAD ID on Line 1 matches NORAD ID on Line 2
- [ ] Modulo-10 checksum validates on both lines
- [ ] Epoch is within 7 days of current time (accuracy warning if older)

**Caching Policy**:
- Cache TLE data locally for 4 hours
- CelesTrak updates orbital elements approximately every 2 hours
- Stale cache (>4 hours) triggers a fresh fetch; failure uses stale data with warning

See `references/tle_format_spec.md` for complete field-level documentation.
See `references/celestrak_api.md` for full API endpoint reference.

### Step 3: Compute Pass Windows (Skyfield/SGP4)

Use Skyfield's `find_events()` method for pass computation:

```python
from skyfield.api import load, wgs84, EarthSatellite

# Initialize timescale and ephemeris
ts = load.timescale()
eph = load('de421.bsp')  # JPL ephemeris for Sun position

# Define time window
t0 = ts.now()
t1 = ts.tt_jd(t0.tt + time_window_days)

# Build satellite and observer objects
satellite = EarthSatellite(tle_line1, tle_line2, sat_name, ts)
observer = wgs84.latlon(latitude, longitude, elevation_m=elevation)

# Find pass events (rise=0, culminate=1, set=2)
t_events, events = satellite.find_events(
    observer, t0, t1, altitude_degrees=10.0
)
```

**Event Mapping**:
- Event `0` → Rise above minimum elevation
- Event `1` → Culmination (maximum elevation point)
- Event `2` → Set below minimum elevation

**Sunlit Check** (for visual observation):
```python
is_sunlit = satellite.at(t_event).is_sunlit(eph)
```

**Topocentric Position** (altitude/azimuth):
```python
difference = satellite - observer
topocentric = difference.at(t_event)
alt, az, distance = topocentric.altaz()
```

### Step 4: Structure Output

Return a JSON response to the Flight Director:

```json
{
  "status": "SUCCESS",
  "satellite": "ISS (ZARYA)",
  "norad_id": 25544,
  "tle_epoch": "2026-07-01T12:00:00Z",
  "data_source": "CelesTrak",
  "computation_engine": "Skyfield/SGP4",
  "observer": {
    "city": "Bengaluru",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "elevation_m": 920
  },
  "passes": [
    {
      "pass_number": 1,
      "rise_utc": "2026-07-02T01:23:45Z",
      "rise_azimuth_deg": 220.1,
      "culmination_utc": "2026-07-02T01:27:12Z",
      "max_elevation_deg": 67.3,
      "set_utc": "2026-07-02T01:30:40Z",
      "set_azimuth_deg": 45.8,
      "is_sunlit": true,
      "duration_seconds": 415,
      "visibility_rating": "EXCELLENT"
    }
  ]
}
```

**Visibility Rating Thresholds**:
| Max Elevation | Rating |
|--------------|--------|
| > 45° | `EXCELLENT` |
| 20° – 45° | `GOOD` |
| 10° – 20° | `LOW` |

### Step 5: Error Responses

**TLE_FETCH_FAILED**:
```json
{
  "status": "ERROR",
  "error_code": "TLE_FETCH_FAILED",
  "error_message": "Unable to retrieve TLE data from CelesTrak for NORAD ID {id}.",
  "data_source": "UNAVAILABLE",
  "recommendation": "Retry in 60 seconds or verify NORAD catalog number."
}
```

**SATELLITE_NOT_FOUND**:
```json
{
  "status": "ERROR",
  "error_code": "SATELLITE_NOT_FOUND",
  "error_message": "No satellite matching \"{query}\" found in CelesTrak catalog.",
  "data_source": "CelesTrak",
  "recommendation": "Verify satellite name or NORAD ID."
}
```

## Guardrails

- **NEVER** fabricate TLE data or pass times if CelesTrak is unreachable (Rule R-001)
- **NEVER** extrapolate pass data beyond TLE epoch validity window (±7 days)
- Always include `data_source: "CelesTrak"` and `tle_epoch` in output (Rule R-004)
- If TLE epoch age > 7 days, attach accuracy degradation warning
- Pass times must be physically plausible: ISS orbital period ≈ 92.68 minutes
- Elevation values must be in [0°, 90°]; azimuth in [0°, 360°]

## Tool Access Requirements
- HTTP GET access to `celestrak.org` (TLE data)
- Python libraries: `skyfield`, `sgp4`
- JPL ephemeris file: `de421.bsp` (for sunlit calculations)
- Filesystem read/write for TLE cache
