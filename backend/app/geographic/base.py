"""Interface for water, coastline, and route corridor validation."""

from __future__ import annotations

from typing import Protocol

from app.models.position import PredictionPoint


class GeographicValidator(Protocol):
    def is_water_coordinate(self, latitude: float, longitude: float) -> bool:
        ...

    def validate_trajectory(self, points: list[PredictionPoint]) -> list[PredictionPoint]:
        ...

    def correct_trajectory(self, points: list[PredictionPoint]) -> list[PredictionPoint]:
        ...

