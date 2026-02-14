"""
Geospatial and live-tracking services for mobile.
Status from recorded_at, Haversine distance, geofence inside/outside.
"""
from math import radians, sin, cos, sqrt, atan2

# Earth radius in meters (for Haversine)
EARTH_RADIUS_METERS = 6371000


def location_status_from_age_minutes(age_minutes: float) -> str:
    """
    Classify employee location status from age in minutes.
    active: < 5 min, recently_active: < 30 min, inactive: < 360 min, else not_registered.
    """
    if age_minutes < 5:
        return "active"
    if age_minutes < 30:
        return "recently_active"
    if age_minutes < 360:
        return "inactive"
    return "not_registered"


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two WGS84 points in meters (Haversine formula)."""
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


def is_inside_geofence(
    lat: float, lon: float,
    center_lat: float, center_lng: float,
    radius_meters: float,
) -> bool:
    """True if point (lat, lon) is inside the geofence circle."""
    return haversine_distance_meters(lat, lon, center_lat, center_lng) <= radius_meters
