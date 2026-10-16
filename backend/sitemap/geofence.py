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


RISK_ORDER = {"RESTRICTED": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def check_worker_zone(worker, lat, lng):
    """
    Return the active zone containing (lat, lng), or None.

    Where zones overlap, the highest-risk zone wins (then the smallest id), so
    a restricted area drawn inside a larger work zone is always detected.
    """
    from .models import Zone

    matches = [
        zone
        for zone in Zone.objects.filter(is_active=True)
        if point_in_polygon(lat, lng, zone.boundaries)
    ]
    if not matches:
        return None
    return max(matches, key=lambda z: (RISK_ORDER.get(z.risk_level, 0), -z.pk))
