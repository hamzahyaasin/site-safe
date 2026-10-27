"""Live camera view: frame ingest, validation, rate limit, camera list and the role-gated socket."""

import io
import time
from urllib.parse import quote

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, ServiceToken, User
from sitemap.models import Zone

from . import live


def jpeg(size=(64, 48), fmt="JPEG"):
    buf = io.BytesIO()
    Image.new("RGB", size, (20, 120, 200)).save(buf, format=fmt)
    return buf.getvalue()


def make_user(email, role):
    user = User.objects.create_user(email=email, password="pw12345678")
    user.role = role
    user.save()
    return user


class FrameIngestTests(APITestCase):
    url = "/api/v1/camera-frames/"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        _, self.key = ServiceToken.issue("cam-1", ServiceToken.Kind.CAMERA, ["CAM-01"])

    def post(self, body, camera_id="CAM-01", key=None, content_type="image/jpeg"):
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key or self.key}")
        r = self.client.post(f"{self.url}?camera_id={quote(camera_id)}", data=body, content_type=content_type)
        self.client.credentials()
        return r

    def test_frame_is_kept_as_latest_and_listed_live(self):
        frame = jpeg()
        r = self.post(frame)
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(live.latest_frames(), [("CAM-01", frame)])
        rows = {row["camera_id"]: row for row in live.camera_list()}
        self.assertTrue(rows["CAM-01"]["live"])

    def test_only_camera_tokens_for_this_camera(self):
        self.assertEqual(self.client.post(f"{self.url}?camera_id=CAM-01", data=jpeg(), content_type="image/jpeg").status_code, 401)
        _, gateway = ServiceToken.issue("gw", ServiceToken.Kind.VEST_GATEWAY)
        self.assertIn(self.post(jpeg(), key=gateway).status_code, (401, 403))
        self.assertEqual(self.post(jpeg(), camera_id="CAM-02").status_code, 403)
        officer = make_user("o@x.io", Role.SAFETY_OFFICER)
        self.client.force_authenticate(officer)
        r = self.client.post(f"{self.url}?camera_id=CAM-01", data=jpeg(), content_type="image/jpeg")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(live.latest_frames(), [])

    def test_rejects_bad_frames(self):
        _, any_camera = ServiceToken.issue("cam-any", ServiceToken.Kind.CAMERA)
        cases = [
            (jpeg(fmt="PNG"), "CAM-01", 400),
            (b"\xff\xd8\xff" + b"\x00" * 40, "CAM-01", 400),
            (b"", "CAM-01", 400),
            (jpeg(), "bad\nid", 400),
            (jpeg(), "bad id", 400),
            (jpeg(), "", 400),
        ]
        for body, camera_id, expected in cases:
            with self.subTest(camera_id=camera_id, size=len(body)):
                self.assertEqual(self.post(body, camera_id=camera_id, key=any_camera).status_code, expected)
        self.assertEqual(self.post(jpeg(), content_type="application/octet-stream").status_code, 415)
        self.assertEqual(live.latest_frames(), [])

    @override_settings(LIVE_FRAME_MAX_BYTES=1024)
    def test_rejects_oversized_frame(self):
        r = self.post(jpeg(size=(400, 400)) + b"\x00" * 2048)
        self.assertEqual(r.status_code, 400)

    @override_settings(LIVE_FRAME_MAX_SIDE=32)
    def test_rejects_oversized_dimensions(self):
        self.assertEqual(self.post(jpeg()).status_code, 400)

    def test_frames_faster_than_limit_are_dropped(self):
        self.assertEqual(self.post(jpeg()).status_code, 204)
        r = self.post(jpeg(size=(32, 32)))
        self.assertEqual(r.status_code, 202)
        self.assertEqual(len(live.latest_frames()[0][1]), len(jpeg()), "the dropped frame did not replace the first")

    @override_settings(LIVE_VIEW_ENABLED=False)
    def test_disabled_server_drops_frames(self):
        r = self.post(jpeg())
        self.assertEqual(r.status_code, 202)
        self.assertEqual(live.latest_frames(), [])


class CameraListTests(APITestCase):
    url = "/api/v1/cameras/"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        Zone.objects.create(name="Bay 1", camera_ids=["CAM-01", "CAM-02"])
        ServiceToken.issue("cam-gate", ServiceToken.Kind.CAMERA, ["CAM-GATE"])

    def test_viewer_refused(self):
        self.client.force_authenticate(make_user("v@x.io", Role.VIEWER))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_lists_zone_token_and_live_cameras(self):
        now = time.time()
        live.publish("CAM-01", jpeg(), now=now)
        live.publish("WEBCAM-TEST", jpeg(), now=now)
        live.publish("CAM-02", jpeg(), now=now - 60)
        self.client.force_authenticate(make_user("o@x.io", Role.SAFETY_OFFICER))
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        rows = {row["camera_id"]: row for row in r.data["cameras"]}
        self.assertEqual(sorted(rows), ["CAM-01", "CAM-02", "CAM-GATE", "WEBCAM-TEST"])
        self.assertEqual(rows["CAM-01"]["zone"], "Bay 1")
        self.assertTrue(rows["CAM-01"]["live"])
        self.assertTrue(rows["WEBCAM-TEST"]["live"])
        self.assertIsNone(rows["WEBCAM-TEST"]["zone"])
        self.assertFalse(rows["CAM-02"]["live"], "last frame a minute ago")
        self.assertIsNone(rows["CAM-GATE"]["last_frame_at"])
        self.assertTrue(r.data["live_view_enabled"])


class CameraSocketTests(TransactionTestCase):
    def setUp(self):
        from sitesafe.asgi import application

        cache.clear()
        self.addCleanup(cache.clear)
        self.app = application

    def connect(self, user):
        token = str(AccessToken.for_user(user)) if user else ""

        async def go():
            comm = WebsocketCommunicator(self.app, f"/ws/cameras/?token={token}", headers=[(b"origin", b"http://localhost:5173")])
            connected, _ = await comm.connect()
            out = await comm.receive_output(timeout=1)
            await comm.disconnect()
            return connected, out

        return async_to_sync(go)()

    def test_closes_for_anonymous_and_viewer(self):
        _, out = self.connect(None)
        self.assertEqual(out.get("code"), 4401)
        _, out = self.connect(make_user("v@x.io", Role.VIEWER))
        self.assertEqual(out.get("code"), 4403)

    def test_officer_gets_latest_then_new_frames(self):
        from channels.db import database_sync_to_async

        first, second = jpeg(), jpeg(size=(80, 60))
        live.publish("CAM-01", first)
        token = str(AccessToken.for_user(make_user("o@x.io", Role.SAFETY_OFFICER)))

        async def go():
            comm = WebsocketCommunicator(self.app, f"/ws/cameras/?token={token}", headers=[(b"origin", b"http://localhost:5173")])
            connected, _ = await comm.connect()
            initial = await comm.receive_from(timeout=2)
            await database_sync_to_async(live.publish)("WEBCAM-TEST", second)
            relayed = await comm.receive_from(timeout=2)
            await comm.disconnect()
            return connected, initial, relayed

        connected, initial, relayed = async_to_sync(go)()
        self.assertTrue(connected)
        self.assertEqual(initial, b"CAM-01\n" + first)
        self.assertEqual(relayed, b"WEBCAM-TEST\n" + second)
