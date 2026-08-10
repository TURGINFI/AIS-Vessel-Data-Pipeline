"""Continuous AIS ingestion pipeline."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.position import VesselPosition
from app.providers.base import AISProvider
from app.services.repository import VesselRepository
from app.services.validation import validate_position
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestionStats:
    provider: str
    running: bool = False
    received_messages: int = 0
    stored_messages: int = 0
    rejected_messages: int = 0
    last_message_at: datetime | None = None


class AISIngestionService:
    def __init__(
        self,
        provider: AISProvider,
        repository: VesselRepository,
        connection_manager: ConnectionManager,
        cleanup_interval_messages: int = 50,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.connection_manager = connection_manager
        self.cleanup_interval_messages = cleanup_interval_messages
        self.stats = IngestionStats(provider=provider.name)
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self.stats.running = True
        self._task = asyncio.create_task(self._run(), name="ais-ingestion")

    async def stop(self) -> None:
        self.stats.running = False
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("ais_ingestion_stopped", extra={"provider": self.provider.name})

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                async for raw_position in self.provider.subscribe_positions():
                    if self._stop_event.is_set():
                        break
                    await self._handle_position(raw_position)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "ais_reconnection_attempt",
                    extra={"provider": self.provider.name, "error": str(exc)},
                )
                await asyncio.sleep(5.0)

    async def _handle_position(self, raw_position: VesselPosition) -> None:
        self.stats.received_messages += 1
        position = raw_position.normalized()
        valid, reason = validate_position(position)
        if not valid:
            self.stats.rejected_messages += 1
            logger.warning(
                "invalid_message_rejected",
                extra={"provider": self.provider.name, "reason": reason, "mmsi": position.mmsi},
            )
            return

        stored = await self.repository.save_position(position)
        self.stats.last_message_at = datetime.now(timezone.utc)
        if stored:
            self.stats.stored_messages += 1
            await self.connection_manager.broadcast_vessel_update(position)

        if self.stats.received_messages % self.cleanup_interval_messages == 0:
            await self.repository.cleanup_history()
            logger.info(
                "vessel_state_updated",
                extra={
                    "provider": self.provider.name,
                    "received_messages": self.stats.received_messages,
                    "stored_messages": self.stats.stored_messages,
                },
            )

