"""
Space Operations Co-Pilot — Open-Meteo Geocoder.

Resolves city names to geographic coordinates using the
Open-Meteo Geocoding API (free, no API key required).
"""

from __future__ import annotations

import logging

import requests

from src.config.settings import API_TIMEOUT_SECONDS, OPENMETEO_GEOCODING_URL
from src.models.observer import ObserverLocation

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when a location name cannot be resolved to coordinates."""
    pass


def geocode_city(city_name: str) -> ObserverLocation:
    """Resolve a city name to an ObserverLocation with coordinates.

    Uses the Open-Meteo Geocoding API to find the best match.

    Args:
        city_name: City or locality name to resolve.

    Returns:
        ObserverLocation with latitude, longitude, elevation, timezone.

    Raises:
        GeocodingError: If the city cannot be resolved or API fails.
    """
    if not city_name or not city_name.strip():
        raise GeocodingError("City name cannot be empty")

    params = {
        "name": city_name.strip(),
        "count": 1,
        "language": "en",
        "format": "json",
    }

    logger.info("Weather & COMM Console: Geocoding '%s'", city_name)

    try:
        response = requests.get(
            OPENMETEO_GEOCODING_URL,
            params=params,
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        msg = (
            f"Geocoding request timed out after {API_TIMEOUT_SECONDS}s "
            f"for city '{city_name}'"
        )
        logger.error(msg)
        raise GeocodingError(msg)
    except requests.exceptions.RequestException as exc:
        msg = f"Geocoding request failed for city '{city_name}': {exc}"
        logger.error(msg)
        raise GeocodingError(msg)

    data = response.json()
    results = data.get("results", [])

    if not results:
        msg = (
            f'Could not resolve location "{city_name}" to geographic '
            f"coordinates. Please provide a recognized city name or "
            f"explicit latitude/longitude coordinates."
        )
        logger.warning(msg)
        raise GeocodingError(msg)

    best = results[0]
    observer = ObserverLocation(
        city=best.get("name", city_name),
        latitude=best["latitude"],
        longitude=best["longitude"],
        elevation_m=best.get("elevation", 0.0) or 0.0,
        timezone=best.get("timezone", "UTC"),
        country=best.get("country"),
    )

    logger.info(
        "Weather & COMM Console: Resolved '%s' → (%.4f, %.4f) %s",
        city_name,
        observer.latitude,
        observer.longitude,
        observer.country or "",
    )

    return observer
