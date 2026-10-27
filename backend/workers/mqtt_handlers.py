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

    if "latitude" in payload:
        vest.latitude = payload["latitude"]
    if "longitude" in payload:
        vest.longitude = payload["longitude"]
    if "battery_level" in payload:
        vest.battery_level = payload["battery_level"]
    if "sos_active" in payload:
        vest.sos_active = payload["sos_active"]

    vest.is_online = True
    vest.last_seen = timezone.now()
    vest.save()
    # Simulated vests drive alerts and the map but never attendance records.
    if vest.worker and source != AlertSource.SIMULATED:
        from .activity import record_seen

        record_seen(vest.worker, vest.last_seen, f"vest {vest.vest_id}")

    if vest.sos_active and not was_sos_active and vest.worker:
        Alert.objects.create(
            worker=vest.worker,
            alert_type=AlertType.SOS,
            severity=Severity.CRITICAL,
            source=source,
            description=f"SOS activated at ({vest.latitude}, {vest.longitude})",
            location={"lat": vest.latitude, "lng": vest.longitude},
        )

    # Only a fresh position can move a worker between zones.
    if vest.worker and "latitude" in payload:
        place_by_gps(vest.worker, vest, source)

    return vest


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
