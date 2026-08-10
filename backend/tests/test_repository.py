from datetime import datetime, timezone

import pytest

from app.models.position import VesselPosition
from app.services.repository import SQLiteVesselRepository


@pytest.mark.asyncio
async def test_repository_deduplicates_positions() -> None:
    repository = SQLiteVesselRepository(
        database_url="sqlite:///:memory:",
        history_window_minutes=60,
        max_positions_per_vessel=100,
    )
    await repository.initialize()
    position = VesselPosition(
        mmsi="230000001",
        latitude=60.0,
        longitude=24.0,
        timestamp=datetime.now(timezone.utc),
        speed=10.0,
        course=90.0,
    )

    first_insert = await repository.save_position(position)
    second_insert = await repository.save_position(position)

    assert first_insert is True
    assert second_insert is False
    assert await repository.count_positions() == 1
    assert await repository.count_vessels() == 1

