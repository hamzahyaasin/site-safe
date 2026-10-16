"""Live updates: every producer broadcasts after commit; sockets require a JWT."""

from datetime import timedelta
from unittest import mock

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, ServiceToken, User
from workers.models import SmartVest, Worker

from .models import Alert, AlertType


class BroadcastOnCommitTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(email="o@x.io", password="pw12345678")
        self.officer.role = Role.SAFETY_OFFICER
        self.officer.save()
        self.client = APIClient()

    def sent_types(self, send):
        return [c.args[0] for c in send.call_args_list]

    def test_create_and_resolve_broadcast(self):
        self.client.force_authenticate(self.officer)
        with mock.patch("alerts.events._send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                r = self.client.post(
                    "/api/alerts/", {"alert_type": "FALL", "severity": "CRITICAL"}, format="json"
                )
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(f"/api/alerts/{r.data['id']}/resolve/")
        self.assertEqual(self.sent_types(send), ["alert_created", "alert_resolved"])
        self.assertTrue(send.call_args_list[1].args[1]["is_resolved"])

    def test_vest_sos_broadcasts_alert_and_vest(self):
        worker = Worker.objects.create(name="Ali", vest_id="V-1")
        SmartVest.objects.create(vest_id="V-1", worker=worker)
        _, key = ServiceToken.issue("gw", ServiceToken.Kind.VEST_GATEWAY)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")
        with mock.patch("alerts.events._send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(
                    "/api/v1/vests/telemetry/",
                    {"vest_id": "V-1", "latitude": 33.6, "longitude": 73.0, "sos_active": True},
                    format="json",
                )
        types = self.sent_types(send)
        self.assertIn("alert_created", types)
        self.assertIn("vest_updated", types)
        self.assertIn("worker_status_update", types)

    def test_rolled_back_alert_not_broadcast(self):
        from django.db import transaction

        with mock.patch("alerts.events._send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        Alert.objects.create(alert_type=AlertType.FALL, severity="HIGH")
                        raise RuntimeError
                except RuntimeError:
                    pass
        send.assert_not_called()


class WebsocketAuthTests(TransactionTestCase):
    def setUp(self):
        from sitesafe.asgi import application

        self.app = application
        self.user = User.objects.create_user(email="v@x.io", password="pw12345678")
        self.user.role = Role.VIEWER
        self.user.save()

    def _close_code(self, query="", origin=b"http://localhost:5173"):
        """Connect and return (handshake_accepted, close_code_or_None)."""

        async def go():
            comm = WebsocketCommunicator(
                self.app, f"/ws/dashboard/{query}", headers=[(b"origin", origin)]
            )
            connected, _ = await comm.connect()
            if not connected:
                return False, None
            out = await comm.receive_output(timeout=1)
            return True, out.get("code") if out["type"] == "websocket.close" else None

        return async_to_sync(go)()

    def test_closes_4401_without_token(self):
        self.assertEqual(self._close_code(), (True, 4401))

    def test_closes_4401_for_bad_or_expired_token(self):
        self.assertEqual(self._close_code("?token=garbage"), (True, 4401))
        expired = AccessToken.for_user(self.user)
        expired.set_exp(lifetime=-timedelta(minutes=1))
        self.assertEqual(self._close_code(f"?token={expired}"), (True, 4401))

    def test_rejects_foreign_origin(self):
        token = str(AccessToken.for_user(self.user))
        accepted, _ = self._close_code(f"?token={token}", origin=b"http://evil.example")
        self.assertFalse(accepted)

    def test_accepts_valid_token_and_receives_events(self):
        from channels.db import database_sync_to_async

        token = str(AccessToken.for_user(self.user))

        async def go():
            comm = WebsocketCommunicator(
                self.app,
                f"/ws/dashboard/?token={token}",
                headers=[(b"origin", b"http://localhost:5173")],
            )
            connected, _ = await comm.connect()
            hello = await comm.receive_json_from()
            await database_sync_to_async(Alert.objects.create)(
                alert_type=AlertType.FALL, severity="HIGH"
            )
            event = await comm.receive_json_from(timeout=2)
            await comm.disconnect()
            return connected, hello, event

        connected, hello, event = async_to_sync(go)()
        self.assertTrue(connected)
        self.assertEqual(hello["type"], "connection_established")
        self.assertEqual(event["type"], "alert_created")
        self.assertEqual(event["payload"]["alert_type"], "FALL")
