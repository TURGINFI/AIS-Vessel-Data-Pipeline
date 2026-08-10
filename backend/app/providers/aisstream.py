"""AISStream WebSocket provider for public real-time AIS data."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import websockets

from app.models.position import VesselPosition

logger = logging.getLogger(__name__)

AISSTREAM_TIME_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d+))?\s+"
    r"(?P<offset>[+-]\d{2})(?P<offset_minutes>\d{2})$"
)


class AISStreamProvider:
    """Stream all vessels delivered by AISStream within configured bounding boxes.

    AISStream requires a free API key and a geographic subscription. This adapter
    intentionally does not send MMSI filters, so every vessel the provider emits
    inside the configured boxes flows through the normal ingestion pipeline.
    """

    name = "aisstream"

    def __init__(
        self,
        stream_url: str,
        api_key: str | None,
        bounding_boxes: list[list[list[float]]],
        filter_message_types: list[str],
        request_timeout_seconds: float,
        max_backoff_seconds: float,
    ) -> None:
        if not api_key:
            raise ValueError("AIS_API_KEY is required when AIS_PROVIDER=aisstream")
        if not bounding_boxes:
            raise ValueError("At least one AIS bounding box is required")

        self.stream_url = stream_url
        self.api_key = api_key
        self.bounding_boxes = bounding_boxes
        self.filter_message_types = filter_message_types
        self.request_timeout_seconds = request_timeout_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self._static_data_by_mmsi: dict[str, dict[str, str]] = {}

    async def fetch_positions(self) -> list[VesselPosition]:
        """AISStream is streaming-only, so point-in-time HTTP fetch is unsupported."""
        return []

    async def subscribe_positions(self) -> AsyncIterator[VesselPosition]:
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(
                    self.stream_url,
                    open_timeout=self.request_timeout_seconds,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                ) as websocket:
                    await websocket.send(json.dumps(self._subscription_payload()))
                    logger.info(
                        "ais_connection_established",
                        extra={
                            "provider": self.name,
                            "bounding_boxes": len(self.bounding_boxes),
                            "message_types": self.filter_message_types,
                        },
                    )
                    backoff = 1.0

                    async for raw_message in websocket:
                        position = self.normalize_message(raw_message)
                        if position is not None:
                            yield position
            except asyncio.CancelledError:
                raise
            except (OSError, websockets.WebSocketException, ValueError, json.JSONDecodeError) as exc:
                logger.warning(
                    "ais_connection_lost",
                    extra={"provider": self.name, "error": str(exc), "backoff_seconds": backoff},
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_seconds)

    def normalize_message(self, raw_message: str | bytes | dict[str, Any]) -> VesselPosition | None:
        envelope = self._load_envelope(raw_message)
        message_type = str(envelope.get("MessageType") or "")
        metadata = envelope.get("MetaData") if isinstance(envelope.get("MetaData"), dict) else {}
        payload = self._payload_for_type(envelope, message_type)

        if message_type == "ShipStaticData":
            self._remember_static_data(metadata, payload)
            return None

        latitude = _optional_float(_first_present(metadata, payload, "latitude", "Latitude", "LAT"))
        longitude = _optional_float(_first_present(metadata, payload, "longitude", "Longitude", "LON"))
        if latitude is None or longitude is None:
            return None

        mmsi = _optional_string(
            _first_present(metadata, payload, "MMSI_String", "MMSI", "UserID", "mmsi")
        )
        if not mmsi:
            return None

        static_data = self._static_data_by_mmsi.get(mmsi, {})
        vessel_name = _optional_string(
            _first_present(metadata, payload, "ShipName", "VesselName", "Name", "ship_name"),
        ) or static_data.get("vessel_name")
        vessel_type = _optional_string(
            _first_present(metadata, payload, "ShipType", "Type", "VesselType", "vessel_type"),
        ) or static_data.get("vessel_type")

        return VesselPosition(
            mmsi=mmsi,
            latitude=latitude,
            longitude=longitude,
            timestamp=_parse_timestamp(
                _first_present(metadata, payload, "time_utc", "TimeUTC", "Timestamp", "timestamp")
            ),
            speed=_optional_float(_first_present(payload, metadata, "Sog", "SOG", "SpeedOverGround", "speed")),
            course=_optional_float(_first_present(payload, metadata, "Cog", "COG", "CourseOverGround", "course")),
            heading=_normalize_heading(
                _optional_float(_first_present(payload, metadata, "TrueHeading", "Heading", "heading"))
            ),
            vessel_name=vessel_name,
            vessel_type=vessel_type,
            source=self.name,
        )

    def _subscription_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "APIKey": self.api_key,
            "BoundingBoxes": self.bounding_boxes,
        }
        if self.filter_message_types:
            payload["FilterMessageTypes"] = self.filter_message_types
        return payload

    @staticmethod
    def _load_envelope(raw_message: str | bytes | dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw_message, dict):
            return raw_message
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8")
        envelope = json.loads(raw_message)
        if not isinstance(envelope, dict):
            raise ValueError("AISStream message envelope must be an object")
        return envelope

    @staticmethod
    def _payload_for_type(envelope: dict[str, Any], message_type: str) -> dict[str, Any]:
        message = envelope.get("Message")
        if not isinstance(message, dict):
            return {}
        payload = message.get(message_type)
        if isinstance(payload, dict):
            return payload
        if len(message) == 1:
            only_value = next(iter(message.values()))
            if isinstance(only_value, dict):
                return only_value
        return {}

    def _remember_static_data(self, metadata: dict[str, Any], payload: dict[str, Any]) -> None:
        mmsi = _optional_string(
            _first_present(metadata, payload, "MMSI_String", "MMSI", "UserID", "mmsi")
        )
        if not mmsi:
            return
        vessel_name = _optional_string(
            _first_present(metadata, payload, "ShipName", "VesselName", "Name", "ship_name")
        )
        vessel_type = _optional_string(
            _first_present(metadata, payload, "ShipType", "Type", "VesselType", "vessel_type")
        )
        if vessel_name or vessel_type:
            self._static_data_by_mmsi[mmsi] = {
                "vessel_name": vessel_name or "",
                "vessel_type": vessel_type or "",
            }


def _first_present(first: dict[str, Any], second: dict[str, Any], *keys: str) -> Any:
    for item in (first, second):
        for key in keys:
            if key in item and item[key] not in (None, ""):
                return item[key]
    return None


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if value in (None, ""):
        return datetime.now(timezone.utc)

    text = str(value).strip().replace(" UTC", "").replace("Z", "+00:00")
    match = AISSTREAM_TIME_PATTERN.match(text)
    if match:
        fraction = (match.group("fraction") or "0")[:6].ljust(6, "0")
        offset = f"{match.group('offset')}:{match.group('offset_minutes')}"
        text = f"{match.group('date')}T{match.group('time')}.{fraction}{offset}"
    else:
        text = text.replace(" ", "T", 1)

    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_heading(value: float | None) -> float | None:
    if value is None or value < 0 or value >= 360:
        return None
    return value


def _optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None
