"""Cameras on the site map (FR-33): placement, map rows, live updates and the latest-frame thumbnail."""

import uuid
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from alerts import live
from alerts.models import Alert, AlertType, Severity
from alerts.test_live import jpeg

from .models import Camera, Zone

PLACE = {"latitude": 33.6851, "longitude": 73.0482, "heading": 135, "field_of_view": 90, "view_range_m": 40}


def user(role):
    u = User.objects.create_user(email=f"{role.lower()}-{uuid.uuid4().hex[:6]}@x.io", password="pw12345678")
    u.role = role
    u.save()
    return u


class PlacementTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(user(Role.ADMIN))

    def put(self, camera_id="CAM-01", **over):
        return self.client.put(f"/api/v1/camera-map/{camera_id}/", {**PLACE, **over}, format="json")

    def test_admin_places_and_moves_a_camera(self):
        r = self.put()
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["placement"], PLACE)
        r = self.put(heading=10)
        self.assertEqual(r.data["placement"]["heading"], 10)
        self.assertEqual(Camera.objects.get(camera_id="CAM-01").heading, 10)

    def test_placing_keeps_the_cameras_people_count(self):
        Camera.objects.create(camera_id="CAM-01", people_count=4, counted_at=timezone.now())
        r = self.put()
        self.assertEqual((r.data["people_in_view"], r.data["placement"]["view_range_m"]), (4, 40))

    def test_rejects_bad_placements(self):
        cases = {
            "latitude out of range": {"latitude": 91},
            "longitude out of range": {"longitude": -181},
            "no position": {"latitude": None},
            "heading over 359": {"heading": 360},
            "view angle too narrow": {"field_of_view": 5},
            "range too long": {"view_range_m": 1000},
        }
        for label, over in cases.items():
            with self.subTest(label):
                self.assertEqual(self.put(**over).status_code, 400)
        self.assertEqual(self.put(camera_id="bad id").status_code, 400)
        self.assertFalse(Camera.objects.exists(), "an invalid request leaves no row behind")

    def test_take_off_the_map(self):
        self.put()
        r = self.client.delete("/api/v1/camera-map/CAM-01/")
        self.assertEqual(r.status_code, 204)
        self.assertIsNone(Camera.objects.get(camera_id="CAM-01").latitude)
        self.assertEqual(self.client.delete("/api/v1/camera-map/CAM-01/").status_code, 404)

    def test_only_admins_place_cameras(self):
        for role in (Role.SAFETY_OFFICER, Role.VIEWER):
            with self.subTest(role):
                self.client.force_authenticate(user(role))
                self.assertEqual(self.put().status_code, 403)
                self.assertEqual(self.client.get("/api/v1/camera-map/").status_code, 200, "everyone signed in reads")
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/camera-map/").status_code, 401)

    def test_placement_is_broadcast(self):
        with mock.patch("alerts.events.publish") as publish:
            with self.captureOnCommitCallbacks(execute=True):
                self.put()
        self.assertEqual(publish.call_args.args[0], "camera_updated")
        self.assertEqual(publish.call_args.args[1]()["placement"], PLACE)


class MapRowTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client.force_authenticate(user(Role.VIEWER))

    def rows(self):
        return {r["camera_id"]: r for r in self.client.get("/api/v1/camera-map/").data}

    def test_lists_known_cameras_placed_or_not(self):
        Zone.objects.create(name="Bay 1", camera_ids=["CAM-01"], risk_level="LOW")
        ServiceToken.issue("cam-2", ServiceToken.Kind.CAMERA, ["CAM-02"])
        Camera.objects.create(camera_id="CAM-07", **PLACE)
        rows = self.rows()
        self.assertEqual(sorted(rows), ["CAM-01", "CAM-02", "CAM-07"])
        self.assertEqual(rows["CAM-01"]["zone"], "Bay 1")
        self.assertIsNone(rows["CAM-01"]["placement"])
        self.assertEqual(rows["CAM-07"]["placement"], PLACE)

    def test_live_status_people_in_view_and_alerts(self):
        now = timezone.now()
        Camera.objects.create(camera_id="CAM-01", people_count=3, counted_at=now, **PLACE)
        Camera.objects.create(camera_id="CAM-02", people_count=5, counted_at=now - timedelta(minutes=5), **PLACE)
        live.publish("CAM-01", jpeg())
        Alert.objects.create(alert_type=AlertType.PPE_VIOLATION, severity=Severity.HIGH, camera_id="CAM-01")
        latest = Alert.objects.create(alert_type=AlertType.DANGER_AREA, severity=Severity.CRITICAL, camera_id="CAM-01")
        Alert.objects.create(
            alert_type=AlertType.FALL, severity=Severity.CRITICAL, camera_id="CAM-02", is_resolved=True, resolved_at=now
        )
        rows = self.rows()
        self.assertTrue(rows["CAM-01"]["live"])
        self.assertFalse(rows["CAM-02"]["live"])
        self.assertEqual(rows["CAM-01"]["people_in_view"], 3)
        self.assertIsNone(rows["CAM-02"]["people_in_view"], "a count older than 30 s is not shown as current")
        self.assertEqual(rows["CAM-01"]["open_alerts"], 2)
        self.assertEqual(rows["CAM-02"]["open_alerts"], 0)
        self.assertEqual(
            (rows["CAM-01"]["last_alert"]["id"], rows["CAM-01"]["last_alert"]["alert_type"]),
            (latest.pk, "DANGER_AREA"),
        )
        self.assertTrue(rows["CAM-02"]["last_alert"]["is_resolved"])

    def test_a_changed_people_count_is_broadcast(self):
        from workers import location

        with mock.patch("alerts.events.publish") as publish:
            with self.captureOnCommitCallbacks(execute=True):
                location.record_camera_count("CAM-01", 2, timezone.now())
        self.assertIn("camera_updated", [c.args[0] for c in publish.call_args_list])


class LatestFrameTests(APITestCase):
    url = "/api/v1/camera-frames/latest/"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_officer_gets_the_latest_frame(self):
        frame = jpeg()
        live.publish("CAM-01", frame)
        self.client.force_authenticate(user(Role.SAFETY_OFFICER))
        r = self.client.get(self.url, {"camera_id": "CAM-01"}, HTTP_ACCEPT="image/*")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r["Content-Type"], r["Cache-Control"], r.content), ("image/jpeg", "no-store", frame))
        self.assertEqual(self.client.get(self.url, {"camera_id": "CAM-02"}).status_code, 404)
        self.assertEqual(self.client.get(self.url, {"camera_id": "bad id"}).status_code, 400)

    def test_viewers_get_no_video(self):
        live.publish("CAM-01", jpeg())
        self.client.force_authenticate(user(Role.VIEWER))
        self.assertEqual(self.client.get(self.url, {"camera_id": "CAM-01"}).status_code, 403)
