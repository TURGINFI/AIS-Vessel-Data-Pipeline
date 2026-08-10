from datetime import datetime, timedelta, timezone

from app.geographic.noop import NoOpGeographicValidator
from app.models.position import VesselPosition
from app.prediction.constant_velocity import ConstantVelocityPredictor


def test_constant_velocity_prediction_moves_north() -> None:
    now = datetime.now(timezone.utc)
    history = [
        VesselPosition(
            mmsi="230000001",
            latitude=60.0,
            longitude=24.0,
            timestamp=now - timedelta(minutes=1),
            speed=12.0,
            course=0.0,
        ),
        VesselPosition(
            mmsi="230000001",
            latitude=60.001,
            longitude=24.0,
            timestamp=now,
            speed=12.0,
            course=0.0,
        ),
    ]

    predictor = ConstantVelocityPredictor()
    points = predictor.predict(history, horizon_seconds=120, step_seconds=30, validator=NoOpGeographicValidator())

    assert len(points) == 4
    assert points[0].latitude > history[-1].latitude
    assert points[-1].latitude > points[0].latitude
    assert all(point.longitude == points[0].longitude for point in points)

