"""Internal normalized AIS domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(slots=True)
class VesselPosition:
    mmsi: str
    latitude: float
    longitude: float
    timestamp: datetime
    speed: float | None = None
    course: float | None = None
    heading: float | None = None
    vessel_name: str | None = None
    vessel_type: str | None = None
    source: str = "unknown"

    def normalized(self) -> "VesselPosition":
        return VesselPosition(
            mmsi=str(self.mmsi).strip(),
            latitude=float(self.latitude),
            longitude=float(self.longitude),
            timestamp=ensure_utc(self.timestamp),
            speed=None if self.speed is None else float(self.speed),
            course=None if self.course is None else float(self.course) % 360,
            heading=None if self.heading is None else float(self.heading) % 360,
            vessel_name=self.vessel_name.strip() if self.vessel_name else None,
            vessel_type=self.vessel_type.strip() if self.vessel_type else None,
            source=self.source,
        )


@dataclass(slots=True)
class PredictionPoint:
    latitude: float
    longitude: float
    timestamp: datetime
    seconds_ahead: int
    confidence: float

