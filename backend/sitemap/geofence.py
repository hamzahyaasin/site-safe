"""Geofencing helpers for zone boundary checks."""


def _normalize_vertex(point):
    if isinstance(point, dict):
        return float(point["lat"]), float(point["lng"])
    return float(point[0]), float(point[1])


def point_in_polygon(lat, lng, boundaries):
    """
    Ray-casting point-in-polygon test.

    boundaries: list of {lat, lng} dicts or [lat, lng] pairs (min 3 vertices).
    """
    if not boundaries or len(boundaries) < 3:
        return False

    x = float(lng)
    y = float(lat)
    inside = False
    n = len(boundaries)
    j = n - 1

    for i in range(n):
        yi, xi = _normalize_vertex(boundaries[i])
        yj, xj = _normalize_vertex(boundaries[j])

        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi
        if intersects:
            inside = not inside
        j = i

    return inside


def check_worker_zone(worker, lat, lng):
    """
    Check whether (lat, lng) falls inside any active zone polygon.
    Returns the first matching Zone, or None.
    """
    from .models import Zone

    for zone in Zone.objects.filter(is_active=True):
        if point_in_polygon(lat, lng, zone.boundaries):
            return zone
    return None
