from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import AlertSerializer

DEFAULT_DASHBOARD_GROUP = "dashboard_default"


def broadcast_alert_created(alert, site_id="default"):
    """Push a new alert to all dashboard WebSocket clients for the site."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = AlertSerializer(alert).data
    group_name = f"dashboard_{site_id}"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "dashboard_alert",
            "payload": payload,
        },
    )
