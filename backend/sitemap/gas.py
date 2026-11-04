"""Fixed gas monitors: readings, zone GAS alerts and offline detection.

A monitor reports its MQ-2 reading every few seconds. A reading at or above
GAS_ALERT_PPM raises one critical GAS alert naming the monitor's zone (no
worker: gas is a hazard of the place). While that alert is open, another
waits until the level has stayed below the limit for GAS_CLEAR_SECONDS, so a
reading that hovers around the limit does not alert every report; once a
supervisor has resolved it, the next rise above the limit alerts at once.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from alerts.models import Alert, AlertSource, AlertType, Severity

from .models import GasMonitor


def open_gas_alerts(monitor, source):
    """Unresolved GAS alerts for the monitor's zone (by monitor ID in the text if it has no zone)."""
    alerts = Alert.objects.filter(alert_type=AlertType.GAS, source=source, is_resolved=False)
    if monitor.zone_id:
        return alerts.filter(zone_id=monitor.zone_id)
    return alerts.filter(zone__isnull=True, description__contains=f"monitor {monitor.monitor_id} ")


def check_gas(monitor, ppm, now, alert_open=lambda: False):
    """Record a reading on ``monitor``; returns True when it should raise a GAS alert.

    ``alert_open`` reports whether the zone still has an unresolved GAS
    alert. The caller saves the monitor.
    """
    monitor.gas_ppm = ppm
    over = ppm >= settings.GAS_ALERT_PPM
    if over:
        rising = monitor.gas_below_since is not None
        monitor.gas_below_since = None
        if monitor.gas_alerted_at is None or (rising and not alert_open()):
            monitor.gas_alerted_at = now
            return True
        return False
    if monitor.gas_alerted_at is not None:
        if monitor.gas_below_since is None:
            monitor.gas_below_since = now
        elif (now - monitor.gas_below_since).total_seconds() >= settings.GAS_CLEAR_SECONDS:
            monitor.gas_alerted_at = monitor.gas_below_since = None
    return False


def apply_gas_telemetry(monitor_id, payload, simulated=False):
    """Update a monitor from validated telemetry; returns it, or None if unknown.

    ``payload`` may omit ``gas_ppm`` while the sensor warms up: the report
    still marks the monitor online. ``simulated`` (a simulator token) labels
    its alerts SIMULATED so they are excluded from report figures.
    """
    source = AlertSource.SIMULATED if simulated else AlertSource.GAS_MONITOR
    with transaction.atomic():
        monitor = (
            GasMonitor.objects.select_for_update(of=("self",))
            .filter(monitor_id=monitor_id)
            .select_related("zone")
            .first()
        )
        if not monitor:
            return None
        now = timezone.now()
        raise_alert = "gas_ppm" in payload and check_gas(
            monitor, payload["gas_ppm"], now, lambda: open_gas_alerts(monitor, source).exists()
        )
        monitor.is_online = True
        monitor.last_seen = now
        monitor.save()
        if raise_alert:
            where = (
                {"lat": monitor.latitude, "lng": monitor.longitude}
                if monitor.latitude is not None and monitor.longitude is not None
                else None
            )
            place = f"in {monitor.zone.name}" if monitor.zone else "(no zone assigned)"
            Alert.objects.create(
                zone=monitor.zone,
                alert_type=AlertType.GAS,
                severity=Severity.CRITICAL,
                source=source,
                description=(
                    f"Gas {monitor.gas_ppm:,} ppm {place}, monitor {monitor.monitor_id} "
                    f"(limit {settings.GAS_ALERT_PPM:,})"
                ),
                location=where,
            )
    return monitor


def is_monitor_online(monitor, now=None):
    if monitor is None or monitor.last_seen is None:
        return False
    now = now or timezone.now()
    return now - monitor.last_seen <= timedelta(seconds=settings.GAS_MONITOR_OFFLINE_AFTER_SECONDS)


def sweep_stale_monitors(now=None):
    """Mark monitors that stopped reporting as offline. Returns how many changed."""
    now = now or timezone.now()
    cutoff = now - timedelta(seconds=settings.GAS_MONITOR_OFFLINE_AFTER_SECONDS)
    changed = 0
    for monitor in GasMonitor.objects.filter(is_online=True).exclude(last_seen__gte=cutoff):
        monitor.is_online = False
        monitor.save(update_fields=["is_online"])  # signal broadcasts gas_monitor_updated
        changed += 1
    return changed
