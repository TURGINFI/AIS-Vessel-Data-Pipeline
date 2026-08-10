"""AIS message validation helpers."""

from __future__ import annotations

from app.models.position import VesselPosition


def validate_position(position: VesselPosition) -> tuple[bool, str | None]:
    if not position.mmsi:
        return False, "MMSI is required"
    if not position.mmsi.isdigit():
        return False, "MMSI must contain only digits"
    if not -90 <= position.latitude <= 90:
        return False, "latitude is outside the valid range"
    if not -180 <= position.longitude <= 180:
        return False, "longitude is outside the valid range"
    if position.speed is not None and position.speed < 0:
        return False, "speed cannot be negative"
    if position.course is not None and not 0 <= position.course < 360:
        return False, "course must be within 0 and 360 degrees"
    if position.heading is not None and not 0 <= position.heading < 360:
        return False, "heading must be within 0 and 360 degrees"
    return True, None

