"""Optional generic public AIS HTTP polling adapter.

This adapter is intentionally conservative. It requires an explicitly configured
public API URL, sends at most one request per configured interval, uses local
deduplication before yielding points, and backs off after upstream failures.
Different public AIS providers return different payloads, so this class accepts
common field aliases and should be specialized before production use.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx

from app.models.position import VesselPosition

logger = logging.getLogger(__name__)


class PublicAPIProvider:
    name = "public_api"

    def __init__(
        self,
        api_url: str,
        api_key: str | None,
        poll_interval: float,
        request_timeout_seconds: float,
        max_backoff_seconds: float,
    ) -> None:
        if not api_url:
            raise ValueError("AIS_API_URL is required when AIS_PROVIDER=public_api")
        self.api_url = api_url
        self.api_key = api_key
        self.poll_interval = max(poll_interval, 1.0)
        self.request_timeout_seconds = request_timeout_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self._seen_keys: set[tuple[str, str, float, float]] = set()

    async def fetch_positions(self) -> list[VesselPosition]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            response = await client.get(self.api_url, headers=headers)
            if response.status_code == 429:
                raise RateLimitError("Upstream AIS API rate limit reached")
            response.raise_for_status()
            payload = response.json()

        items = payload if isinstance(payload, list) else payload.get("data", [])
        return [self._normalize_item(item) for item in items if isinstance(item, dict)]

    async def subscribe_positions(self) -> AsyncIterator[VesselPosition]:
        backoff = self.poll_interval
        logger.info("ais_connection_established", extra={"provider": self.name})
        while True:
            try:
                positions = await self.fetch_positions()
                backoff = self.poll_interval
                for position in positions:
                    key = (
                        position.mmsi,
                        position.timestamp.isoformat(),
                        round(position.latitude, 6),
                        round(position.longitude, 6),
                    )
                    if key in self._seen_keys:
                        continue
                    self._seen_keys.add(key)
                    yield position
                await asyncio.sleep(self.poll_interval)
            except RateLimitError:
                logger.warning(
                    "ais_rate_limit_reached",
                    extra={"provider": self.name, "backoff_seconds": backoff},
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_seconds)
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning(
                    "ais_connection_lost",
                    extra={"provider": self.name, "error": str(exc), "backoff_seconds": backoff},
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_seconds)

    def _normalize_item(self, item: dict[str, Any]) -> VesselPosition:
        timestamp_value = _first_present(item, "timestamp", "time", "received_at", "last_update")
        timestamp = _parse_timestamp(timestamp_value)
        return VesselPosition(
            mmsi=str(_first_present(item, "mmsi", "MMSI")),
            latitude=float(_first_present(item, "latitude", "lat", "LAT")),
            longitude=float(_first_present(item, "longitude", "lon", "lng", "LON")),
            timestamp=timestamp,
            speed=_optional_float(_first_present(item, "speed", "sog", "SOG")),
            course=_optional_float(_first_present(item, "course", "cog", "COG")),
            heading=_optional_float(_first_present(item, "heading", "true_heading", "HEADING")),
            vessel_name=_optional_string(_first_present(item, "vessel_name", "name", "shipname")),
            vessel_type=_optional_string(_first_present(item, "vessel_type", "ship_type", "type")),
            source=self.name,
        )


class RateLimitError(Exception):
    """Raised when the upstream provider returns a rate-limit response."""


def _first_present(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    raise ValueError(f"Missing required AIS field. Tried: {', '.join(keys)}")


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip()

