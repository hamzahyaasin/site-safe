from django.utils import timezone

from alerts.models import Alert, AlertSource, AlertType, Severity
from sitemap.geofence import check_worker_zone

from .models import ActivityLog, SmartVest


def log_zone_change(worker, new_zone, lat, lng):
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
        return

    metadata = {"lat": lat, "lng": lng}
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


def apply_vest_telemetry(vest_id, payload):
    """
    Update vest state from telemetry payload.
    Returns the updated SmartVest, or None if vest_id is unknown.
    """
    vest = SmartVest.objects.filter(vest_id=vest_id).select_related("worker").first()
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

    if vest.sos_active and not was_sos_active and vest.worker:
        Alert.objects.create(
            worker=vest.worker,
            alert_type=AlertType.SOS,
            severity=Severity.CRITICAL,
            source=AlertSource.SMART_VEST,
            description=f"SOS activated at ({vest.latitude}, {vest.longitude})",
            location={"lat": vest.latitude, "lng": vest.longitude},
        )

    if vest.worker and vest.latitude is not None and vest.longitude is not None:
        zone = check_worker_zone(vest.worker, vest.latitude, vest.longitude)
        log_zone_change(vest.worker, zone, vest.latitude, vest.longitude)

    return vest


def handle_telemetry(vest_id, payload):
    """Handle sitesafe/vest/{vest_id}/telemetry messages."""
    apply_vest_telemetry(vest_id, payload)


def handle_sos(vest_id, payload):
    """Handle sitesafe/vest/{vest_id}/sos messages."""
    data = dict(payload)
    data["sos_active"] = True
    apply_vest_telemetry(vest_id, data)
