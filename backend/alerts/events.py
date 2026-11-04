"""Live-update fan-out to dashboard websocket clients.

Every producer — API views, camera ingest, vest telemetry, the MQTT consumer
and the admin — saves models, and model signals call these helpers. Sending
happens in ``transaction.on_commit`` so a client is never told about a row
that was rolled back, and a failure to reach the channel layer never breaks
the save that triggered it.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)

DEFAULT_SITE = "default"


def group_name(site_id=DEFAULT_SITE):
    return f"dashboard_{site_id}"


def _send(event_type, payload, site_id=DEFAULT_SITE):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            group_name(site_id),
            {"type": "dashboard_event", "event_type": event_type, "payload": payload},
        )
    except Exception:  # noqa: BLE001 - delivery must not break persistence
        logger.exception("Failed to broadcast %s", event_type)


def publish(event_type, build_payload, site_id=DEFAULT_SITE):
    """Broadcast after the current transaction commits.

    ``build_payload`` is called at commit time so the payload reflects the
    committed row (including fields set by later saves in the same transaction).
    """
    transaction.on_commit(lambda: _send(event_type, build_payload(), site_id))


def publish_alert(alert, created):
    from .serializers import AlertSerializer

    if created:
        event_type = "alert_created"
    elif alert.is_resolved:
        event_type = "alert_resolved"
    else:
        event_type = "alert_updated"
    pk = alert.pk

    def build():
        from .models import Alert

        fresh = Alert.objects.select_related("worker", "zone").filter(pk=pk).first()
        return AlertSerializer(fresh or alert).data

    publish(event_type, build)


def publish_vest(vest):
    from workers.serializers import SmartVestSerializer

    pk = vest.pk

    def build():
        from workers.models import SmartVest

        fresh = SmartVest.objects.select_related("worker").filter(pk=pk).first()
        return SmartVestSerializer(fresh or vest).data

    publish("vest_updated", build)


def publish_gas_monitor(monitor):
    from sitemap.serializers import GasMonitorSerializer

    pk = monitor.pk

    def build():
        from sitemap.models import GasMonitor

        fresh = GasMonitor.objects.select_related("zone").filter(pk=pk).first()
        return GasMonitorSerializer(fresh or monitor).data

    publish("gas_monitor_updated", build)


def publish_gas_monitor_deleted(monitor_id):
    publish("gas_monitor_deleted", lambda: {"id": monitor_id})


def publish_worker(worker):
    from workers.serializers import WorkerSerializer

    pk = worker.pk

    def build():
        from workers.models import Worker

        fresh = Worker.objects.select_related("zone", "smart_vest", "location_zone").filter(pk=pk).first()
        return WorkerSerializer(fresh or worker).data

    publish("worker_status_update", build)


def publish_camera(camera_id):
    """Broadcast a camera's site-map row (placement, live status, people in view, alerts)."""

    def build():
        from sitemap import camera_map

        return camera_map.row(camera_id)

    publish("camera_updated", build)


def publish_zones(zones):
    """Broadcast each zone's details, including its current head count."""
    from sitemap.serializers import ZoneDetailSerializer

    pks = sorted({z.pk for z in zones})
    if not pks:
        return

    def send_all():
        from sitemap.models import Zone

        rows = Zone.objects.filter(pk__in=pks).prefetch_related("workers")
        context = {}
        for zone in rows:
            _send("zone_updated", ZoneDetailSerializer(zone, context=context).data)

    transaction.on_commit(send_all)
