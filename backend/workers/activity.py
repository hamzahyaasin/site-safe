"""Automatic workforce activity: check-in/out sessions and idle periods.

Evidence that a worker is on site comes from two places: their vest
reporting, and a camera reading their QR badge. From that:

* **Check-in**: the first evidence while no session is open opens one at
  the time of that evidence.
* **Check-out**: when no evidence has arrived for ``CHECKOUT_AFTER_MINUTES``,
  the session is closed at the *last* time the worker was seen, not at the
  time the sweep noticed. An open idle period closes with it.
* **Idle**: a camera reports an identified person who stayed still past the
  inactivity timeout (IDLE_START, dated to when they stopped moving) and
  when that person moves again (IDLE_END).

All times are when things happened, so events delivered late by the camera
outbox land where they belong. Workers without a vest or a readable badge
produce no activity at all: absence of evidence is never recorded as
presence or absence.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import ActivityLog, Worker

A = ActivityLog.Action
SESSION_ACTIONS = (A.CHECK_IN, A.CHECK_OUT)
IDLE_ACTIONS = (A.IDLE_START, A.IDLE_END)


def checkout_after():
    return timedelta(minutes=settings.CHECKOUT_AFTER_MINUTES)


def _last(worker, actions, before=None):
    qs = ActivityLog.objects.filter(worker=worker, action__in=actions)
    if before is not None:
        qs = qs.filter(timestamp__lte=before)
    return qs.order_by("-timestamp", "-id").first()


def session_open(worker, at=None) -> bool:
    last = _last(worker, SESSION_ACTIONS, at)
    return bool(last and last.action == A.CHECK_IN)


def idle_open(worker, at=None) -> bool:
    last = _last(worker, IDLE_ACTIONS, at)
    return bool(last and last.action == A.IDLE_START)


def record_seen(worker, when=None, source=""):
    """Note evidence that ``worker`` was on site at ``when``; check in if needed."""
    if worker is None or not worker.is_active:
        return None
    when = when or timezone.now()
    with transaction.atomic():
        worker = Worker.objects.select_for_update().get(pk=worker.pk)
        if worker.last_seen_at is None or when > worker.last_seen_at:
            worker.last_seen_at = when
            worker.last_seen_source = source[:80]
            worker.save(update_fields=["last_seen_at", "last_seen_source"])
        if not session_open(worker, when):
            _open_or_merge(worker, when, source)
    return worker


def _open_or_merge(worker, when, source):
    """Start a session at ``when``, or extend an adjacent one with a late event.

    Late delivery means ``when`` can fall just before an existing check-in
    (move that check-in earlier) or just after an automatic check-out (move
    the check-out later). Only gaps shorter than the check-out interval are
    merged; anything further apart is a separate session.
    """
    window = checkout_after()
    following = (
        ActivityLog.objects.filter(worker=worker, action__in=SESSION_ACTIONS, timestamp__gt=when)
        .order_by("timestamp", "id")
        .first()
    )
    if following and following.action == A.CHECK_IN and following.timestamp - when <= window:
        following.timestamp = when
        following.save(update_fields=["timestamp"])
        return
    previous = _last(worker, SESSION_ACTIONS, when)
    if (
        previous
        and previous.action == A.CHECK_OUT
        and (previous.metadata or {}).get("automatic")
        and when - previous.timestamp <= window
    ):
        previous.timestamp = when
        previous.save(update_fields=["timestamp"])
        return
    ActivityLog.objects.create(worker=worker, action=A.CHECK_IN, timestamp=when, metadata={"source": source})
    if following and following.action == A.CHECK_IN:
        # An isolated late sighting before a later session: it is a session
        # of its own, closed where it was seen, not one spanning the gap.
        ActivityLog.objects.create(
            worker=worker,
            action=A.CHECK_OUT,
            timestamp=when,
            metadata={"reason": "isolated late sighting", "automatic": True},
        )


def idle_start(worker, when, source=""):
    record_seen(worker, when, source)
    if worker and not idle_open(worker, when):
        ActivityLog.objects.create(worker=worker, action=A.IDLE_START, timestamp=when, metadata={"source": source})


def idle_end(worker, when, source=""):
    if worker and idle_open(worker, when):
        ActivityLog.objects.create(worker=worker, action=A.IDLE_END, timestamp=when, metadata={"source": source})
    record_seen(worker, when, source)


def sweep_checkouts(now=None) -> int:
    """Close sessions of workers not seen for CHECKOUT_AFTER_MINUTES. Returns the count."""
    now = now or timezone.now()
    cutoff = now - checkout_after()
    closed = 0
    for worker in Worker.objects.filter(last_seen_at__lt=cutoff):
        if not session_open(worker):
            continue
        at = worker.last_seen_at
        meta = {"reason": f"not seen for {settings.CHECKOUT_AFTER_MINUTES} min", "automatic": True}
        if idle_open(worker):
            ActivityLog.objects.create(worker=worker, action=A.IDLE_END, timestamp=at, metadata=meta)
        ActivityLog.objects.create(worker=worker, action=A.CHECK_OUT, timestamp=at, metadata=meta)
        closed += 1
    return closed
