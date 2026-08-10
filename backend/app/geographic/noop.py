"""Initial geographic validator placeholder.

The first iteration does not ship a coastline dataset. This class keeps the
prediction model independent from geographic constraints so a land mask,
coastline intersection check, or route corridor validator can be added later.
"""

from __future__ import annotations

from app.models.position import PredictionPoint


class NoOpGeographicValidator:
    def is_water_coordinate(self, latitude: float, longitude: float) -> bool:
        return -90 <= latitude <= 90 and -180 <= longitude <= 180

    def validate_trajectory(self, points: list[PredictionPoint]) -> list[PredictionPoint]:
        return [point for point in points if self.is_water_coordinate(point.latitude, point.longitude)]

    def correct_trajectory(self, points: list[PredictionPoint]) -> list[PredictionPoint]:
        return self.validate_trajectory(points)

