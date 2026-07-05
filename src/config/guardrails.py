"""
Space Operations Co-Pilot — Input Validation & Guardrail Functions.

Implements Rules R-001 through R-008 input validation layer.
All user inputs are validated before dispatching to external APIs.
"""

from __future__ import annotations

import logging
import re

from src.config.settings import MAX_TIME_WINDOW_HOURS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# R-007: Coordinate Validation
# ---------------------------------------------------------------------------

def validate_coordinates(
    latitude: float,
    longitude: float,
) -> tuple[bool, str]:
    """Validate geographic coordinates are within valid ranges.

    Args:
        latitude: Observer latitude (-90 to 90).
        longitude: Observer longitude (-180 to 180).

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    errors: list[str] = []

    if not isinstance(latitude, (int, float)):
        errors.append(f"Latitude must be a number, got {type(latitude).__name__}")
    elif not -90.0 <= latitude <= 90.0:
        errors.append(
            f"Latitude must be between -90 and 90, got {latitude}"
        )

    if not isinstance(longitude, (int, float)):
        errors.append(f"Longitude must be a number, got {type(longitude).__name__}")
    elif not -180.0 <= longitude <= 180.0:
        errors.append(
            f"Longitude must be between -180 and 180, got {longitude}"
        )

    if errors:
        msg = "; ".join(errors)
        logger.warning("Coordinate validation failed: %s", msg)
        return False, msg

    return True, ""


# ---------------------------------------------------------------------------
# R-007: Time Window Validation
# ---------------------------------------------------------------------------

def validate_time_window(hours: int | float) -> tuple[int, str | None]:
    """Validate and cap the prediction time window.

    Args:
        hours: Requested time window in hours.

    Returns:
        Tuple of (capped_hours, notice_or_none).
        If capped, notice contains the user-facing message.
    """
    if not isinstance(hours, (int, float)) or hours <= 0:
        logger.warning("Invalid time window: %s, defaulting to 72 hours", hours)
        return 72, "Invalid time window specified. Using default of 72 hours."

    hours_int = int(hours)

    if hours_int > MAX_TIME_WINDOW_HOURS:
        notice = (
            f"ℹ️ Time window capped to {MAX_TIME_WINDOW_HOURS // 24} days "
            f"({MAX_TIME_WINDOW_HOURS} hours) for TLE accuracy. "
            f"Orbital predictions beyond 7 days from TLE epoch may have "
            f"reduced accuracy due to atmospheric drag uncertainty."
        )
        logger.info(
            "Time window capped from %d to %d hours", hours_int, MAX_TIME_WINDOW_HOURS
        )
        return MAX_TIME_WINDOW_HOURS, notice

    return hours_int, None


# ---------------------------------------------------------------------------
# TLE Line Validation
# ---------------------------------------------------------------------------

def tle_checksum(line: str) -> int:
    """Compute modulo-10 checksum for a TLE line.

    Args:
        line: A single TLE line (69 characters).

    Returns:
        The modulo-10 checksum digit (0–9).
    """
    total = 0
    for char in line[:68]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1
        # Letters, spaces, '.', '+' contribute 0
    return total % 10


def validate_tle_lines(line1: str, line2: str) -> tuple[bool, str]:
    """Validate a pair of TLE lines for format compliance.

    Checks:
    - Line 1 starts with '1 ' and is 69 characters
    - Line 2 starts with '2 ' and is 69 characters
    - NORAD catalog IDs match between lines
    - Modulo-10 checksums are valid

    Args:
        line1: TLE line 1.
        line2: TLE line 2.

    Returns:
        Tuple of (is_valid, error_message).
    """
    errors: list[str] = []

    # Strip trailing whitespace/newlines for validation
    l1 = line1.rstrip()
    l2 = line2.rstrip()

    # Line 1 format check
    if len(l1) != 69:
        errors.append(f"TLE Line 1 must be 69 characters, got {len(l1)}")
    if not l1.startswith("1 "):
        errors.append("TLE Line 1 must start with '1 '")

    # Line 2 format check
    if len(l2) != 69:
        errors.append(f"TLE Line 2 must be 69 characters, got {len(l2)}")
    if not l2.startswith("2 "):
        errors.append("TLE Line 2 must start with '2 '")

    if errors:
        return False, "; ".join(errors)

    # NORAD ID match
    norad_1 = l1[2:7].strip()
    norad_2 = l2[2:7].strip()
    if norad_1 != norad_2:
        errors.append(
            f"NORAD ID mismatch: Line 1 has '{norad_1}', Line 2 has '{norad_2}'"
        )

    # Checksum validation
    expected_cs1 = int(l1[68])
    actual_cs1 = tle_checksum(l1)
    if expected_cs1 != actual_cs1:
        errors.append(
            f"Line 1 checksum mismatch: expected {expected_cs1}, computed {actual_cs1}"
        )

    expected_cs2 = int(l2[68])
    actual_cs2 = tle_checksum(l2)
    if expected_cs2 != actual_cs2:
        errors.append(
            f"Line 2 checksum mismatch: expected {expected_cs2}, computed {actual_cs2}"
        )

    if errors:
        return False, "; ".join(errors)

    return True, ""


# ---------------------------------------------------------------------------
# Additional Validators
# ---------------------------------------------------------------------------

def validate_norad_id(norad_id: int) -> bool:
    """Check that a NORAD catalog ID is a valid positive integer."""
    return isinstance(norad_id, int) and norad_id > 0


def validate_elevation(deg: float) -> bool:
    """Check that elevation is within [0, 90] degrees."""
    return isinstance(deg, (int, float)) and 0.0 <= deg <= 90.0


def validate_azimuth(deg: float) -> bool:
    """Check that azimuth is within [0, 360] degrees."""
    return isinstance(deg, (int, float)) and 0.0 <= deg <= 360.0


def validate_cloud_cover(pct: float) -> bool:
    """Check that cloud cover percentage is within [0, 100]."""
    return isinstance(pct, (int, float)) and 0.0 <= pct <= 100.0
