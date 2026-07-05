"""
Space Operations Co-Pilot — GNC Console Agent (Space Mechanics).

Orbital mechanics authority responsible for TLE data acquisition
and satellite pass computation using the SGP4 propagation model.
"""

from __future__ import annotations

import logging
from datetime import datetime

from src.models.observer import ObserverLocation
from src.models.satellite import TrackingResult
from src.tools.pass_calculator import PassCalculationError, compute_passes, get_satellite_position
from src.tools.tle_fetcher import TLEFetchError, fetch_tle_by_norad_id

logger = logging.getLogger(__name__)


class SpaceMechanicsAgent:
    """GNC Console Agent — Guidance, Navigation, and Control.

    Fetches TLE data from CelesTrak and computes satellite pass windows
    using the Skyfield/SGP4 propagation pipeline. Never fabricates data.
    """

    def track_passes(
        self,
        satellite_name: str,
        norad_id: int,
        observer: ObserverLocation,
        time_window_hours: int = 72,
    ) -> dict:
        """Compute satellite pass windows over an observer location.

        Args:
            satellite_name: Official satellite catalog name.
            norad_id: NORAD catalog number.
            observer: Ground observer location.
            time_window_hours: Prediction window in hours.

        Returns:
            TrackingResult as a dictionary.
        """
        logger.info(
            "GNC Console: TRACK_PASS mission — %s (NORAD %d) over %s, %dh window",
            satellite_name, norad_id,
            observer.city or f"({observer.latitude}, {observer.longitude})",
            time_window_hours,
        )

        # Step 1: Fetch TLE data from CelesTrak
        try:
            tle_data = fetch_tle_by_norad_id(norad_id)
        except TLEFetchError as exc:
            logger.error("GNC Console: TLE fetch failed — %s", exc)
            return TrackingResult(
                status="ERROR",
                satellite=satellite_name,
                norad_id=norad_id,
                data_source="UNAVAILABLE",
                observer=observer.to_dict(),
                error_code="SATELLITE_NOT_FOUND" if "empty" in str(exc).lower() else "DATA_SOURCE_UNAVAILABLE",
                error_message=(
                    f"Unable to retrieve TLE data from CelesTrak for "
                    f"{satellite_name} (NORAD {norad_id}). "
                    f"Cannot provide orbital data without verified source data."
                ),
            ).model_dump()

        # Step 2: Compute pass windows via Skyfield/SGP4
        try:
            passes = compute_passes(
                tle_data=tle_data,
                observer=observer,
                time_window_hours=time_window_hours,
            )
        except PassCalculationError as exc:
            logger.error("GNC Console: Pass computation failed — %s", exc)
            return TrackingResult(
                status="ERROR",
                satellite=satellite_name,
                norad_id=norad_id,
                tle_epoch=tle_data.epoch,
                data_source="CelesTrak",
                observer=observer.to_dict(),
                error_code="COMPUTATION_FAILED",
                error_message=f"SGP4 pass computation failed: {exc}",
            ).model_dump()

        # Step 3: Build success result
        result = TrackingResult(
            status="SUCCESS",
            satellite=satellite_name,
            norad_id=norad_id,
            tle_epoch=tle_data.epoch,
            data_source="CelesTrak",
            computation_engine="Skyfield/SGP4",
            observer=observer.to_dict(),
            passes=passes,
        )

        logger.info(
            "GNC Console: Mission complete — %d pass(es) computed for %s",
            len(passes), satellite_name,
        )

        return result.model_dump()

    def get_position(
        self,
        satellite_name: str,
        norad_id: int,
        observer: ObserverLocation,
    ) -> dict:
        """Get current satellite position relative to observer.

        Args:
            satellite_name: Official satellite catalog name.
            norad_id: NORAD catalog number.
            observer: Ground observer location.

        Returns:
            Position data dictionary or error dictionary.
        """
        logger.info(
            "GNC Console: SATELLITE_POSITION mission — %s (NORAD %d)",
            satellite_name, norad_id,
        )

        try:
            tle_data = fetch_tle_by_norad_id(norad_id)
        except TLEFetchError as exc:
            logger.error("GNC Console: TLE fetch failed — %s", exc)
            return {
                "status": "ERROR",
                "satellite": satellite_name,
                "norad_id": norad_id,
                "data_source": "UNAVAILABLE",
                "error_code": "DATA_SOURCE_UNAVAILABLE",
                "error_message": str(exc),
            }

        try:
            position = get_satellite_position(tle_data, observer)
            return {
                "status": "SUCCESS",
                "satellite": satellite_name,
                "norad_id": norad_id,
                "data_source": "CelesTrak",
                "computation_engine": "Skyfield/SGP4",
                "position": position,
            }
        except PassCalculationError as exc:
            logger.error("GNC Console: Position computation failed — %s", exc)
            return {
                "status": "ERROR",
                "satellite": satellite_name,
                "norad_id": norad_id,
                "data_source": "CelesTrak",
                "error_code": "COMPUTATION_FAILED",
                "error_message": str(exc),
            }
