import logging

from django.db import transaction
from django.utils import timezone

from alerts.models import Alert, AlertSource, AlertType, Severity
from sitemap.geofence import check_worker_zone

from .models import SmartVest

logger = logging.getLogger(__name__)


def validated_payload(payload):
    """Validate a raw MQTT payload; returns clean data or None (and logs) if invalid."""
    from .serializers import VestTelemetrySerializer

    serializer = VestTelemetrySerializer(data=payload if isinstance(payload, dict) else {})
    if not serializer.is_valid():
        logger.warning("Rejected vest telemetry %r: %s", payload, serializer.errors)
        return None
    data = dict(serializer.validated_data)
    data.pop("vest_id", None)
    return data


def apply_vest_telemetry(vest_id, payload, simulated=False):
    """
    Update vest state from an already-validated telemetry payload.
    Returns the updated SmartVest, or None if vest_id is unknown.

    Saving the vest and any SOS alert fires model signals that broadcast the
    change to dashboards after the transaction commits.

    ``simulated`` marks data from a simulator token: alerts get the
    SIMULATED source and zone logs a ``simulated`` flag, so they are
    labelled in the UI and excluded from report figures.
    """
    with transaction.atomic():
        return _apply(vest_id, payload, AlertSource.SIMULATED if simulated else AlertSource.SMART_VEST)


def _apply(vest_id, payload, source):
    # Lock only the vest row: PostgreSQL cannot lock the nullable side of the
    # worker join, and the worker row does not need locking.
    vest = (
        SmartVest.objects.select_for_update(of=("self",))
        .filter(vest_id=vest_id)
        .select_related("worker")
        .first()
    )
    if not vest:
        return None

    was_sos_active = vest.sos_active
    presses = payload.get("sos_presses")
    # The vest counts presses from start-up, so a lower count means it restarted.
    restarted = presses is not None and presses < vest.sos_presses
    pressed_again = presses is not None and presses > vest.sos_presses

    if "latitude" in payload:
        vest.latitude = payload["latitude"]
    if "longitude" in payload:
        vest.longitude = payload["longitude"]
    if "battery_level" in payload:
        vest.battery_level = payload["battery_level"]
    if "sos_active" in payload:
        vest.sos_active = payload["sos_active"]
    if presses is not None:
        vest.sos_presses = presses
    now = timezone.now()

    vest.is_online = True
    vest.last_seen = now
    vest.save()
    # Simulated vests drive alerts and the map but never attendance records.
    if vest.worker and source != AlertSource.SIMULATED:
        from .activity import record_seen

        record_seen(vest.worker, vest.last_seen, f"vest {vest.vest_id}")

    # A vest without a GPS fix (or without a GPS module) has no position yet.
    where = {"lat": vest.latitude, "lng": vest.longitude} if vest.latitude is not None else None
    if vest.worker:
        update_sos_alert(vest, was_sos_active, pressed_again, restarted, where, source, now)

    # Only a fresh position can move a worker between zones.
    if vest.worker and "latitude" in payload:
        place_by_gps(vest.worker, vest, source)

    return vest


def update_sos_alert(vest, was_active, pressed_again, restarted, where, source, now):
    """Keep the worker's SOS alert in step with the vest's SOS state.

    A press raises an SOS alert unless one is still open; a repeated press on
    a vest already in SOS raises a new one once a supervisor has resolved the
    first. The wearer cancelling (holding the button) resolves the open alert
    with a note. A vest that restarts loses its SOS state without the wearer
    cancelling, so its open alert stays open for a supervisor to resolve.
    """
    open_sos = Alert.objects.filter(
        worker=vest.worker, alert_type=AlertType.SOS, source=source, is_resolved=False
    )
    if vest.sos_active and (not was_active or pressed_again):
        if not open_sos.exists():
            Alert.objects.create(
                worker=vest.worker,
                alert_type=AlertType.SOS,
                severity=Severity.CRITICAL,
                source=source,
                description=(
                    f"SOS activated at ({vest.latitude}, {vest.longitude})" if where else "SOS activated (no position reported)"
                ),
                location=where,
            )
    elif was_active and not vest.sos_active and not restarted:
        for alert in open_sos:
            alert.description += "; cancelled by the wearer"
            alert.is_resolved = True
            alert.resolved_at = now
            alert.save(update_fields=["description", "is_resolved", "resolved_at"])


def place_by_gps(worker, vest, source):
    """Place the vest's worker in the zone containing its position; raise breaches on entry."""
    from . import location
    from alerts.events import publish_zones

    zone = check_worker_zone(worker, vest.latitude, vest.longitude)
    metadata = {"lat": vest.latitude, "lng": vest.longitude}
    if source == AlertSource.SIMULATED:
        metadata["simulated"] = True
    entered, previous = location.place(worker, zone, vest.last_seen, location.VEST, vest.vest_id, metadata)
    if previous != zone:
        publish_zones([z for z in (previous, zone) if z is not None])
    if entered:
        where = {"lat": vest.latitude, "lng": vest.longitude}
        location.restricted_breach(worker, zone, source, location=where)
        location.check_capacity(zone, worker=worker, source=source, location=where)


def handle_telemetry(vest_id, payload):
    """Handle sitesafe/vest/{vest_id}/telemetry messages."""
    data = validated_payload(payload)
    if data is not None:
        apply_vest_telemetry(vest_id, data)


def handle_sos(vest_id, payload):
    """Handle sitesafe/vest/{vest_id}/sos messages."""
    data = validated_payload(payload)
    if data is not None:
        data["sos_active"] = True
        apply_vest_telemetry(vest_id, data)
