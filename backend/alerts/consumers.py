import json

from channels.generic.websocket import AsyncWebsocketConsumer


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("dashboard_default", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("dashboard_default", self.channel_name)

    async def dashboard_alert(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "alert_created",
                    "payload": event["payload"],
                }
            )
        )
