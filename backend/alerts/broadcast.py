from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_alert(alert):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        "dashboard_default",
        {
            "type": "dashboard_alert",
            "payload": {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "description": alert.description,
                "worker_name": alert.worker.name if alert.worker else None,
                "timestamp": alert.timestamp.isoformat(),
            },
        },
    )
