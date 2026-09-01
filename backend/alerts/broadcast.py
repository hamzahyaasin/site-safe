from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import AlertSerializer


def broadcast_alert(alert, site_id="default"):
    """Push a new alert to all dashboard WebSocket clients for the site."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"dashboard_{site_id}",
        {
            "type": "dashboard_alert",
            "payload": AlertSerializer(alert).data,
        },
    )
