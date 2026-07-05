# CelesTrak GP Data API Reference

## Base URL
```
https://celestrak.org/NORAD/elements/gp.php
```

## Query Methods

### By NORAD Catalog Number (Preferred)
```
GET /gp.php?CATNR={catalog_number}&FORMAT={format}
```
Example: `CATNR=25544&FORMAT=TLE` → ISS TLE data

### By Satellite Name
```
GET /gp.php?NAME={name}&FORMAT={format}
```
Example: `NAME=ISS&FORMAT=TLE` → Returns all matches containing "ISS"

### By International Designator
```
GET /gp.php?INTDES={designator}&FORMAT={format}
```
Example: `INTDES=1998-067A&FORMAT=TLE` → ISS by launch designator

### By Predefined Group
```
GET /gp.php?GROUP={group_name}&FORMAT={format}
```

| Group Name | Description | Approx Count |
|-----------|-------------|-------------|
| `stations` | Space stations (ISS, Tiangong, etc.) | ~15 |
| `visual` | Brightest satellites | ~200 |
| `active` | All active satellites | ~8000+ |
| `starlink` | SpaceX Starlink constellation | ~5000+ |
| `oneweb` | OneWeb constellation | ~600+ |
| `weather` | Weather satellites | ~50 |
| `science` | Scientific satellites | ~100 |
| `gps-ops` | GPS operational | ~31 |

## Format Options

| FORMAT Value | Content Type | Description |
|-------------|-------------|-------------|
| `TLE` or `3LE` | text/plain | 3-line format (name + 2 TLE lines) |
| `2LE` | text/plain | 2-line only (no name line) |
| `JSON` | application/json | OMM JSON format |
| `JSON-PRETTY` | application/json | Pretty-printed OMM JSON |
| `XML` | application/xml | OMM XML format |
| `KVN` | text/plain | OMM KVN format |
| `CSV` | text/csv | CSV format |

## JSON Response Format (OMM)

```json
[
  {
    "OBJECT_NAME": "ISS (ZARYA)",
    "OBJECT_ID": "1998-067A",
    "EPOCH": "2026-07-01T12:00:00.000000",
    "MEAN_MOTION": 15.48919755,
    "ECCENTRICITY": 0.00075,
    "INCLINATION": 51.64,
    "RA_OF_ASC_NODE": 200.1234,
    "ARG_OF_PERICENTER": 50.1234,
    "MEAN_ANOMALY": 310.5678,
    "EPHEMERIS_TYPE": 0,
    "CLASSIFICATION_TYPE": "U",
    "NORAD_CAT_ID": 25544,
    "ELEMENT_SET_NO": 999,
    "REV_AT_EPOCH": 12345,
    "BSTAR": 0.0001027,
    "MEAN_MOTION_DOT": 0.00016717,
    "MEAN_MOTION_DDOT": 0
  }
]
```

## Usage Guidelines

- **Update Frequency**: Data refreshed every ~2 hours by CelesTrak
- **Caching**: Cache locally for 4 hours; re-fetch on miss
- **Error Handling**: 
  - HTTP 200 with empty body = no matching satellite
  - HTTP 404 = invalid endpoint
  - HTTP 503 = service temporarily unavailable
- **Rate Limiting**: Be respectful; cache aggressively
- **Important**: CelesTrak is transitioning to 6-digit catalog numbers (Alpha-5).
  JSON format is recommended over fixed-width TLE for future compatibility.

## Common Satellite Quick Reference

| Satellite | NORAD ID | Query |
|----------|----------|-------|
| ISS | 25544 | `CATNR=25544` |
| Hubble (HST) | 20580 | `CATNR=20580` |
| Tiangong (CSS) | 48274 | `CATNR=48274` |
| GOES-16 | 41866 | `CATNR=41866` |
| Landsat 9 | 49260 | `CATNR=49260` |
