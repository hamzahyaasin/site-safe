"""Cameras on the site map (FR-33).

One row per known camera (assigned to a zone, named by a camera token, seen
live, or placed by an Admin): where it is and what it covers, whether its
live view is current, how many people it sees now, and its alerts. The map
draws placed cameras as a marker with a view cone; unplaced ones are listed
so an Admin can place them.
"""

from django.db.models import Count
from django.utils import timezone

from .models import Camera


def _placement(camera):
    if camera is None or not camera.is_placed:
        return None
    return {
        "latitude": camera.latitude,
        "longitude": camera.longitude,
        "heading": camera.heading,
        "field_of_view": camera.field_of_view,
        "view_range_m": camera.view_range_m,
    }


def _alerts(camera_ids):
    """camera_id -> number of open alerts, and camera_id -> its latest alert."""
    from alerts.models import Alert

    open_counts = dict(
        Alert.objects.filter(camera_id__in=camera_ids, is_resolved=False)
        .values_list("camera_id")
        .annotate(n=Count("id"))
    )
    latest = {}
    for camera_id in camera_ids:
        alert = (
            Alert.objects.filter(camera_id=camera_id)
            .order_by("-timestamp")
            .values("id", "alert_type", "severity", "timestamp", "is_resolved")
            .first()
        )
        if alert:
            latest[camera_id] = {**alert, "timestamp": alert["timestamp"].isoformat()}
    return open_counts, latest


def rows(camera_ids=None, now=None):
    """Map rows for every known camera, or only for ``camera_ids``."""
    from alerts import live
    from workers.location import count_stale_after

    now = now or timezone.now()
    listed = {row["camera_id"]: row for row in live.camera_list()}
    cameras = {c.camera_id: c for c in Camera.objects.all()}
    ids = sorted(set(listed) | set(cameras)) if camera_ids is None else sorted(camera_ids)
    open_counts, latest = _alerts(ids)
    out = []
    for camera_id in ids:
        base = listed.get(camera_id) or {"camera_id": camera_id, "zone": None, "live": False, "last_frame_at": None}
        camera = cameras.get(camera_id)
        fresh = camera is not None and camera.counted_at is not None and now - camera.counted_at <= count_stale_after()
        out.append(
            {
                **base,
                "people_in_view": camera.people_count if fresh else None,
                "counted_at": camera.counted_at.isoformat() if camera and camera.counted_at else None,
                "placement": _placement(camera),
                "open_alerts": open_counts.get(camera_id, 0),
                "last_alert": latest.get(camera_id),
            }
        )
    return out


def row(camera_id, now=None):
    return rows([camera_id], now=now)[0]
