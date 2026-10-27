"""Where workers are and how many people each zone holds (FR-31).

Two sources place a worker:

* **Camera:** a QR badge sighting by a camera puts the worker in that
  camera's zone (each camera belongs to at most one zone). Cameras report
  sightings every 15 s; the location is current for
  ``CAMERA_PRESENCE_SECONDS`` after the last one, then the worker is "last
  seen" there and the presence monitor records the zone exit, dated to that
  sighting.
* **Vest GPS:** a position report places the worker in the zone that
  contains it, current while the vest is online. While a camera sighting is
  current it takes precedence: GPS near a zone edge cannot move a worker a
  camera has just seen elsewhere.

Each placement updates the worker's last known location (``location_*``)
and, when the zone changes, writes ZONE_EXIT/ZONE_ENTER activity logs, so
timelines and reports show zone visits from both sources.

A zone's head count combines what cameras see with who is placed there.
Each camera reports how many people are in its view. If the zone's cameras
can see the same people (``camera_views_overlap``), the largest single count
is used, which never double-counts; otherwise the counts are added. The head
count is the larger of that and the number of identified workers currently
placed in the zone, so a worker seen by both a camera and a vest is counted
once.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import ActivityLog, Worker

CAMERA = "camera"
VEST = "vest"


def camera_presence():
    return timedelta(seconds=settings.CAMERA_PRESENCE_SECONDS)


def count_stale_after():
    return timedelta(seconds=settings.CAMERA_COUNT_STALE_SECONDS)


def is_current(worker, now=None):
    """Whether the worker's last known location still describes where they are."""
    if worker.location_at is None:
        return False
    now = now or timezone.now()
    if worker.location_source == VEST:
        from .presence import is_vest_online

        return is_vest_online(getattr(worker, "smart_vest", None), now)
    return now - worker.location_at <= camera_presence()


def current_zone_ids(now=None):
    """{worker_id: zone_id} for active workers currently placed in a zone."""
    from .presence import offline_after

    now = now or timezone.now()
    placed = Worker.objects.filter(is_active=True, location_zone__isnull=False)
    by_camera = placed.filter(location_source=CAMERA, location_at__gte=now - camera_presence())
    by_vest = placed.filter(location_source=VEST, smart_vest__last_seen__gte=now - offline_after())
    out = dict(by_camera.values_list("pk", "location_zone_id"))
    out.update(by_vest.values_list("pk", "location_zone_id"))
    return out


def _log_zone_change(worker, old_zone, new_zone, when, metadata):
    if old_zone == new_zone:
        return False
    if old_zone is not None:
        ActivityLog.objects.create(
            worker=worker, action=ActivityLog.Action.ZONE_EXIT, zone=old_zone, timestamp=when, metadata=metadata
        )
    if new_zone is not None:
        ActivityLog.objects.create(
            worker=worker, action=ActivityLog.Action.ZONE_ENTER, zone=new_zone, timestamp=when, metadata=metadata
        )
    return new_zone is not None


def _open_zone(worker):
    """The zone of the worker's latest zone log if it is an entry, else None."""
    last = (
        ActivityLog.objects.filter(
            worker=worker, action__in=[ActivityLog.Action.ZONE_ENTER, ActivityLog.Action.ZONE_EXIT]
        )
        .select_related("zone")
        .first()
    )
    return last.zone if last and last.action == ActivityLog.Action.ZONE_ENTER else None


def place(worker, zone, when, source, device, metadata=None):
    """Record that ``source`` (CAMERA or VEST) placed ``worker`` in ``zone`` at ``when``.

    Returns ``(entered, previous_zone)``: ``entered`` is True when ``zone``
    was just entered. Late observations (older than the stored location) and
    GPS that disagrees with a current camera sighting do not move the worker.
    """
    with transaction.atomic():
        worker = Worker.objects.select_for_update().get(pk=worker.pk)
        if worker.location_at is not None and when < worker.location_at:
            return False, None
        if (
            source == VEST
            and worker.location_source == CAMERA
            and when - worker.location_at <= camera_presence()
        ):
            return False, None
        previous = _open_zone(worker)
        worker.location_zone = zone
        worker.location_at = when
        worker.location_source = source
        worker.location_device = device[:64]
        worker.save(update_fields=["location_zone", "location_at", "location_source", "location_device"])
        meta = {"source": f"{source} {device}", **(metadata or {})}
        entered = _log_zone_change(worker, previous, zone, when, meta)
    return entered, previous


def zone_occupancy(zone, now=None, present=None, cameras=None):
    """Head count of ``zone`` with how it was worked out.

    ``present`` ({worker_id: zone_id}) and ``cameras`` ({camera_id: Camera}
    with a fresh count) can be passed in when many zones are counted at once.
    """
    from sitemap.models import Camera

    now = now or timezone.now()
    if present is None:
        present = current_zone_ids(now)
    if cameras is None:
        cameras = {
            c.camera_id: c
            for c in Camera.objects.filter(camera_id__in=zone.camera_ids or [], counted_at__gte=now - count_stale_after())
        }
    identified = sum(1 for z in present.values() if z == zone.pk)
    counts = [cameras[c].people_count for c in zone.camera_ids or [] if c in cameras]
    if counts:
        method = "max" if zone.camera_views_overlap else "sum"
        camera_count = max(counts) if zone.camera_views_overlap else sum(counts)
    else:
        method, camera_count = None, None
    return {
        "count": max(identified, camera_count or 0),
        "identified": identified,
        "camera_count": camera_count,
        "cameras_reporting": len(counts),
        "cameras_assigned": len(zone.camera_ids or []),
        "method": method,
    }


def fresh_cameras(now=None):
    """{camera_id: Camera} for every camera whose people count is still current."""
    from sitemap.models import Camera

    now = now or timezone.now()
    return {c.camera_id: c for c in Camera.objects.filter(counted_at__gte=now - count_stale_after())}


def check_capacity(zone, now=None, worker=None, source=None, camera_id="", location=None):
    """Raise one ZONE_BREACH per over-capacity period of ``zone``; returns it, or None.

    A head count is a noisy reading, so this uses hysteresis: the zone must
    be over ``max_occupancy`` for ``ZONE_CAPACITY_CONFIRM_SECONDS`` before
    the alert, and back within it for ``ZONE_CAPACITY_CLEAR_SECONDS`` before
    another period can start. A brief spike that never confirmed is simply
    forgotten. Called on every count change and by the presence monitor.
    """
    from alerts.models import Alert, AlertSource, AlertType, Severity
    from alerts.rules import rule_for
    from sitemap.models import Zone

    now = now or timezone.now()
    confirm = timedelta(seconds=settings.ZONE_CAPACITY_CONFIRM_SECONDS)
    clear = timedelta(seconds=settings.ZONE_CAPACITY_CLEAR_SECONDS)
    with transaction.atomic():
        zone = Zone.objects.select_for_update().get(pk=zone.pk)
        count = zone_occupancy(zone, now)["count"]
        over = zone.max_occupancy > 0 and count > zone.max_occupancy
        fields = {}
        if over:
            if zone.within_capacity_since is not None:
                fields["within_capacity_since"] = None
            if zone.over_capacity_since is None:
                fields["over_capacity_since"] = now
        elif zone.capacity_alerted_at is not None:
            if zone.within_capacity_since is None:
                fields["within_capacity_since"] = now
            elif now - zone.within_capacity_since >= clear:
                fields.update(over_capacity_since=None, capacity_alerted_at=None, within_capacity_since=None)
        elif zone.over_capacity_since is not None:
            fields["over_capacity_since"] = None  # a spike that never confirmed
        for name, value in fields.items():
            setattr(zone, name, value)
        alert = None
        if (
            over
            and zone.capacity_alerted_at is None
            and now - zone.over_capacity_since >= confirm
            and rule_for(AlertType.ZONE_BREACH, zone).is_enabled
        ):
            zone.capacity_alerted_at = now
            fields["capacity_alerted_at"] = now
            alert = Alert.objects.create(
                worker=worker,
                alert_type=AlertType.ZONE_BREACH,
                severity=Severity.MEDIUM,
                source=source or AlertSource.AI_CAMERA,
                camera_id=camera_id,
                location=location,
                description=f"{zone.name} over capacity: {count} present, limit {zone.max_occupancy}",
            )
        if fields:
            zone.save(update_fields=list(fields))
    return alert


def restricted_breach(worker, zone, source, camera_id="", location=None, seen_by=""):
    """ZONE_BREACH when an identified worker enters a restricted zone they are not assigned to."""
    from alerts.models import Alert, AlertType, Severity
    from alerts.rules import rule_for
    from sitemap.models import Zone

    if zone.risk_level != Zone.RiskLevel.RESTRICTED or worker.zone_id == zone.pk:
        return None
    if not rule_for(AlertType.ZONE_BREACH, zone).is_enabled:
        return None
    suffix = f" (seen by {seen_by})" if seen_by else ""
    return Alert.objects.create(
        worker=worker,
        alert_type=AlertType.ZONE_BREACH,
        severity=Severity.HIGH,
        source=source,
        camera_id=camera_id,
        location=location,
        description=f"Entered restricted zone {zone.name} without assignment{suffix}",
    )


def sweep_camera_exits(now=None):
    """Record the zone exit of camera-placed workers no longer seen. Returns the zones affected."""
    now = now or timezone.now()
    stale = Worker.objects.filter(
        location_source=CAMERA, location_zone__isnull=False, location_at__lt=now - camera_presence()
    ).select_related("location_zone")
    zones = set()
    for worker in stale:
        if _open_zone(worker) == worker.location_zone:
            ActivityLog.objects.create(
                worker=worker,
                action=ActivityLog.Action.ZONE_EXIT,
                zone=worker.location_zone,
                timestamp=worker.location_at,
                metadata={"source": f"{CAMERA} {worker.location_device}", "reason": "not seen"},
            )
            zones.add(worker.location_zone)
    return zones


def place_by_camera(worker, camera_id, when):
    """A camera read ``worker``'s badge at ``when``: place them in the camera's zone, raise breaches on entry."""
    from alerts.events import publish_zones
    from alerts.models import AlertSource
    from sitemap.models import Zone

    zone = Zone.objects.for_camera(camera_id).filter(is_active=True).first()
    entered, previous = place(worker, zone, when, CAMERA, camera_id)
    if previous != zone:
        publish_zones([z for z in (previous, zone) if z is not None])
    if entered:
        restricted_breach(worker, zone, AlertSource.AI_CAMERA, camera_id=camera_id, seen_by=camera_id)
        check_capacity(zone, worker=worker, source=AlertSource.AI_CAMERA, camera_id=camera_id)
    return zone


def record_camera_count(camera_id, people, when):
    """Store a camera's people count and re-check its zone's capacity. Returns True if stored."""
    from alerts.events import publish_zones
    from sitemap.models import Camera, Zone

    with transaction.atomic():
        camera, _ = Camera.objects.select_for_update().get_or_create(camera_id=camera_id)
        if camera.counted_at is not None and when <= camera.counted_at:
            return False
        changed = camera.counted_at is None or camera.people_count != people
        camera.people_count = people
        camera.counted_at = when
        camera.save(update_fields=["people_count", "counted_at"])
    zones = list(Zone.objects.for_camera(camera_id).filter(is_active=True))
    # Every report advances the capacity state (a steady crowd must still
    # reach its confirm time); only a changed count is broadcast.
    for zone in zones:
        if zone.max_occupancy > 0 or zone.over_capacity_since is not None:
            check_capacity(zone, now=when, camera_id=camera_id)
    if changed:
        publish_zones(zones)
    return True


LAST_PUBLISHED_KEY = "zone_counts:last_published"


def sweep_zone_counts(now=None):
    """Re-count every active zone: broadcast changed counts and update capacity flags.

    Counts change with time alone (a camera count or sighting going stale),
    so the presence monitor calls this on each pass. Returns the zones whose
    count changed.
    """
    from django.core.cache import cache

    from alerts.events import publish_zones
    from sitemap.models import Zone

    now = now or timezone.now()
    present, cameras = current_zone_ids(now), fresh_cameras(now)
    last = cache.get(LAST_PUBLISHED_KEY) or {}
    counts, changed = {}, []
    for zone in Zone.objects.filter(is_active=True):
        counts[zone.pk] = zone_occupancy(zone, now, present, cameras)["count"]
        if last.get(zone.pk) != counts[zone.pk]:
            changed.append(zone)
        if zone.max_occupancy > 0 or zone.over_capacity_since is not None:
            check_capacity(zone, now)  # confirms sustained periods and re-arms cleared ones
    cache.set(LAST_PUBLISHED_KEY, counts, None)
    publish_zones(changed)
    return changed
