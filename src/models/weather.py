"""
Space Operations Co-Pilot — Weather & Visibility Models.

Pydantic v2 models and enums for weather classification,
cloud cover analysis, and observation feasibility reports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VisibilityClass(str, Enum):
    """Sky observation feasibility classification."""

    CLEAR = "CLEAR"
    MOSTLY_CLEAR = "MOSTLY_CLEAR"
    PARTIAL = "PARTIAL"
    MOSTLY_CLOUDY = "MOSTLY_CLOUDY"
    OBSTRUCTED = "OBSTRUCTED"


class CloudLayers(BaseModel):
    """Cloud cover breakdown by atmospheric layer."""

    low_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Low cloud cover % (stratus, <2 km)",
    )
    mid_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Mid cloud cover % (alto, 2-6 km)",
    )
    high_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="High cloud cover % (cirrus, >6 km)",
    )

    def effective_cover(self) -> float:
        """Compute effective cloud cover using layer impact factors.

        Formula: max(low×1.0, mid×0.8, high×0.4)
        Low clouds block fully, mid partially, high minimally.
        """
        return max(
            self.low_pct * 1.0,
            self.mid_pct * 0.8,
            self.high_pct * 0.4,
        )


class WeatherReport(BaseModel):
    """Weather assessment for a specific satellite pass time."""

    check_time_utc: datetime = Field(
        ..., description="Time this weather check applies to (UTC)"
    )
    cloud_cover_total_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Total sky cloud cover %"
    )
    cloud_layers: Optional[CloudLayers] = Field(
        None, description="Cloud cover breakdown by layer"
    )
    effective_cover_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0,
        description="Effective cloud cover after layer weighting",
    )
    visibility_class: VisibilityClass = Field(
        ..., description="Observation feasibility classification"
    )
    temperature_c: Optional[float] = Field(
        None, description="Surface temperature in °C"
    )
    humidity_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Relative humidity %"
    )
    visibility_m: Optional[float] = Field(
        None, ge=0.0, description="Horizontal visibility in meters"
    )
    recommendation: str = Field(
        ..., description="Human-readable observation recommendation"
    )
    observation_likelihood: str = Field(
        ..., description="Likelihood label (Excellent/Good/Possible/Unlikely/Very Unlikely)"
    )
    data_source: str = Field(
        default="Open-Meteo", description="Weather data source attribution (R-004)"
    )


class WeatherResult(BaseModel):
    """Complete result from the Weather & COMM Console."""

    status: str = Field(..., description="SUCCESS, ERROR, or FALLBACK")
    data_source: str = Field(
        default="Open-Meteo", description="Data origin attribution (R-004)"
    )
    observer: Optional[dict] = Field(
        None, description="Observer location details"
    )
    reports: list[WeatherReport] = Field(
        default_factory=list, description="Weather reports per pass time"
    )
    error_code: Optional[str] = Field(
        None, description="Error code if status is ERROR"
    )
    error_message: Optional[str] = Field(
        None, description="Human-readable error description"
    )

    @classmethod
    def fallback_result(
        cls,
        pass_times_utc: list[datetime] | None = None,
    ) -> "WeatherResult":
        """Create a Weather Fallback (Rule R-005) result.

        Assumes clear-sky conditions with a prominent telemetry notice.
        Used when the Open-Meteo API fails or times out.
        """
        fallback_notice = (
            "ℹ️ TELEMETRY NOTICE: Weather data temporarily unavailable. "
            "Assuming clear-sky conditions. Verify local weather independently "
            "before planning your observation session."
        )
        reports = []
        for t in (pass_times_utc or []):
            reports.append(
                WeatherReport(
                    check_time_utc=t,
                    cloud_cover_total_pct=0.0,
                    visibility_class=VisibilityClass.CLEAR,
                    recommendation=fallback_notice,
                    observation_likelihood="Unknown (weather data unavailable)",
                    data_source="FALLBACK_CLEAR_SKY",
                )
            )

        return cls(
            status="FALLBACK",
            data_source="FALLBACK_CLEAR_SKY",
            reports=reports,
        )
