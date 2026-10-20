import logging

from django.db import transaction
from django.utils import timezone

from alerts.models import Alert, AlertSource, AlertType, Severity
from sitemap.geofence import check_worker_zone

from .models import ActivityLog, SmartVest

logger = logging.getLogger(__name__)


def log_zone_change(worker, new_zone, lat, lng, simulated=False):
    """Record zone exit/entry when the worker's observed zone changes.

    Returns True when ``new_zone`` was just entered.
    """
    last_log = (
        ActivityLog.objects.filter(
            worker=worker,
            action__in=[ActivityLog.Action.ZONE_ENTER, ActivityLog.Action.ZONE_EXIT],
        )
        .select_related("zone")
        .first()
    )
    current_zone = (
        last_log.zone
        if last_log and last_log.action == ActivityLog.Action.ZONE_ENTER
        else None
    )

    if current_zone == new_zone:
        return False

    metadata = {"lat": lat, "lng": lng}
    if simulated:
        metadata["simulated"] = True
    if current_zone:
        ActivityLog.objects.create(
            worker=worker,
            action=ActivityLog.Action.ZONE_EXIT,
            zone=current_zone,
            metadata=metadata,
        )
    if new_zone:
        ActivityLog.objects.create(
            worker=worker,
            action=ActivityLog.Action.ZONE_ENTER,
            zone=new_zone,
            metadata=metadata,
        )
    return new_zone is not None


def raise_zone_breaches(worker, zone, lat, lng, source=AlertSource.SMART_VEST):
    """Alert when a worker enters a restricted zone they are not assigned to,
    or when their entry takes a zone over its maximum occupancy."""
    from alerts.rules import rule_for
    from sitemap.models import Zone

    from .presence import observed_occupancy

    if not rule_for(AlertType.ZONE_BREACH, zone).is_enabled:
        return []
    location = {"lat": lat, "lng": lng}
    raised = []
    if zone.risk_level == Zone.RiskLevel.RESTRICTED and worker.zone_id != zone.pk:
        raised.append(
            Alert.objects.create(
                worker=worker,
                alert_type=AlertType.ZONE_BREACH,
                severity=Severity.HIGH,
                source=source,
                description=f"Entered restricted zone {zone.name} without assignment",
                location=location,
            )
        )
    if zone.max_occupancy > 0:
        occupancy = observed_occupancy(zone.pk)
        if occupancy > zone.max_occupancy:
            raised.append(
                Alert.objects.create(
                    worker=worker,
                    alert_type=AlertType.ZONE_BREACH,
                    severity=Severity.MEDIUM,
                    source=source,
                    description=(
                        f"{zone.name} over capacity: {occupancy} present, limit {zone.max_occupancy}"
                    ),
                    location=location,
                )
            )
    return raised


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
        zone = check_worker_zone(vest.worker, vest.latitude, vest.longitude)
        simulated = source == AlertSource.SIMULATED
        if log_zone_change(vest.worker, zone, vest.latitude, vest.longitude, simulated):
            raise_zone_breaches(vest.worker, zone, vest.latitude, vest.longitude, source)

    return vest


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
