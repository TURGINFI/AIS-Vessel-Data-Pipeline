"""Baseline constant-velocity trajectory predictor."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from app.geographic.base import GeographicValidator
from app.models.position import PredictionPoint, VesselPosition, ensure_utc
from app.prediction.geodesy import (
    KNOT_TO_METERS_PER_SECOND,
    destination_point,
    haversine_distance_meters,
    initial_bearing_degrees,
)


class ConstantVelocityPredictor:
    name = "constant_velocity"

    def __init__(self, max_speed_knots: float = 50.0) -> None:
        self.max_speed_knots = max_speed_knots

    def predict(
        self,
        history: list[VesselPosition],
        horizon_seconds: int,
        step_seconds: int,
        validator: GeographicValidator,
    ) -> list[PredictionPoint]:
        if not history or horizon_seconds <= 0 or step_seconds <= 0:
            return []

        ordered_history = sorted(history, key=lambda item: ensure_utc(item.timestamp))
        latest = ordered_history[-1].normalized()
        speed_knots = self._resolve_speed_knots(ordered_history)
        course_degrees = self._resolve_course_degrees(ordered_history)
        if speed_knots <= 0:
            return []

        speed_knots = float(np.clip(speed_knots, 0, self.max_speed_knots))
        speed_mps = speed_knots * KNOT_TO_METERS_PER_SECOND
        steps = np.arange(step_seconds, horizon_seconds + step_seconds, step_seconds, dtype=int)

        points: list[PredictionPoint] = []
        for seconds_ahead in steps:
            distance = float(speed_mps * int(seconds_ahead))
            latitude, longitude = destination_point(
                latest.latitude,
                latest.longitude,
                course_degrees,
                distance,
            )
            confidence = max(0.25, 1.0 - (int(seconds_ahead) / max(horizon_seconds, 1)) * 0.45)
            points.append(
                PredictionPoint(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=latest.timestamp + timedelta(seconds=int(seconds_ahead)),
                    seconds_ahead=int(seconds_ahead),
                    confidence=round(confidence, 3),
                )
            )

        return validator.correct_trajectory(points)

    def _resolve_speed_knots(self, history: list[VesselPosition]) -> float:
        latest_speed = history[-1].speed
        if latest_speed is not None and latest_speed > 0:
            return latest_speed
        if len(history) < 2:
            return 0.0

        previous = history[-2]
        latest = history[-1]
        delta_seconds = (ensure_utc(latest.timestamp) - ensure_utc(previous.timestamp)).total_seconds()
        if delta_seconds <= 0:
            return 0.0
        distance = haversine_distance_meters(
            previous.latitude,
            previous.longitude,
            latest.latitude,
            latest.longitude,
        )
        return distance / delta_seconds / KNOT_TO_METERS_PER_SECOND

    def _resolve_course_degrees(self, history: list[VesselPosition]) -> float:
        latest = history[-1]
        if latest.course is not None:
            return latest.course % 360
        if latest.heading is not None:
            return latest.heading % 360
        if len(history) >= 2:
            previous = history[-2]
            return initial_bearing_degrees(
                previous.latitude,
                previous.longitude,
                latest.latitude,
                latest.longitude,
            )
        return 0.0

