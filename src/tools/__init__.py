"""
Space Operations Co-Pilot — Tools Package.

Re-exports tool functions for convenient imports.
"""

from src.tools.tle_fetcher import (
    TLEFetchError,
    TLEParseError,
    fetch_tle_by_name,
    fetch_tle_by_norad_id,
    parse_tle_response,
)
from src.tools.geocoder import GeocodingError, geocode_city
from src.tools.weather_fetcher import (
    WeatherFetchError,
    fetch_weather,
    get_weather_at_time,
)
from src.tools.visibility_classifier import (
    adjust_for_elevation,
    classify_visibility,
    compute_effective_cover,
    generate_recommendation,
    get_observation_likelihood,
)
from src.tools.pass_calculator import (
    PassCalculationError,
    compute_passes,
    get_satellite_position,
)
from src.tools.map_generator import generate_satellite_map, start_live_tracking

__all__ = [
    "TLEFetchError",
    "TLEParseError",
    "fetch_tle_by_name",
    "fetch_tle_by_norad_id",
    "parse_tle_response",
    "GeocodingError",
    "geocode_city",
    "WeatherFetchError",
    "fetch_weather",
    "get_weather_at_time",
    "adjust_for_elevation",
    "classify_visibility",
    "compute_effective_cover",
    "generate_recommendation",
    "get_observation_likelihood",
    "PassCalculationError",
    "compute_passes",
    "get_satellite_position",
    "generate_satellite_map",
]
