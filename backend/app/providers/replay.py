"""Replay provider for deterministic local AIS demos."""

from __future__ import annotations

import asyncio
import csv
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.models.position import VesselPosition

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReplayRecord:
    simulation_second: float
    mmsi: str
    latitude: float
    longitude: float
    speed: float | None
    course: float | None
    heading: float | None
    vessel_name: str | None
    vessel_type: str | None


class ReplayAISProvider:
    name = "replay"

    def __init__(
        self,
        data_path: str,
        speed_multiplier: float = 30.0,
        loop: bool = True,
    ) -> None:
        self.data_path = Path(data_path)
        self.speed_multiplier = max(speed_multiplier, 0.1)
        self.loop = loop
        self._records = self._load_records()

    async def fetch_positions(self) -> list[VesselPosition]:
        latest_by_mmsi: dict[str, ReplayRecord] = {}
        for record in self._records:
            latest_by_mmsi[record.mmsi] = record
        now = datetime.now(timezone.utc)
        return [self._to_position(record, now) for record in latest_by_mmsi.values()]

    async def subscribe_positions(self) -> AsyncIterator[VesselPosition]:
        logger.info(
            "ais_connection_established",
            extra={"provider": self.name, "records": len(self._records)},
        )
        while True:
            previous_second = self._records[0].simulation_second
            for record in self._records:
                delay = (record.simulation_second - previous_second) / self.speed_multiplier
                if delay > 0:
                    await asyncio.sleep(delay)
                previous_second = record.simulation_second
                yield self._to_position(record, datetime.now(timezone.utc))
            if not self.loop:
                break
            await asyncio.sleep(1.0)

    def _load_records(self) -> list[ReplayRecord]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Replay AIS data file not found: {self.data_path}")

        with self.data_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            records = [self._parse_record(row) for row in reader]

        if not records:
            raise ValueError(f"Replay AIS data file is empty: {self.data_path}")

        return sorted(records, key=lambda row: (row.simulation_second, row.mmsi))

    @staticmethod
    def _parse_record(row: dict[str, str]) -> ReplayRecord:
        return ReplayRecord(
            simulation_second=float(row["simulation_second"]),
            mmsi=row["mmsi"].strip(),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            speed=_optional_float(row.get("speed")),
            course=_optional_float(row.get("course")),
            heading=_optional_float(row.get("heading")),
            vessel_name=_optional_string(row.get("vessel_name")),
            vessel_type=_optional_string(row.get("vessel_type")),
        )

    @staticmethod
    def _to_position(record: ReplayRecord, timestamp: datetime) -> VesselPosition:
        return VesselPosition(
            mmsi=record.mmsi,
            latitude=record.latitude,
            longitude=record.longitude,
            timestamp=timestamp,
            speed=record.speed,
            course=record.course,
            heading=record.heading,
            vessel_name=record.vessel_name,
            vessel_type=record.vessel_type,
            source="replay",
        )


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

