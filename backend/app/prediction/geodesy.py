"""Small geodesic helpers for short-term trajectory projection."""

from __future__ import annotations

import math

EARTH_RADIUS_METERS = 6_371_000.0
KNOT_TO_METERS_PER_SECOND = 0.514444


def destination_point(
    latitude: float,
    longitude: float,
    bearing_degrees: float,
    distance_meters: float,
) -> tuple[float, float]:
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    bearing = math.radians(bearing_degrees)
    angular_distance = distance_meters / EARTH_RADIUS_METERS

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    normalized_lon = (math.degrees(lon2) + 540) % 360 - 180
    return math.degrees(lat2), normalized_lon


def haversine_distance_meters(
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
) -> float:
    start_lat = math.radians(start_latitude)
    end_lat = math.radians(end_latitude)
    delta_lat = math.radians(end_latitude - start_latitude)
    delta_lon = math.radians(end_longitude - start_longitude)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(start_lat) * math.cos(end_lat) * math.sin(delta_lon / 2) ** 2
    )
    return EARTH_RADIUS_METERS * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def initial_bearing_degrees(
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
) -> float:
    start_lat = math.radians(start_latitude)
    end_lat = math.radians(end_latitude)
    delta_lon = math.radians(end_longitude - start_longitude)
    x = math.sin(delta_lon) * math.cos(end_lat)
    y = math.cos(start_lat) * math.sin(end_lat) - math.sin(start_lat) * math.cos(end_lat) * math.cos(delta_lon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

