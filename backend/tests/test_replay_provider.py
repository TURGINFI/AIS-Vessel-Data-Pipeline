import pytest

from app.providers.replay import ReplayAISProvider


@pytest.mark.asyncio
async def test_default_replay_sample_exposes_many_active_vessels() -> None:
    provider = ReplayAISProvider(
        data_path="data/sample/replay_ais.csv",
        speed_multiplier=30.0,
        loop=False,
    )

    positions = await provider.fetch_positions()

    assert len(positions) >= 20
    assert len({position.mmsi for position in positions}) == len(positions)
