"""Vest presence and observed zone occupancy.

A vest counts as online only while it keeps reporting: ``last_seen`` within
``VEST_OFFLINE_AFTER_SECONDS``. The API computes this at read time, so it is
correct even if the background sweep is not running; the sweep exists to
persist the transition and push it to dashboards.

"Observed" zone membership comes from GPS zone-enter/exit logs of vests that
are still online. It is separate from a worker's assigned ``zone``.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from .models import ActivityLog, SmartVest


def offline_after():
    return timedelta(seconds=settings.VEST_OFFLINE_AFTER_SECONDS)


def is_vest_online(vest, now=None):
    if vest is None or vest.last_seen is None:
        return False
    now = now or timezone.now()
    return now - vest.last_seen <= offline_after()


def sweep_stale_vests(now=None):
    """Mark vests that stopped reporting as offline. Returns how many changed."""
    now = now or timezone.now()
    stale = SmartVest.objects.filter(is_online=True).exclude(last_seen__gte=now - offline_after())
    changed = 0
    for vest in stale.select_related("worker"):
        vest.is_online = False
        vest.save(update_fields=["is_online"])  # signal broadcasts vest_updated
        changed += 1
    return changed


def observed_zone_ids(now=None):
    """{worker_id: zone_id} for workers whose vest is online and whose latest
    GPS zone log is an entry. Workers outside every zone are omitted."""
    now = now or timezone.now()
    latest = ActivityLog.objects.filter(
        worker=OuterRef("worker"),
        action__in=[ActivityLog.Action.ZONE_ENTER, ActivityLog.Action.ZONE_EXIT],
    ).order_by("-timestamp", "-id")
    rows = (
        ActivityLog.objects.filter(
            pk=Subquery(latest.values("pk")[:1]),
            action=ActivityLog.Action.ZONE_ENTER,
            worker__smart_vest__last_seen__gte=now - offline_after(),
            worker__is_active=True,
        )
        .values_list("worker_id", "zone_id")
    )
    return {w: z for w, z in rows if z is not None}


def observed_occupancy(zone_id, now=None):
    return sum(1 for z in observed_zone_ids(now).values() if z == zone_id)
