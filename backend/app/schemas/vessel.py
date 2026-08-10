"""API response schemas for vessels and trajectory predictions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.position import PredictionPoint, VesselPosition


class VesselPositionSchema(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, position: VesselPosition) -> "VesselPositionSchema":
        return cls.model_validate(position)


class VesselDetailSchema(BaseModel):
    latest_position: VesselPositionSchema
    history_count: int


class PredictionPointSchema(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime
    seconds_ahead: int
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, point: PredictionPoint) -> "PredictionPointSchema":
        return cls.model_validate(point)


class PredictionResponseSchema(BaseModel):
    mmsi: str
    horizon_seconds: int
    step_seconds: int
    model: str
    points: list[PredictionPointSchema]


class HealthResponseSchema(BaseModel):
    status: str
    app: str
    version: str


class SystemStatusSchema(BaseModel):
    provider: str
    ingestion_running: bool
    websocket_clients: int
    active_vessels: int
    stored_positions: int
    received_messages: int
    stored_messages: int
    rejected_messages: int
    last_message_at: datetime | None
    target_delay_seconds: int


class WebSocketVesselMessage(BaseModel):
    type: str = "vessel_update"
    data: VesselPositionSchema

