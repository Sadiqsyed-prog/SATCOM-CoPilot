"""
Space Operations Co-Pilot — Satellite & Orbital Data Models.

Pydantic v2 models for TLE data, pass windows, and tracking results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class TLEData(BaseModel):
    """Two-Line Element set parsed from CelesTrak response."""

    line0: str = Field(..., description="Satellite name line")
    line1: str = Field(..., description="TLE line 1 (69 characters)")
    line2: str = Field(..., description="TLE line 2 (69 characters)")
    epoch: Optional[datetime] = Field(None, description="TLE epoch timestamp (UTC)")
    norad_id: int = Field(..., description="NORAD catalog number")
    source: str = Field(default="CelesTrak", description="Data source attribution")


class PassWindow(BaseModel):
    """A single satellite pass event over an observer location."""

    pass_number: int = Field(..., ge=1, description="Sequential pass number")
    rise_utc: datetime = Field(..., description="Rise time above min elevation (UTC)")
    rise_azimuth_deg: float = Field(
        ..., ge=0.0, le=360.0, description="Azimuth at rise (degrees)"
    )
    culmination_utc: datetime = Field(
        ..., description="Maximum elevation time (UTC)"
    )
    max_elevation_deg: float = Field(
        ..., ge=0.0, le=90.0, description="Peak elevation (degrees)"
    )
    set_utc: datetime = Field(
        ..., description="Set time below min elevation (UTC)"
    )
    set_azimuth_deg: float = Field(
        ..., ge=0.0, le=360.0, description="Azimuth at set (degrees)"
    )
    is_sunlit: bool = Field(..., description="Whether satellite is sunlit")
    duration_seconds: int = Field(
        ..., ge=0, description="Pass duration in seconds"
    )
    visibility_rating: str = Field(
        default="GOOD", description="EXCELLENT / GOOD / LOW"
    )

    @model_validator(mode="after")
    def _check_chronological(self) -> "PassWindow":
        """Ensure rise < culmination < set."""
        if self.rise_utc >= self.culmination_utc:
            raise ValueError("culmination_utc must be after rise_utc")
        if self.culmination_utc >= self.set_utc:
            raise ValueError("set_utc must be after culmination_utc")
        return self


def compute_visibility_rating(max_elevation_deg: float) -> str:
    """Compute pass visibility rating from peak elevation.

    Args:
        max_elevation_deg: Maximum elevation above horizon in degrees.

    Returns:
        'EXCELLENT' (>45°), 'GOOD' (20-45°), or 'LOW' (<20°).
    """
    if max_elevation_deg > 45.0:
        return "EXCELLENT"
    elif max_elevation_deg >= 20.0:
        return "GOOD"
    else:
        return "LOW"


class SatelliteInfo(BaseModel):
    """Satellite identification metadata."""

    name: str = Field(..., description="Official satellite catalog name")
    norad_id: int = Field(..., gt=0, description="NORAD catalog number")
    aliases: list[str] = Field(
        default_factory=list, description="Known alternative names"
    )


class TrackingResult(BaseModel):
    """Complete result from the GNC Console pass tracking pipeline."""

    status: str = Field(..., description="SUCCESS or ERROR")
    satellite: str = Field(..., description="Official satellite name")
    norad_id: int = Field(..., description="NORAD catalog number")
    tle_epoch: Optional[datetime] = Field(
        None, description="TLE epoch timestamp (UTC)"
    )
    data_source: str = Field(
        default="CelesTrak", description="Data origin attribution (R-004)"
    )
    computation_engine: str = Field(
        default="Skyfield/SGP4", description="Propagation engine used"
    )
    observer: dict = Field(
        default_factory=dict, description="Observer location details"
    )
    passes: list[PassWindow] = Field(
        default_factory=list, description="Computed pass windows"
    )
    error_code: Optional[str] = Field(
        None, description="Error code if status is ERROR"
    )
    error_message: Optional[str] = Field(
        None, description="Human-readable error description"
    )
    notices: list[str] = Field(
        default_factory=list, description="Advisory notices"
    )
