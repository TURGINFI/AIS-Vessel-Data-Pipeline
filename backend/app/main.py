"""FastAPI entrypoint for the AIS trajectory prediction backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.logging import configure_logging
from app.core.settings import Settings, get_settings
from app.geographic.noop import NoOpGeographicValidator
from app.ingestion.service import AISIngestionService
from app.prediction.constant_velocity import ConstantVelocityPredictor
from app.providers.factory import create_ais_provider
from app.services.repository import SQLiteVesselRepository
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = SQLiteVesselRepository(
            database_url=active_settings.database_url,
            history_window_minutes=active_settings.history_window_minutes,
            max_positions_per_vessel=active_settings.max_positions_per_vessel,
        )
        await repository.initialize()

        connection_manager = ConnectionManager()
        predictor = ConstantVelocityPredictor(max_speed_knots=active_settings.max_prediction_speed_knots)
        geographic_validator = NoOpGeographicValidator()

        app.state.settings = active_settings
        app.state.repository = repository
        app.state.connection_manager = connection_manager
        app.state.predictor = predictor
        app.state.geographic_validator = geographic_validator
        app.state.ingestion_service = None

        if active_settings.ingestion_enabled:
            provider = create_ais_provider(active_settings)
            ingestion_service = AISIngestionService(
                provider=provider,
                repository=repository,
                connection_manager=connection_manager,
            )
            app.state.ingestion_service = ingestion_service
            await ingestion_service.start()
            logger.info("ais_ingestion_started", extra={"provider": provider.name})

        yield

        ingestion_service = app.state.ingestion_service
        if ingestion_service is not None:
            await ingestion_service.stop()

    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        description="Lightweight AIS vessel tracking and trajectory prediction API.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()

