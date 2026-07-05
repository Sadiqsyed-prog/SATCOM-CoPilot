# Space Operations Co-Pilot — Project Rules & Constraints

> **Codename**: SATCOM-CoPilot  
> **Classification**: Autonomous Satellite Trajectory & Observation Planning System  
> **Console Theme**: SpaceX Mission Control Nomenclature

---

## Agent Roster

| Console Designation | Skill Binding | Role |
|-------------------|--------------|------|
| **Flight Director (FD) Agent** | `copilot-router-skill` | Intent parsing, agent dispatch, response aggregation |
| **GNC Console Agent** | `satellite-tracker-skill` | TLE fetch, SGP4 propagation, pass window computation |
| **Weather & COMM Console Agent** | `weather-validator-skill` | Geocoding, weather forecast, visibility classification |
| **QA / Evaluation Agent** | `qa-evaluator-skill` | Schema validation, hallucination detection, rubric scoring |

---

## System Defaults

- **Default Satellite**: ISS (ZARYA) — NORAD ID `25544`
- **Default Location**: Bengaluru, Karnataka, India — `(12.9716°N, 77.5946°E, 920m ASL)`
- **Default Time Window**: 72 hours (3 days) from current UTC time
- **Minimum Elevation Threshold**: 10° above horizon

---

## Global Rules

### R-001: No Hallucinated Orbital Data
Agents must NEVER fabricate satellite positions, pass times, or orbital elements.
All orbital data must trace directly to a verified TLE source (CelesTrak) processed
through the SGP4/Skyfield propagation pipeline. If the data source is unreachable,
return an explicit `DATA_SOURCE_UNAVAILABLE` error — never approximate.

### R-002: No Hallucinated Weather Data
Weather reports must originate exclusively from the Open-Meteo API response.
If the API fails or times out, apply the **Weather Fallback Rule** (R-005).
Never generate plausible-sounding weather data from general knowledge.

### R-003: Graceful Degradation Over Silent Failure
Every external dependency failure must produce a structured, user-facing notice.
No unhandled exceptions may propagate to the user. Partial results are acceptable
when clearly annotated with what data is missing and why.

### R-004: Data Source Attribution
Every response must include a `data_source` field identifying the origin:
- `"CelesTrak"` — for orbital/TLE data
- `"Open-Meteo"` — for weather data
- `"Skyfield/SGP4"` — for computed pass windows
- `"UNAVAILABLE"` — when a source could not be reached

### R-005: Weather Fallback Rule
If the Open-Meteo API request fails or times out (>10 seconds):
1. Log a `WARNING`-level telemetry notice
2. Assume `"CLEAR"` sky conditions as fallback
3. Attach a prominent user-facing notice:
   ```
   ℹ️ TELEMETRY NOTICE: Weather data temporarily unavailable.
   Assuming clear-sky conditions. Verify local weather independently
   before planning your observation session.
   ```
4. Set `weather.data_source` to `"FALLBACK_CLEAR_SKY"`
5. Continue pipeline execution — do NOT break the flow

### R-006: Pass Times Are Sacred
Computed satellite pass windows must NEVER be suppressed or omitted due to
adverse weather conditions. Weather data is advisory overlay only. The user
always receives accurate pass timing regardless of cloud cover.

### R-007: Input Validation Before API Calls
All user inputs must be validated before dispatching to external APIs:
- Latitude: `[-90.0, 90.0]`
- Longitude: `[-180.0, 180.0]`
- Satellite name/NORAD ID: Must resolve against known catalog
- Time window: Must be positive, capped at 168 hours (7 days)

### R-008: Deterministic Testing
All BDD scenarios and unit tests must use hardcoded mock TLE data and weather
fixtures. Tests must NEVER depend on live network calls to pass. Integration
tests against live APIs are a separate, explicitly-tagged test suite.

---

## Technology Constraints

- **Python**: 3.10+
- **Orbital Mechanics**: `skyfield` + `sgp4` (no alternatives)
- **Weather**: Open-Meteo free tier (no API key required)
- **TLE Source**: CelesTrak GP data API
- **BDD Framework**: `behave` (Python Gherkin runner)
- **Testing**: `pytest` for unit/integration tests
- **No External LLM API calls** in the core pipeline — all computation is deterministic

---

## File Conventions

- All Python source files use `snake_case` naming
- All feature files use `snake_case.feature` naming
- Skill directories use `kebab-case` naming
- JSON fixtures use `snake_case.json` naming
- ISO 8601 timestamps in UTC for all datetime fields
- 4-space indentation in Python files
