"""Trajectory prediction interface."""

from __future__ import annotations

from typing import Protocol

from app.geographic.base import GeographicValidator
from app.models.position import PredictionPoint, VesselPosition


class TrajectoryPredictor(Protocol):
    name: str

    def predict(
        self,
        history: list[VesselPosition],
        horizon_seconds: int,
        step_seconds: int,
        validator: GeographicValidator,
    ) -> list[PredictionPoint]:
        ...

