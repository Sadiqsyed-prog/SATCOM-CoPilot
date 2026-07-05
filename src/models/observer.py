"""
Space Operations Co-Pilot — Observer Location Model.

Pydantic v2 model for ground-based observer positions.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.config.settings import (
    DEFAULT_CITY,
    DEFAULT_COUNTRY,
    DEFAULT_ELEVATION_M,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_TIMEZONE,
)


class ObserverLocation(BaseModel):
    """Ground-based observer location for satellite pass computation."""

    city: Optional[str] = Field(None, description="City or locality name")
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude in degrees"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in degrees"
    )
    elevation_m: float = Field(
        default=0.0, ge=0.0, description="Elevation above sea level in meters"
    )
    timezone: str = Field(default="UTC", description="IANA timezone identifier")
    country: Optional[str] = Field(None, description="Country name")

    @classmethod
    def default(cls) -> "ObserverLocation":
        """Return the system default observer location (Bengaluru, India)."""
        return cls(
            city=DEFAULT_CITY,
            latitude=DEFAULT_LATITUDE,
            longitude=DEFAULT_LONGITUDE,
            elevation_m=DEFAULT_ELEVATION_M,
            timezone=DEFAULT_TIMEZONE,
            country=DEFAULT_COUNTRY,
        )

    @classmethod
    def from_coordinates(
        cls,
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
    ) -> "ObserverLocation":
        """Create an observer from raw coordinates without city metadata."""
        return cls(
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary for inclusion in tracking results."""
        return {
            "city": self.city,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "timezone": self.timezone,
        }
