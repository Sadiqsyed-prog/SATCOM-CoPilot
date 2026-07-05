"""
Space Operations Co-Pilot — Skyfield/SGP4 Pass Calculator.

Computes satellite pass windows (rise/culminate/set events)
over an observer location using the SGP4 propagation model
via the Skyfield astronomical library.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from skyfield.api import EarthSatellite, load, wgs84

from src.models.observer import ObserverLocation
from src.models.satellite import PassWindow, TLEData, compute_visibility_rating

logger = logging.getLogger(__name__)


class PassCalculationError(Exception):
    """Raised when satellite pass computation fails."""
    pass


@lru_cache(maxsize=1)
def _load_timescale():
    """Load and cache the Skyfield timescale (downloads leap-second data)."""
    return load.timescale()


@lru_cache(maxsize=1)
def _load_ephemeris():
    """Load and cache the JPL ephemeris for Sun position calculations."""
    return load("de421.bsp")


def az_el_to_human_readable(azimuth_deg: float, elevation_deg: float) -> tuple[str, str]:
    """Translate azimuth and elevation into human-readable compass and sky directions.
    
    Returns:
        Tuple of (compass_direction, sky_position)
    """
    compass_dirs = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West", "North"]
    idx = round(azimuth_deg / 45.0) % 8
    compass = compass_dirs[idx]

    if elevation_deg < 0:
        sky = "Below the horizon"
    elif elevation_deg < 20:
        sky = "Low on the horizon"
    elif elevation_deg < 45:
        sky = "Mid-sky"
    elif elevation_deg < 75:
        sky = "High in the sky"
    else:
        sky = "High overhead, near the zenith"

    return compass, sky


def compute_passes(
    tle_data: TLEData,
    observer: ObserverLocation,
    time_window_hours: int = 72,
    min_elevation_deg: float = 10.0,
) -> list[PassWindow]:
    """Compute satellite passes visible from an observer location.

    Uses Skyfield's find_events() to locate rise/culminate/set triplets,
    then computes azimuth, sunlit status, and visibility rating for each.

    Args:
        tle_data: Validated TLE data for the target satellite.
        observer: Observer ground location.
        time_window_hours: Prediction window in hours from now.
        min_elevation_deg: Minimum elevation above horizon (degrees).

    Returns:
        List of PassWindow objects sorted by rise_utc.

    Raises:
        PassCalculationError: If Skyfield computation fails.
    """
    try:
        ts = _load_timescale()
        eph = _load_ephemeris()

        # Build satellite object from TLE lines
        satellite = EarthSatellite(
            tle_data.line1, tle_data.line2, tle_data.line0, ts
        )

        # Build observer position
        observer_pos = wgs84.latlon(
            observer.latitude,
            observer.longitude,
            elevation_m=observer.elevation_m,
        )

        # Define time window
        t0 = ts.now()
        t1 = ts.tt_jd(t0.tt + time_window_hours / 24.0)

        logger.info(
            "GNC Console: Computing passes for '%s' over (%.4f, %.4f) "
            "for %dh window, min elevation %.1f°",
            tle_data.line0,
            observer.latitude,
            observer.longitude,
            time_window_hours,
            min_elevation_deg,
        )

        # Find pass events: 0=rise, 1=culminate, 2=set
        t_events, events = satellite.find_events(
            observer_pos, t0, t1, altitude_degrees=min_elevation_deg
        )

        if len(t_events) == 0:
            logger.info("GNC Console: No passes found in the specified window")
            return []

        # Group events into rise/culminate/set triplets
        passes: list[PassWindow] = []
        pass_number = 0
        i = 0

        while i < len(events):
            # Find a complete rise(0) → culminate(1) → set(2) triplet
            if events[i] != 0:
                i += 1
                continue

            # Look for the full triplet
            if i + 2 >= len(events):
                break
            if events[i] != 0 or events[i + 1] != 1 or events[i + 2] != 2:
                i += 1
                continue

            t_rise = t_events[i]
            t_culm = t_events[i + 1]
            t_set = t_events[i + 2]

            # Compute topocentric positions for azimuth/elevation
            diff = satellite - observer_pos

            # Rise azimuth
            rise_topo = diff.at(t_rise)
            rise_alt, rise_az, _ = rise_topo.altaz()

            # Culmination elevation
            culm_topo = diff.at(t_culm)
            culm_alt, culm_az, _ = culm_topo.altaz()

            # Set azimuth
            set_topo = diff.at(t_set)
            set_alt, set_az, _ = set_topo.altaz()

            # Check if satellite is sunlit at culmination
            is_sunlit = bool(satellite.at(t_culm).is_sunlit(eph))

            # Compute duration
            rise_dt = t_rise.utc_datetime()
            set_dt = t_set.utc_datetime()
            duration = int((set_dt - rise_dt).total_seconds())

            max_elev = culm_alt.degrees
            rating = compute_visibility_rating(max_elev)

            pass_number += 1
            passes.append(
                PassWindow(
                    pass_number=pass_number,
                    rise_utc=rise_dt.replace(tzinfo=timezone.utc),
                    rise_azimuth_deg=round(rise_az.degrees, 1),
                    culmination_utc=t_culm.utc_datetime().replace(
                        tzinfo=timezone.utc
                    ),
                    max_elevation_deg=round(max_elev, 1),
                    set_utc=set_dt.replace(tzinfo=timezone.utc),
                    set_azimuth_deg=round(set_az.degrees, 1),
                    is_sunlit=is_sunlit,
                    duration_seconds=duration,
                    visibility_rating=rating,
                )
            )

            i += 3  # Move past this triplet

        logger.info(
            "GNC Console: Found %d pass(es) for '%s'",
            len(passes),
            tle_data.line0,
        )

        return sorted(passes, key=lambda p: p.rise_utc)

    except Exception as exc:
        msg = f"Pass computation failed for '{tle_data.line0}': {exc}"
        logger.error("GNC Console: %s", msg)
        raise PassCalculationError(msg) from exc


def get_satellite_position(
    tle_data: TLEData,
    observer: ObserverLocation,
) -> dict:
    """Get the current topocentric position of a satellite.

    Args:
        tle_data: Validated TLE data for the target satellite.
        observer: Observer ground location.

    Returns:
        Dictionary with altitude, azimuth, distance, and is_sunlit.

    Raises:
        PassCalculationError: If computation fails.
    """
    try:
        ts = _load_timescale()
        eph = _load_ephemeris()

        satellite = EarthSatellite(
            tle_data.line1, tle_data.line2, tle_data.line0, ts
        )
        observer_pos = wgs84.latlon(
            observer.latitude,
            observer.longitude,
            elevation_m=observer.elevation_m,
        )

        t = ts.now()
        diff = satellite - observer_pos
        topocentric = diff.at(t)
        alt, az, distance = topocentric.altaz()

        is_sunlit = bool(satellite.at(t).is_sunlit(eph))

        # Add live telemetry: Lat, Long, Altitude (km), Speed (km/h)
        subpoint = satellite.at(t).subpoint()
        lat = subpoint.latitude.degrees
        lon = subpoint.longitude.degrees
        alt_km = subpoint.elevation.km

        velocity_vector = satellite.at(t).velocity.km_per_s
        import math
        speed_kmps = math.sqrt(velocity_vector[0]**2 + velocity_vector[1]**2 + velocity_vector[2]**2)
        speed_kmh = speed_kmps * 3600

        compass, sky = az_el_to_human_readable(az.degrees, alt.degrees)

        return {
            "timestamp_utc": t.utc_datetime().replace(tzinfo=timezone.utc).isoformat(),
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "altitude_km": round(alt_km, 1),
            "speed_kmh": round(speed_kmh, 1),
            "altitude_deg": round(alt.degrees, 2),
            "azimuth_deg": round(az.degrees, 2),
            "compass_direction": compass,
            "sky_position": sky,
            "distance_km": round(distance.km, 1),
            "is_sunlit": is_sunlit,
            "is_above_horizon": alt.degrees > 0,
            "data_source": "Skyfield/SGP4",
        }

    except Exception as exc:
        msg = f"Position computation failed for '{tle_data.line0}': {exc}"
        logger.error("GNC Console: %s", msg)
        raise PassCalculationError(msg) from exc
