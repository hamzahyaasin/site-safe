"""Per-worker daily timelines built from ActivityLog.

A day runs midnight to midnight in the requested time zone. Intervals that
began before the day (a night shift, a long idle period) are clipped to its
start; intervals still open are clipped to now (today) or to the end of the
day (past days) and marked ``open``. Totals are computed from the clipped
intervals, so per-day figures add up across days.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import ActivityLog

A = ActivityLog.Action
PAIRS = {
    "sessions": (A.CHECK_IN, A.CHECK_OUT),
    "idle": (A.IDLE_START, A.IDLE_END),
}


def day_bounds(day, tz):
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def _iso(dt):
    return dt.isoformat() if dt else None


def _intervals(logs, open_action, close_action, start, cap, key=lambda log: None):
    """Pair open/close actions (per ``key``) into clipped intervals."""
    opened = {}
    out = []
    for log in logs:
        k = key(log)
        if log.action == open_action:
            opened.setdefault(k, (log.timestamp, log))
        elif log.action == close_action and k in opened:
            began, first = opened.pop(k)
            if log.timestamp > start:
                out.append((max(began, start), min(log.timestamp, cap), False, first))
    for k, (began, first) in opened.items():
        if cap > max(began, start):
            out.append((max(began, start), cap, True, first))
    return sorted((iv for iv in out if iv[1] > iv[0]), key=lambda iv: iv[0])


def _minutes(intervals):
    return round(sum((end - begin).total_seconds() for begin, end, *_ in intervals) / 60, 1)


def build_timeline(worker, day, tz, now=None):
    now = now or timezone.now()
    start, end = day_bounds(day, tz)
    cap = min(end, now)
    # Look back far enough to know what was already open at midnight.
    logs = list(
        ActivityLog.objects.filter(worker=worker, timestamp__lt=end, timestamp__gte=start - timedelta(days=2))
        .select_related("zone")
        .order_by("timestamp", "id")
    )

    sessions = _intervals(logs, *PAIRS["sessions"], start, cap)
    idle = _intervals(logs, *PAIRS["idle"], start, cap)
    zones = _intervals(logs, A.ZONE_ENTER, A.ZONE_EXIT, start, cap, key=lambda log: log.zone_id)

    zone_minutes = {}
    for begin, finish, _, first in zones:
        name = first.zone.name if first.zone_id else "Unknown zone"
        zone_minutes[name] = round(zone_minutes.get(name, 0) + (finish - begin).total_seconds() / 60, 1)

    in_day = [log for log in logs if log.timestamp >= start]
    check_ins = [log.timestamp for log in in_day if log.action == A.CHECK_IN]
    check_outs = [log.timestamp for log in in_day if log.action == A.CHECK_OUT]
    sources = sorted({(log.metadata or {}).get("source") for log in in_day if (log.metadata or {}).get("source")})

    return {
        "worker": worker.pk,
        "worker_name": worker.name,
        "date": day.isoformat(),
        "timezone": str(tz),
        "sessions": [{"start": _iso(b), "end": _iso(e), "open": o} for b, e, o, _ in sessions],
        "idle": [{"start": _iso(b), "end": _iso(e), "open": o} for b, e, o, _ in idle],
        "zones": [
            {"zone": f.zone_id, "zone_name": f.zone.name if f.zone_id else None, "start": _iso(b), "end": _iso(e), "open": o}
            for b, e, o, f in zones
        ],
        "first_check_in": _iso(min(check_ins)) if check_ins else None,
        "last_check_out": _iso(max(check_outs)) if check_outs else None,
        "on_site_minutes": _minutes(sessions),
        "idle_minutes": _minutes(idle),
        "zone_minutes": zone_minutes,
        "evidence_sources": sources,
        "has_activity": bool(sessions or idle or zones),
    }
