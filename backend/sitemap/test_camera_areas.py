"""Danger areas drawn on camera pictures (FR-32): API, validation, camera config, alert type."""

import uuid

from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from alerts.models import Alert, AlertConfig, AlertType

from .models import CameraArea

SQUARE = [[0.2, 0.5], [0.6, 0.5], [0.6, 0.95], [0.2, 0.95]]


def user(role):
    u = User.objects.create_user(email=f"{role.lower()}-{uuid.uuid4().hex[:6]}@x.io", password="pw12345678")
    u.role = role
    u.save()
    return u


class CameraAreaApiTests(APITestCase):
    url = "/api/v1/camera-areas/"

    def setUp(self):
        self.client.force_authenticate(user(Role.ADMIN))

    def create(self, **over):
        body = {"camera_id": "CAM-09", "name": "Crane swing", "polygon": SQUARE, "severity": "CRITICAL"}
        body.update(over)
        return self.client.post(self.url, body, format="json")

    def test_admin_draws_an_area(self):
        r = self.create()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["polygon"], SQUARE)
        self.assertTrue(r.data["is_active"])

    def test_officer_reads_but_cannot_edit(self):
        self.create()
        self.client.force_authenticate(user(Role.SAFETY_OFFICER))
        r = self.client.get(self.url, {"camera_id": "CAM-09"})
        self.assertEqual([a["name"] for a in r.data], ["Crane swing"])
        self.assertEqual(self.client.get(self.url, {"camera_id": "CAM-01"}).data, [])
        self.assertEqual(self.create(name="Other").status_code, 403)

    def test_rejects_bad_polygons_and_names(self):
        cases = {
            "two points": {"polygon": SQUARE[:2]},
            "outside the image": {"polygon": [[0.1, 0.1], [1.2, 0.1], [0.5, 0.9]]},
            "not numbers": {"polygon": [["a", 0.1], [0.2, 0.1], [0.5, 0.9]]},
            "repeated points": {"polygon": [[0.1, 0.1], [0.1, 0.1], [0.1, 0.1], [0.5, 0.5]]},
            "too many points": {"polygon": [[i / 30, (i % 2) * 0.5 + 0.1] for i in range(25)]},
            "bad camera id": {"camera_id": "bad id"},
            "empty name": {"name": "  "},
        }
        for label, over in cases.items():
            with self.subTest(label):
                self.assertEqual(self.create(**over).status_code, 400)

    def test_area_names_are_unique_per_camera(self):
        self.create()
        r = self.create(name="crane SWING")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already has an area", str(r.data["name"]))
        self.assertEqual(self.create(camera_id="CAM-10").status_code, 201, "same name on another camera is fine")


class CameraConfigAreaTests(APITestCase):
    def test_camera_receives_only_its_active_areas(self):
        CameraArea.objects.create(camera_id="CAM-09", name="Crane swing", polygon=SQUARE, severity="CRITICAL")
        CameraArea.objects.create(camera_id="CAM-09", name="Pit", polygon=SQUARE, is_active=False)
        CameraArea.objects.create(camera_id="CAM-01", name="Gate", polygon=SQUARE)
        _, key = ServiceToken.issue("cam-9", ServiceToken.Kind.CAMERA, ["CAM-09"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")
        r = self.client.get("/api/v1/camera-config/", {"camera_id": "CAM-09"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            [(a["name"], a["severity"], a["polygon"]) for a in r.data["areas"]], [("Crane swing", "CRITICAL", SQUARE)]
        )
        self.assertIn("DANGER_AREA", r.data["rules"])


class DangerAreaAlertTests(APITestCase):
    def setUp(self):
        _, self.key = ServiceToken.issue("cam-9", ServiceToken.Kind.CAMERA)

    def post_event(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {self.key}")
        return self.client.post(
            "/api/v1/camera-events/",
            {
                "event_id": str(uuid.uuid4()),
                "camera_id": "CAM-09",
                "alert_type": "DANGER_AREA",
                "severity": "CRITICAL",
                "description": "Person entered danger area 'Crane swing' on CAM-09",
            },
            format="json",
        )

    def test_camera_can_raise_danger_area_alerts(self):
        self.assertTrue(AlertConfig.objects.filter(alert_type=AlertType.DANGER_AREA, zone=None).exists(), "seeded rule")
        r = self.post_event()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Alert.objects.get().alert_type, "DANGER_AREA")

    def test_rule_can_switch_them_off(self):
        AlertConfig.objects.filter(alert_type=AlertType.DANGER_AREA, zone=None).update(is_enabled=False)
        self.assertEqual(self.post_event().status_code, 202)
        self.assertEqual(Alert.objects.count(), 0)
