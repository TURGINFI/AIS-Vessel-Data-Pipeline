"""Provider interface for AIS position sources."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from app.models.position import VesselPosition


class AISProvider(Protocol):
    name: str

    async def fetch_positions(self) -> list[VesselPosition]:
        """Fetch a point-in-time batch of positions when polling is supported."""
        ...

    def subscribe_positions(self) -> AsyncIterator[VesselPosition]:
        """Stream positions as they arrive from the provider."""
        ...

