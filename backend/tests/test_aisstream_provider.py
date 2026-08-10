from datetime import timezone

from app.core.settings import Settings
from app.providers.aisstream import AISStreamProvider


def test_aisstream_normalizes_position_report() -> None:
    provider = AISStreamProvider(
        stream_url="wss://stream.aisstream.io/v0/stream",
        api_key="test-key",
        bounding_boxes=[[[-90.0, -180.0], [90.0, 180.0]]],
        filter_message_types=["PositionReport"],
        request_timeout_seconds=1.0,
        max_backoff_seconds=2.0,
    )

    position = provider.normalize_message(
        {
            "MessageType": "PositionReport",
            "MetaData": {
                "MMSI": 368207620,
                "ShipName": "EXAMPLE VESSEL      ",
                "latitude": 25.702,
                "longitude": -80.101,
                "time_utc": "2026-07-12 12:00:00.000000000 +0000 UTC",
            },
            "Message": {
                "PositionReport": {
                    "UserID": 368207620,
                    "Latitude": 25.702,
                    "Longitude": -80.101,
                    "Sog": 12.3,
                    "Cog": 180.5,
                    "TrueHeading": 181,
                }
            },
        }
    )

    assert position is not None
    assert position.mmsi == "368207620"
    assert position.vessel_name == "EXAMPLE VESSEL"
    assert position.latitude == 25.702
    assert position.longitude == -80.101
    assert position.speed == 12.3
    assert position.course == 180.5
    assert position.heading == 181
    assert position.timestamp.tzinfo == timezone.utc


def test_aisstream_uses_cached_static_data_for_positions() -> None:
    provider = AISStreamProvider(
        stream_url="wss://stream.aisstream.io/v0/stream",
        api_key="test-key",
        bounding_boxes=[[[-90.0, -180.0], [90.0, 180.0]]],
        filter_message_types=["PositionReport", "ShipStaticData"],
        request_timeout_seconds=1.0,
        max_backoff_seconds=2.0,
    )

    static_position = provider.normalize_message(
        {
            "MessageType": "ShipStaticData",
            "MetaData": {"MMSI_String": "230123456"},
            "Message": {"ShipStaticData": {"Name": "Baltic Aurora", "Type": 70}},
        }
    )
    position = provider.normalize_message(
        {
            "MessageType": "StandardClassBPositionReport",
            "MetaData": {"MMSI_String": "230123456", "time_utc": "2026-07-12T12:00:00Z"},
            "Message": {
                "StandardClassBPositionReport": {
                    "Latitude": 60.1,
                    "Longitude": 24.9,
                    "Sog": 8.5,
                    "Cog": 45.0,
                    "TrueHeading": 511,
                }
            },
        }
    )

    assert static_position is None
    assert position is not None
    assert position.vessel_name == "Baltic Aurora"
    assert position.vessel_type == "70"
    assert position.heading is None


def test_settings_parses_world_bounding_box() -> None:
    settings = Settings(ais_bounding_boxes="-90,-180,90,180")

    assert settings.ais_bounding_box_list == [[[-90.0, -180.0], [90.0, 180.0]]]
