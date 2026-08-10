"""WebSocket connection manager for vessel updates."""

from __future__ import annotations

import logging

from fastapi import WebSocket

from app.models.position import VesselPosition
from app.schemas.vessel import VesselPositionSchema, WebSocketVesselMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("websocket_connection_established", extra={"clients": self.client_count})

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info("websocket_connection_closed", extra={"clients": self.client_count})

    async def broadcast_vessel_update(self, position: VesselPosition) -> None:
        if not self._connections:
            return
        message = WebSocketVesselMessage(
            data=VesselPositionSchema.from_domain(position),
        ).model_dump(mode="json")

        disconnected: list[WebSocket] = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(message)
            except RuntimeError:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

