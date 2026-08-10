from datetime import datetime, timezone

from app.models.position import VesselPosition
from app.services.validation import validate_position


def test_rejects_invalid_latitude() -> None:
    valid, reason = validate_position(
        VesselPosition(
            mmsi="230000001",
            latitude=120.0,
            longitude=24.0,
            timestamp=datetime.now(timezone.utc),
        )
    )

    assert valid is False
    assert reason is not None

