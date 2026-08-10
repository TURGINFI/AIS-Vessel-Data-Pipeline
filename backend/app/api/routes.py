"""REST and WebSocket API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.core.settings import Settings
from app.geographic.base import GeographicValidator
from app.ingestion.service import AISIngestionService
from app.prediction.base import TrajectoryPredictor
from app.schemas.vessel import (
    HealthResponseSchema,
    PredictionPointSchema,
    PredictionResponseSchema,
    SystemStatusSchema,
    VesselDetailSchema,
    VesselPositionSchema,
)
from app.services.repository import VesselRepository
from app.websocket.manager import ConnectionManager

api_router = APIRouter()


def repository_from_request(request: Request) -> VesselRepository:
    return request.app.state.repository


def settings_from_request(request: Request) -> Settings:
    return request.app.state.settings


def predictor_from_request(request: Request) -> TrajectoryPredictor:
    return request.app.state.predictor


def geographic_validator_from_request(request: Request) -> GeographicValidator:
    return request.app.state.geographic_validator


def ingestion_from_request(request: Request) -> AISIngestionService | None:
    return getattr(request.app.state, "ingestion_service", None)


def websocket_manager_from_request(request: Request) -> ConnectionManager:
    return request.app.state.connection_manager


@api_router.get("/api/health", response_model=HealthResponseSchema, tags=["system"])
async def health(request: Request) -> HealthResponseSchema:
    settings = settings_from_request(request)
    return HealthResponseSchema(status="ok", app=settings.app_name, version=settings.app_version)


@api_router.get("/api/vessels", response_model=list[VesselPositionSchema], tags=["vessels"])
async def list_vessels(request: Request) -> list[VesselPositionSchema]:
    repository = repository_from_request(request)
    vessels = await repository.list_latest_positions()
    return [VesselPositionSchema.from_domain(vessel) for vessel in vessels]


@api_router.get("/api/vessels/{mmsi}", response_model=VesselDetailSchema, tags=["vessels"])
async def get_vessel(request: Request, mmsi: str) -> VesselDetailSchema:
    repository = repository_from_request(request)
    latest = await repository.get_latest_position(mmsi)
    if latest is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    history = await repository.get_history(mmsi)
    return VesselDetailSchema(
        latest_position=VesselPositionSchema.from_domain(latest),
        history_count=len(history),
    )


@api_router.get("/api/vessels/{mmsi}/history", response_model=list[VesselPositionSchema], tags=["vessels"])
async def get_vessel_history(request: Request, mmsi: str, limit: int | None = None) -> list[VesselPositionSchema]:
    repository = repository_from_request(request)
    history = await repository.get_history(mmsi, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail="Vessel history not found")
    return [VesselPositionSchema.from_domain(position) for position in history]


@api_router.get("/api/vessels/{mmsi}/prediction", response_model=PredictionResponseSchema, tags=["prediction"])
async def get_vessel_prediction(request: Request, mmsi: str) -> PredictionResponseSchema:
    repository = repository_from_request(request)
    settings = settings_from_request(request)
    predictor = predictor_from_request(request)
    validator = geographic_validator_from_request(request)

    history = await repository.get_history(mmsi)
    if not history:
        raise HTTPException(status_code=404, detail="Vessel history not found")

    points = predictor.predict(
        history=history,
        horizon_seconds=settings.prediction_horizon_seconds,
        step_seconds=settings.prediction_step_seconds,
        validator=validator,
    )
    return PredictionResponseSchema(
        mmsi=mmsi,
        horizon_seconds=settings.prediction_horizon_seconds,
        step_seconds=settings.prediction_step_seconds,
        model=predictor.name,
        points=[PredictionPointSchema.from_domain(point) for point in points],
    )


@api_router.get("/api/system/status", response_model=SystemStatusSchema, tags=["system"])
async def get_system_status(request: Request) -> SystemStatusSchema:
    repository = repository_from_request(request)
    settings = settings_from_request(request)
    ingestion = ingestion_from_request(request)
    manager = websocket_manager_from_request(request)

    return SystemStatusSchema(
        provider=settings.ais_provider,
        ingestion_running=bool(ingestion and ingestion.stats.running),
        websocket_clients=manager.client_count,
        active_vessels=await repository.count_vessels(),
        stored_positions=await repository.count_positions(),
        received_messages=ingestion.stats.received_messages if ingestion else 0,
        stored_messages=ingestion.stats.stored_messages if ingestion else 0,
        rejected_messages=ingestion.stats.rejected_messages if ingestion else 0,
        last_message_at=ingestion.stats.last_message_at if ingestion else None,
        target_delay_seconds=10,
    )


@api_router.websocket("/ws/vessels")
async def vessel_websocket(websocket: WebSocket) -> None:
    manager: ConnectionManager = websocket.app.state.connection_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

