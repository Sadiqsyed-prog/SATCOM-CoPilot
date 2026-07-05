"""
Space Operations Co-Pilot — System Configuration & Constants.

Centralizes all API endpoints, default values, satellite aliases,
visibility thresholds, and operational parameters.
"""

# ---------------------------------------------------------------------------
# External API Endpoints
# ---------------------------------------------------------------------------

CELESTRAK_BASE_URL: str = "https://celestrak.org/NORAD/elements/gp.php"
"""CelesTrak General Perturbations (GP) data API base URL."""

OPENMETEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
"""Open-Meteo weather forecast API endpoint."""

OPENMETEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
"""Open-Meteo geocoding API endpoint (city → coordinates)."""

# ---------------------------------------------------------------------------
# Default Satellite (Rule: ISS if unspecified)
# ---------------------------------------------------------------------------

DEFAULT_SATELLITE_NAME: str = "ISS (ZARYA)"
DEFAULT_NORAD_ID: int = 25544

# ---------------------------------------------------------------------------
# Default Observer Location (Bengaluru, Karnataka, India)
# ---------------------------------------------------------------------------

DEFAULT_LATITUDE: float = 12.9716
DEFAULT_LONGITUDE: float = 77.5946
DEFAULT_ELEVATION_M: float = 920.0
DEFAULT_CITY: str = "Bengaluru"
DEFAULT_COUNTRY: str = "India"
DEFAULT_TIMEZONE: str = "Asia/Kolkata"

# ---------------------------------------------------------------------------
# Operational Parameters
# ---------------------------------------------------------------------------

DEFAULT_TIME_WINDOW_HOURS: int = 72
"""Default prediction window: 3 days."""

MAX_TIME_WINDOW_HOURS: int = 168
"""Maximum prediction window: 7 days (R-007 cap)."""

MIN_ELEVATION_DEG: float = 10.0
"""Minimum elevation above horizon to consider a pass visible."""

API_TIMEOUT_SECONDS: int = 10
"""HTTP request timeout for all external APIs."""

TLE_CACHE_TTL_HOURS: int = 4
"""Time-to-live for cached TLE data (CelesTrak updates ~every 2 hours)."""

TLE_MAX_AGE_DAYS: int = 7
"""Maximum TLE epoch age before accuracy warning is attached."""

# ---------------------------------------------------------------------------
# Satellite Alias Dictionary
# ---------------------------------------------------------------------------

SATELLITE_ALIASES: dict[str, tuple[str, int]] = {
    # Key: lowercase alias → Value: (official_name, norad_id)
    "iss": ("ISS (ZARYA)", 25544),
    "international space station": ("ISS (ZARYA)", 25544),
    "space station": ("ISS (ZARYA)", 25544),
    "zarya": ("ISS (ZARYA)", 25544),
    "hubble": ("HST", 20580),
    "hst": ("HST", 20580),
    "hubble telescope": ("HST", 20580),
    "hubble space telescope": ("HST", 20580),
    "tiangong": ("CSS (TIANHE)", 48274),
    "chinese space station": ("CSS (TIANHE)", 48274),
    "css": ("CSS (TIANHE)", 48274),
    "tianhe": ("CSS (TIANHE)", 48274),
    "goes-16": ("GOES 16", 41866),
    "goes east": ("GOES 16", 41866),
    "goes 16": ("GOES 16", 41866),
    "landsat 9": ("LANDSAT 9", 49260),
    "landsat": ("LANDSAT 9", 49260),
}

# ---------------------------------------------------------------------------
# Visibility Classification Thresholds
# ---------------------------------------------------------------------------

VISIBILITY_THRESHOLDS: dict[str, tuple[int, int]] = {
    "CLEAR": (0, 25),
    "MOSTLY_CLEAR": (26, 50),
    "PARTIAL": (51, 75),
    "MOSTLY_CLOUDY": (76, 90),
    "OBSTRUCTED": (91, 100),
}
"""Maps VisibilityClass name → (min_pct, max_pct) of cloud cover."""

# ---------------------------------------------------------------------------
# Cloud Layer Impact Factors (for layered analysis)
# ---------------------------------------------------------------------------

CLOUD_LAYER_FACTORS: dict[str, float] = {
    "low": 1.0,   # Dense stratus clouds (<2 km) — fully block
    "mid": 0.8,   # Alto clouds (2–6 km) — moderate blocking
    "high": 0.4,  # Cirrus clouds (>6 km) — thin, partial blocking
}

# ---------------------------------------------------------------------------
# Time Window Resolution (NL → hours)
# ---------------------------------------------------------------------------

TIME_WINDOW_KEYWORDS: dict[str, int] = {
    "tonight": 12,
    "today": 24,
    "tomorrow": 24,
    "this week": 168,
    "next week": 168,
}

# ---------------------------------------------------------------------------
# Open-Meteo Hourly Variables for Satellite Observation
# ---------------------------------------------------------------------------

OPENMETEO_HOURLY_VARS: str = (
    "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,"
    "temperature_2m,relative_humidity_2m,visibility,weather_code"
)
