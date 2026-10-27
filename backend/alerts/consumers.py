import json

from channels.generic.websocket import AsyncWebsocketConsumer

from .events import DEFAULT_SITE, group_name

# Close code for an unauthenticated socket; the dashboard renews its access
# token and reconnects when it sees this.
CLOSE_UNAUTHORIZED = 4401
# Close code for a valid user whose role may not use this socket; clients
# must not retry it.
CLOSE_FORBIDDEN = 4403


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not (user and user.is_authenticated and user.has_role_at_least("VIEWER")):
            # Accept then close, rather than refusing the handshake: a refused
            # handshake reaches the browser only as code 1006, which the
            # dashboard cannot tell apart from a network drop. Nothing is sent
            # and the socket never joins a group.
            await self.accept()
            await self.close(code=CLOSE_UNAUTHORIZED)
            return

        self.site_id = self.scope["url_route"]["kwargs"].get("site_id", DEFAULT_SITE)
        self.group_name = group_name(self.site_id)

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

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def dashboard_event(self, event):
        await self.send(
            text_data=json.dumps({"type": event["event_type"], "payload": event["payload"]})
        )


class CameraFeedConsumer(AsyncWebsocketConsumer):
    """Live camera frames for Safety Officers and Admins (Cameras page).

    Each message is binary: camera id, newline, JPEG. On connect the latest
    frame of every live camera is sent at once.
    """

    async def connect(self):
        from channels.db import database_sync_to_async

        from . import live

        user = self.scope.get("user")
        await self.accept()
        if not (user and user.is_authenticated):
            await self.close(code=CLOSE_UNAUTHORIZED)
            return
        if not user.has_role_at_least("SAFETY_OFFICER"):
            await self.close(code=CLOSE_FORBIDDEN)
            return
        self.joined = True
        await self.channel_layer.group_add(live.GROUP, self.channel_name)
        for camera_id, jpeg in await database_sync_to_async(live.latest_frames)():
            await self.send(bytes_data=live.message(camera_id, jpeg))

    async def disconnect(self, close_code):
        from . import live

        if getattr(self, "joined", False):
            await self.channel_layer.group_discard(live.GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def camera_frame(self, event):
        from . import live

        await self.send(bytes_data=live.message(event["camera_id"], event["jpeg"]))
