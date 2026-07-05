"""
Space Operations Co-Pilot — CelesTrak TLE Data Fetcher.

Retrieves Two-Line Element sets from the CelesTrak GP data API
and parses them into validated TLEData models.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from src.config.guardrails import validate_tle_lines
from src.config.settings import API_TIMEOUT_SECONDS, CELESTRAK_BASE_URL
from src.models.satellite import TLEData

logger = logging.getLogger(__name__)


class TLEFetchError(Exception):
    """Raised when TLE data cannot be retrieved from CelesTrak."""
    pass


class TLEParseError(Exception):
    """Raised when TLE response text cannot be parsed."""
    pass


def fetch_tle_by_norad_id(norad_id: int) -> TLEData:
    """Fetch TLE data from CelesTrak by NORAD catalog number.

    Args:
        norad_id: NORAD catalog number (e.g., 25544 for ISS).

    Returns:
        Parsed TLEData object.

    Raises:
        TLEFetchError: If the API request fails or returns no data.
        TLEParseError: If the response cannot be parsed as valid TLE.
    """
    url = f"{CELESTRAK_BASE_URL}?CATNR={norad_id}&FORMAT=TLE"
    logger.info("GNC Console: Fetching TLE for NORAD ID %d from CelesTrak", norad_id)

    try:
        response = requests.get(url, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        msg = f"CelesTrak request timed out after {API_TIMEOUT_SECONDS}s for NORAD ID {norad_id}"
        logger.error(msg)
        raise TLEFetchError(msg)
    except requests.exceptions.RequestException as exc:
        msg = f"CelesTrak request failed for NORAD ID {norad_id}: {exc}"
        logger.error(msg)
        raise TLEFetchError(msg)

    text = response.text.strip()
    if not text:
        msg = f"CelesTrak returned empty response for NORAD ID {norad_id}"
        logger.warning(msg)
        raise TLEFetchError(msg)

    return parse_tle_response(text)


def fetch_tle_by_name(name: str) -> TLEData:
    """Fetch TLE data from CelesTrak by satellite name.

    Args:
        name: Satellite name to search for.

    Returns:
        Parsed TLEData object (first match if multiple).

    Raises:
        TLEFetchError: If the API request fails or no matching satellite found.
    """
    url = f"{CELESTRAK_BASE_URL}?NAME={name}&FORMAT=TLE"
    logger.info("GNC Console: Fetching TLE for satellite '%s' from CelesTrak", name)

    try:
        response = requests.get(url, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        msg = f"CelesTrak request timed out after {API_TIMEOUT_SECONDS}s for name '{name}'"
        logger.error(msg)
        raise TLEFetchError(msg)
    except requests.exceptions.RequestException as exc:
        msg = f"CelesTrak request failed for name '{name}': {exc}"
        logger.error(msg)
        raise TLEFetchError(msg)

    text = response.text.strip()
    if not text:
        msg = f"No satellite matching '{name}' found in CelesTrak catalog"
        logger.warning(msg)
        raise TLEFetchError(msg)

    return parse_tle_response(text)


def parse_tle_response(response_text: str) -> TLEData:
    """Parse a CelesTrak TLE response into a TLEData model.

    Expects 3-line format: satellite name + 2 TLE lines.

    Args:
        response_text: Raw text response from CelesTrak.

    Returns:
        Validated TLEData object.

    Raises:
        TLEParseError: If the text cannot be parsed as valid TLE.
    """
    lines = [line.rstrip() for line in response_text.strip().splitlines()]

    if len(lines) < 3:
        raise TLEParseError(
            f"Expected at least 3 lines in TLE response, got {len(lines)}"
        )

    # Take first satellite if multiple are returned
    line0 = lines[0].strip()  # Satellite name
    line1 = lines[1].strip()  # TLE Line 1
    line2 = lines[2].strip()  # TLE Line 2

    # Validate TLE format and checksum
    is_valid, error_msg = validate_tle_lines(line1, line2)
    if not is_valid:
        raise TLEParseError(f"TLE validation failed: {error_msg}")

    # Extract NORAD ID from Line 1
    norad_id = int(line1[2:7].strip())

    # Parse epoch
    epoch = _parse_tle_epoch(line1)

    logger.info(
        "GNC Console: TLE parsed — Satellite: %s, NORAD: %d, Epoch: %s",
        line0, norad_id, epoch.isoformat(),
    )

    return TLEData(
        line0=line0,
        line1=line1,
        line2=line2,
        epoch=epoch,
        norad_id=norad_id,
        source="CelesTrak",
    )


def _parse_tle_epoch(line1: str) -> datetime:
    """Extract the epoch datetime from TLE Line 1.

    TLE epoch format: YYDDD.DDDDDDDD (columns 19-32)
    YY = 2-digit year (00-56 → 2000-2056, 57-99 → 1957-1999)
    DDD.DDDDDDDD = day of year with fractional day

    Args:
        line1: TLE Line 1 string.

    Returns:
        Epoch as a timezone-aware UTC datetime.
    """
    epoch_str = line1[18:32].strip()
    year_2d = int(epoch_str[:2])
    year = 2000 + year_2d if year_2d < 57 else 1900 + year_2d
    day_of_year = float(epoch_str[2:])

    epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
        days=day_of_year - 1
    )
    return epoch
