"""Storage abstraction and SQLite implementation for vessel positions."""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from app.models.position import VesselPosition, ensure_utc


class VesselRepository(Protocol):
    async def initialize(self) -> None:
        ...

    async def save_position(self, position: VesselPosition) -> bool:
        ...

    async def list_latest_positions(self) -> list[VesselPosition]:
        ...

    async def get_latest_position(self, mmsi: str) -> VesselPosition | None:
        ...

    async def get_history(self, mmsi: str, limit: int | None = None) -> list[VesselPosition]:
        ...

    async def count_positions(self) -> int:
        ...

    async def count_vessels(self) -> int:
        ...

    async def cleanup_history(self) -> None:
        ...


class SQLiteVesselRepository:
    """SQLite-backed repository with local deduplication and latest-state cache."""

    def __init__(
        self,
        database_url: str,
        history_window_minutes: int,
        max_positions_per_vessel: int,
    ) -> None:
        self.database_path = self._database_path(database_url)
        self.history_window_minutes = history_window_minutes
        self.max_positions_per_vessel = max_positions_per_vessel
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _database_path(database_url: str) -> str:
        if database_url == "sqlite:///:memory:":
            return ":memory:"
        if database_url.startswith("sqlite:///"):
            return database_url.replace("sqlite:///", "", 1)
        raise ValueError("Only sqlite:/// database URLs are supported in this iteration")

    async def initialize(self) -> None:
        self._initialize_sync()

    def _initialize_sync(self) -> None:
        with self._lock:
            if self.database_path != ":memory:":
                Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mmsi TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    speed REAL,
                    course REAL,
                    heading REAL,
                    vessel_name TEXT,
                    vessel_type TEXT,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(mmsi, timestamp, latitude, longitude)
                );

                CREATE TABLE IF NOT EXISTS vessels (
                    mmsi TEXT PRIMARY KEY,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    speed REAL,
                    course REAL,
                    heading REAL,
                    vessel_name TEXT,
                    vessel_type TEXT,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_positions_mmsi_timestamp
                    ON positions (mmsi, timestamp DESC);
                """
            )
            self._connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Repository has not been initialized")
        return self._connection

    async def save_position(self, position: VesselPosition) -> bool:
        return self._save_position_sync(position.normalized())

    def _save_position_sync(self, position: VesselPosition) -> bool:
        timestamp = ensure_utc(position.timestamp).isoformat()
        with self._lock:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO positions (
                    mmsi, latitude, longitude, timestamp, speed, course, heading,
                    vessel_name, vessel_type, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.mmsi,
                    position.latitude,
                    position.longitude,
                    timestamp,
                    position.speed,
                    position.course,
                    position.heading,
                    position.vessel_name,
                    position.vessel_type,
                    position.source,
                ),
            )
            inserted = cursor.rowcount > 0

            latest = self.connection.execute(
                "SELECT timestamp FROM vessels WHERE mmsi = ?",
                (position.mmsi,),
            ).fetchone()
            if latest is None or timestamp >= latest["timestamp"]:
                self.connection.execute(
                    """
                    INSERT INTO vessels (
                        mmsi, latitude, longitude, timestamp, speed, course, heading,
                        vessel_name, vessel_type, source, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(mmsi) DO UPDATE SET
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        timestamp = excluded.timestamp,
                        speed = excluded.speed,
                        course = excluded.course,
                        heading = excluded.heading,
                        vessel_name = COALESCE(excluded.vessel_name, vessels.vessel_name),
                        vessel_type = COALESCE(excluded.vessel_type, vessels.vessel_type),
                        source = excluded.source,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        position.mmsi,
                        position.latitude,
                        position.longitude,
                        timestamp,
                        position.speed,
                        position.course,
                        position.heading,
                        position.vessel_name,
                        position.vessel_type,
                        position.source,
                    ),
                )
            self.connection.commit()
            return inserted

    async def list_latest_positions(self) -> list[VesselPosition]:
        return self._list_latest_positions_sync()

    def _list_latest_positions_sync(self) -> list[VesselPosition]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM vessels
                ORDER BY COALESCE(vessel_name, mmsi), mmsi
                """
            ).fetchall()
            return [self._row_to_position(row) for row in rows]

    async def get_latest_position(self, mmsi: str) -> VesselPosition | None:
        return self._get_latest_position_sync(mmsi)

    def _get_latest_position_sync(self, mmsi: str) -> VesselPosition | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM vessels WHERE mmsi = ?",
                (mmsi,),
            ).fetchone()
            return self._row_to_position(row) if row else None

    async def get_history(self, mmsi: str, limit: int | None = None) -> list[VesselPosition]:
        return self._get_history_sync(mmsi, limit)

    def _get_history_sync(self, mmsi: str, limit: int | None) -> list[VesselPosition]:
        query = """
            SELECT * FROM positions
            WHERE mmsi = ?
            ORDER BY timestamp DESC
        """
        params: tuple[object, ...]
        if limit is None:
            params = (mmsi,)
        else:
            query += " LIMIT ?"
            params = (mmsi, limit)

        with self._lock:
            rows = self.connection.execute(query, params).fetchall()
            return [self._row_to_position(row) for row in reversed(rows)]

    async def count_positions(self) -> int:
        return self._count_positions_sync()

    def _count_positions_sync(self) -> int:
        with self._lock:
            row = self.connection.execute("SELECT COUNT(*) AS count FROM positions").fetchone()
            return int(row["count"])

    async def count_vessels(self) -> int:
        return self._count_vessels_sync()

    def _count_vessels_sync(self) -> int:
        with self._lock:
            row = self.connection.execute("SELECT COUNT(*) AS count FROM vessels").fetchone()
            return int(row["count"])

    async def cleanup_history(self) -> None:
        self._cleanup_history_sync()

    def _cleanup_history_sync(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.history_window_minutes)
        cutoff_iso = cutoff.isoformat()
        with self._lock:
            self.connection.execute("DELETE FROM positions WHERE timestamp < ?", (cutoff_iso,))
            vessel_rows = self.connection.execute("SELECT DISTINCT mmsi FROM positions").fetchall()
            for row in vessel_rows:
                mmsi = row["mmsi"]
                self.connection.execute(
                    """
                    DELETE FROM positions
                    WHERE mmsi = ?
                      AND id NOT IN (
                          SELECT id FROM positions
                          WHERE mmsi = ?
                          ORDER BY timestamp DESC
                          LIMIT ?
                      )
                    """,
                    (mmsi, mmsi, self.max_positions_per_vessel),
                )
            self.connection.commit()

    @staticmethod
    def _row_to_position(row: sqlite3.Row) -> VesselPosition:
        return VesselPosition(
            mmsi=row["mmsi"],
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            speed=row["speed"],
            course=row["course"],
            heading=row["heading"],
            vessel_name=row["vessel_name"],
            vessel_type=row["vessel_type"],
            source=row["source"],
        )
