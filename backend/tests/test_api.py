from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.core.settings import Settings
from app.main import create_app
from app.models.position import VesselPosition


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    settings = Settings(
        ingestion_enabled=False,
        database_url="sqlite:///:memory:",
    )
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_vessels_endpoint_returns_every_latest_position() -> None:
    settings = Settings(
        ingestion_enabled=False,
        database_url="sqlite:///:memory:",
    )
    app = create_app(settings)
    expected_mmsis = {f"23000{index:04d}" for index in range(12)}

    async with app.router.lifespan_context(app):
        repository = app.state.repository
        now = datetime.now(timezone.utc)
        for index, mmsi in enumerate(sorted(expected_mmsis)):
            await repository.save_position(
                VesselPosition(
                    mmsi=mmsi,
                    latitude=59.8 + index * 0.01,
                    longitude=24.1 + index * 0.01,
                    timestamp=now + timedelta(seconds=index),
                    speed=10.0 + index,
                    course=90.0,
                    vessel_name=f"Test Vessel {index}",
                    source="test",
                )
            )

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/vessels")

    assert response.status_code == 200
    vessels = response.json()
    assert len(vessels) == len(expected_mmsis)
    assert {vessel["mmsi"] for vessel in vessels} == expected_mmsis
