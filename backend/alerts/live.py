"""Live view relay: latest frame per camera, broadcast to /ws/cameras/.

Frames are disposable. The cache holds only each camera's newest frame for a
few seconds, so a page that opens late can show something at once; nothing
is written to the database or to disk. Every frame is sent to the
``live_cameras`` group, which only Safety Officer and Admin sockets join.

A websocket message is binary: the camera id, a newline, then the JPEG.
Camera ids are validated so they cannot contain a newline.
"""

import io
import re
import time
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.cache import cache

GROUP = "live_cameras"
REGISTRY_KEY = "live:cameras"
CAMERA_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
# Long enough for a page that opens a moment after the last frame.
FRAME_TTL_SECONDS = 30


class InvalidFrame(ValueError):
    pass


def frame_key(camera_id):
    return f"live:frame:{camera_id}"


def validate_frame(data):
    """Raise InvalidFrame unless ``data`` is a JPEG within the size limits.

    Only the image header is read (no full decode), which is enough to check
    the format and dimensions a few times a second per camera.
    """
    from PIL import Image, UnidentifiedImageError

    if not data:
        raise InvalidFrame("empty body")
    if len(data) > settings.LIVE_FRAME_MAX_BYTES:
        raise InvalidFrame(f"frame larger than {settings.LIVE_FRAME_MAX_BYTES // 1024} KB")
    if not data.startswith(b"\xff\xd8\xff"):
        raise InvalidFrame("not a JPEG")
    try:
        with Image.open(io.BytesIO(data)) as image:
            kind, size = image.format, image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidFrame("not a readable image") from exc
    if kind != "JPEG":
        raise InvalidFrame("not a JPEG")
    if max(size) > settings.LIVE_FRAME_MAX_SIDE:
        raise InvalidFrame(f"frame larger than {settings.LIVE_FRAME_MAX_SIDE} pixels on a side")


def too_soon(camera_id, now):
    """True if this camera already sent a frame within 1/LIVE_MAX_FPS seconds."""
    last = (cache.get(REGISTRY_KEY) or {}).get(camera_id)
    return last is not None and now - last < 1.0 / settings.LIVE_MAX_FPS


def publish(camera_id, jpeg, now=None):
    """Keep ``jpeg`` as the camera's latest frame and relay it to live viewers."""
    now = time.time() if now is None else now
    cache.set(frame_key(camera_id), (now, jpeg), FRAME_TTL_SECONDS)
    # Read-modify-write without a lock: a lost update only drops a camera from
    # the list until its next frame, a fraction of a second later.
    registry = cache.get(REGISTRY_KEY) or {}
    registry[camera_id] = now
    cache.set(REGISTRY_KEY, registry, None)
    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(GROUP, {"type": "camera.frame", "camera_id": camera_id, "jpeg": jpeg})


def last_seen():
    """camera_id -> unix time of its latest frame."""
    return dict(cache.get(REGISTRY_KEY) or {})


def latest_frame(camera_id):
    """The camera's newest JPEG still in the cache, or None."""
    hit = cache.get(frame_key(camera_id))
    return hit[1] if hit else None


def latest_frames():
    """(camera_id, jpeg) for every camera with a frame still in the cache."""
    out = []
    for camera_id in last_seen():
        hit = cache.get(frame_key(camera_id))
        if hit:
            out.append((camera_id, hit[1]))
    return out


def message(camera_id, jpeg):
    return camera_id.encode() + b"\n" + jpeg


def camera_list(now=None):
    """Every known camera: assigned to a zone, named by a camera token, or seen live."""
    from accounts.models import ServiceToken
    from sitemap.models import Zone

    now = time.time() if now is None else now
    zones = {}
    for zone in Zone.objects.filter(is_active=True).order_by("name"):
        for camera_id in zone.camera_ids or []:
            zones.setdefault(camera_id, zone.name)
    ids = set(zones)
    for camera_ids in ServiceToken.objects.filter(kind=ServiceToken.Kind.CAMERA, is_active=True).values_list(
        "camera_ids", flat=True
    ):
        ids.update(camera_ids or [])
    seen = last_seen()
    ids.update(seen)
    rows = []
    for camera_id in sorted(ids):
        at = seen.get(camera_id)
        rows.append(
            {
                "camera_id": camera_id,
                "zone": zones.get(camera_id),
                "live": at is not None and now - at <= settings.LIVE_OFFLINE_AFTER_SECONDS,
                "last_frame_at": datetime.fromtimestamp(at, tz=timezone.utc).isoformat() if at else None,
            }
        )
    return rows
