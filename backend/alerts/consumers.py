import json

from channels.generic.websocket import AsyncWebsocketConsumer


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.site_id = self.scope["url_route"]["kwargs"].get("site_id", "default")
        self.group_name = f"dashboard_{self.site_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to Site-Safe dashboard",
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def dashboard_alert(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "alert_created",
                    "payload": event["payload"],
                }
            )
        )

    async def dashboard_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": event["event_type"],
                    "payload": event["payload"],
                }
            )
        )
