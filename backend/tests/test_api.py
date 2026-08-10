import httpx
import pytest

from app.core.settings import Settings
from app.main import create_app


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
