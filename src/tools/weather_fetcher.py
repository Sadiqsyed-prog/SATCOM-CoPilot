"""
Space Operations Co-Pilot — Open-Meteo Weather Fetcher.

Retrieves hourly weather forecasts from the Open-Meteo API
and extracts conditions at specific satellite pass times.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from src.config.settings import (
    API_TIMEOUT_SECONDS,
    OPENMETEO_FORECAST_URL,
    OPENMETEO_HOURLY_VARS,
)
from src.models.weather import CloudLayers, VisibilityClass, WeatherReport
from src.tools.visibility_classifier import classify_visibility, compute_effective_cover

logger = logging.getLogger(__name__)


class WeatherFetchError(Exception):
    """Raised when weather data cannot be retrieved from Open-Meteo."""
    pass


def fetch_weather(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
) -> dict | None:
    """Fetch hourly weather forecast from Open-Meteo.

    Args:
        latitude: Observer latitude.
        longitude: Observer longitude.
        forecast_days: Number of forecast days (1-16).

    Returns:
        Raw API response dict, or None on failure (caller applies R-005).
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": OPENMETEO_HOURLY_VARS,
        "timezone": "UTC",
        "forecast_days": forecast_days,
    }

    logger.info(
        "Weather & COMM Console: Fetching %d-day forecast for (%.4f, %.4f)",
        forecast_days, latitude, longitude,
    )

    try:
        response = requests.get(
            OPENMETEO_FORECAST_URL,
            params=params,
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Weather & COMM Console: Forecast received successfully")
        return data

    except requests.exceptions.Timeout:
        logger.warning(
            "Weather & COMM Console: Open-Meteo request timed out after %ds — "
            "applying Weather Fallback Rule R-005",
            API_TIMEOUT_SECONDS,
        )
        return None

    except requests.exceptions.RequestException as exc:
        logger.warning(
            "Weather & COMM Console: Open-Meteo request failed (%s) — "
            "applying Weather Fallback Rule R-005",
            exc,
        )
        return None


def get_weather_at_time(
    weather_data: dict,
    target_time_utc: datetime,
) -> WeatherReport:
    """Extract weather conditions for a specific time from hourly data.

    Finds the nearest hourly data point to the target time.

    Args:
        weather_data: Raw Open-Meteo API response dict.
        target_time_utc: Target time to check weather for.

    Returns:
        WeatherReport for the nearest hour to target_time.
    """
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])
    cloud_cover = hourly.get("cloud_cover", [])
    cloud_low = hourly.get("cloud_cover_low", [])
    cloud_mid = hourly.get("cloud_cover_mid", [])
    cloud_high = hourly.get("cloud_cover_high", [])
    temperatures = hourly.get("temperature_2m", [])
    humidity = hourly.get("relative_humidity_2m", [])
    visibility = hourly.get("visibility", [])

    if not times:
        raise WeatherFetchError("Weather data contains no hourly time entries")

    # Find nearest hourly index to target time
    target_str = target_time_utc.strftime("%Y-%m-%dT%H:00")
    best_idx = 0
    best_delta = float("inf")

    for i, t_str in enumerate(times):
        try:
            t = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
            delta = abs((t - target_time_utc).total_seconds())
            if delta < best_delta:
                best_delta = delta
                best_idx = i
        except (ValueError, TypeError):
            continue

    # Extract values at the nearest index
    idx = best_idx
    total_cover = _safe_get(cloud_cover, idx, 0.0)

    cloud_layers = CloudLayers(
        low_pct=_safe_get(cloud_low, idx, 0.0),
        mid_pct=_safe_get(cloud_mid, idx, 0.0),
        high_pct=_safe_get(cloud_high, idx, 0.0),
    )

    eff_cover = compute_effective_cover(cloud_layers)
    vis_class = classify_visibility(eff_cover)

    from src.tools.visibility_classifier import (
        generate_recommendation,
        get_observation_likelihood,
    )

    return WeatherReport(
        check_time_utc=target_time_utc,
        cloud_cover_total_pct=total_cover,
        cloud_layers=cloud_layers,
        effective_cover_pct=eff_cover,
        visibility_class=vis_class,
        temperature_c=_safe_get(temperatures, idx, None),
        humidity_pct=_safe_get(humidity, idx, None),
        visibility_m=_safe_get(visibility, idx, None),
        recommendation=generate_recommendation(vis_class, total_cover),
        observation_likelihood=get_observation_likelihood(vis_class),
        data_source="Open-Meteo",
    )


def _safe_get(lst: list, idx: int, default=None):
    """Safely get an element from a list by index."""
    try:
        val = lst[idx]
        return val if val is not None else default
    except (IndexError, TypeError):
        return default
