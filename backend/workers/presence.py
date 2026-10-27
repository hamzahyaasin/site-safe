"""Vest presence.

A vest counts as online only while it keeps reporting: ``last_seen`` within
``VEST_OFFLINE_AFTER_SECONDS``. The API computes this at read time, so it is
correct even if the background sweep is not running; the sweep exists to
persist the transition and push it to dashboards.

Where workers are (from vests and cameras) and zone head counts live in
``workers.location``.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import SmartVest


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
