"""
Space Operations Co-Pilot — Weather & COMM Console Agent.

Environmental assessment authority responsible for weather data
acquisition and visual observation feasibility classification.
Implements Weather Fallback Rule R-005.
"""

from __future__ import annotations

import logging
from datetime import datetime

from src.models.observer import ObserverLocation
from src.models.weather import WeatherResult
from src.tools.weather_fetcher import fetch_weather, get_weather_at_time

logger = logging.getLogger(__name__)


class EnvironmentalAgent:
    """Weather & COMM Console Agent.

    Fetches weather forecasts from Open-Meteo and classifies observation
    visibility for each satellite pass time. Applies R-005 fallback
    on API failure — never breaks the pipeline flow.
    """

    def assess_visibility(
        self,
        observer: ObserverLocation,
        pass_times_utc: list[datetime],
    ) -> dict:
        """Assess observation visibility for satellite pass times.

        Args:
            observer: Ground observer location.
            pass_times_utc: List of pass culmination times to check.

        Returns:
            WeatherResult as a dictionary.
        """
        logger.info(
            "Weather & COMM Console: Visibility assessment for %d pass(es) at %s",
            len(pass_times_utc),
            observer.city or f"({observer.latitude}, {observer.longitude})",
        )

        if not pass_times_utc:
            return WeatherResult(
                status="SUCCESS",
                data_source="Open-Meteo",
                observer=observer.to_dict(),
                reports=[],
            ).model_dump()

        # Fetch weather forecast from Open-Meteo
        weather_data = fetch_weather(
            latitude=observer.latitude,
            longitude=observer.longitude,
            forecast_days=3,
        )

        # Apply Weather Fallback Rule R-005 if API failed
        if weather_data is None:
            logger.warning(
                "Weather & COMM Console: Applying Weather Fallback Rule R-005"
            )
            return self._apply_fallback(observer, pass_times_utc)

        # Classify visibility for each pass time
        reports = []
        for pass_time in pass_times_utc:
            try:
                report = get_weather_at_time(weather_data, pass_time)
                reports.append(report)
            except Exception as exc:
                logger.warning(
                    "Weather & COMM Console: Failed to extract weather for %s: %s",
                    pass_time.isoformat(), exc,
                )
                # Individual time failure — continue with others
                continue

        result = WeatherResult(
            status="SUCCESS",
            data_source="Open-Meteo",
            observer=observer.to_dict(),
            reports=reports,
        )

        logger.info(
            "Weather & COMM Console: Visibility assessed for %d/%d pass(es)",
            len(reports), len(pass_times_utc),
        )

        return result.model_dump()

    def _apply_fallback(
        self,
        observer: ObserverLocation,
        pass_times_utc: list[datetime],
    ) -> dict:
        """Apply Weather Fallback Rule R-005.

        Assumes clear-sky conditions with a prominent telemetry notice.
        The pipeline continues without breaking — pass times are sacred (R-006).

        Args:
            observer: Ground observer location.
            pass_times_utc: List of pass times to generate fallback reports for.

        Returns:
            WeatherResult dictionary with FALLBACK_CLEAR_SKY source.
        """
        logger.warning(
            "Weather & COMM Console: R-005 FALLBACK — Assuming clear sky for %d pass(es)",
            len(pass_times_utc),
        )

        fallback = WeatherResult.fallback_result(pass_times_utc)
        fallback.observer = observer.to_dict()

        return fallback.model_dump()
