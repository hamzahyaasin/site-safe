from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User

from .geofence import point_in_polygon
from .models import Zone

SQUARE = [
    {"lat": 0, "lng": 0},
    {"lat": 0, "lng": 1},
    {"lat": 1, "lng": 1},
    {"lat": 1, "lng": 0},
]


class GeofenceTests(APITestCase):
    def test_point_in_polygon(self):
        self.assertTrue(point_in_polygon(0.5, 0.5, SQUARE))
        self.assertFalse(point_in_polygon(1.5, 0.5, SQUARE))
        self.assertFalse(point_in_polygon(0.5, 0.5, SQUARE[:2]))

    def test_for_camera(self):
        z = Zone.objects.create(name="A", camera_ids=["CAM-01", "CAM-02"])
        Zone.objects.create(name="B", camera_ids=["CAM-03"])
        self.assertEqual(list(Zone.objects.for_camera("CAM-02")), [z])
        self.assertFalse(Zone.objects.for_camera("").exists())


class ZoneValidationTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user(email="a@x.io", password="pw12345678")
        admin.role = Role.ADMIN
        admin.save()
        self.client.force_authenticate(admin)

    def post(self, **fields):
        return self.client.post("/api/v1/zones/", {"name": "Z", **fields}, format="json")

    def test_valid_zone(self):
        r = self.post(boundaries=SQUARE, camera_ids=["CAM-01"])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_empty_boundary_allowed(self):
        self.assertEqual(self.post(boundaries=[]).status_code, status.HTTP_201_CREATED)

    def test_invalid_geometry_rejected(self):
        for boundaries in (
            SQUARE[:2],
            [{"lat": 0, "lng": 0}] * 3,
            [{"lat": 100, "lng": 0}, *SQUARE[1:]],
            [{"x": 1}, *SQUARE[1:]],
            "not a list",
        ):
            r = self.post(boundaries=boundaries)
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, boundaries)

    def test_invalid_camera_ids_rejected(self):
        for cams in (["CAM-01", "CAM-01"], [""], [5], "CAM-01"):
            r = self.post(camera_ids=cams)
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, cams)

    def test_negative_occupancy_rejected(self):
        self.assertEqual(self.post(max_occupancy=-1).status_code, status.HTTP_400_BAD_REQUEST)


class HotWorkPermitTests(APITestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone

        self.now = timezone.now()
        self.td = timedelta
        self.officer = User.objects.create_user(email="o@x.io", password="pw12345678")
        self.officer.role = Role.SAFETY_OFFICER
        self.officer.save()
        self.viewer = User.objects.create_user(email="v@x.io", password="pw12345678")
        self.viewer.role = Role.VIEWER
        self.viewer.save()
        self.zone = Zone.objects.create(name="Bay 2", camera_ids=["CAM-02"])

    def body(self, **over):
        b = {
            "zone": self.zone.id,
            "description": "Welding level 3 beams",
            "starts_at": (self.now - self.td(minutes=5)).isoformat(),
            "ends_at": (self.now + self.td(hours=2)).isoformat(),
        }
        b.update(over)
        return b

    def test_officer_issues_viewer_reads_only(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post("/api/v1/hot-work-permits/", self.body(), format="json").status_code, 403)
        self.client.force_authenticate(self.officer)
        r = self.client.post("/api/v1/hot-work-permits/", self.body(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data["is_active"])
        self.assertEqual(r.data["issued_by_email"], "o@x.io")
        self.client.force_authenticate(self.viewer)
        self.assertEqual(len(self.client.get("/api/v1/hot-work-permits/?state=active").data), 1)

    def test_validation(self):
        self.client.force_authenticate(self.officer)
        bad = [
            self.body(ends_at=(self.now - self.td(hours=1)).isoformat(), starts_at=(self.now - self.td(hours=2)).isoformat()),
            self.body(ends_at=(self.now - self.td(hours=1)).isoformat()),
            self.body(ends_at=(self.now + self.td(hours=13)).isoformat()),
            self.body(description="  "),
        ]
        for b in bad:
            self.assertEqual(self.client.post("/api/v1/hot-work-permits/", b, format="json").status_code, 400, b)
        self.zone.is_active = False
        self.zone.save()
        self.assertEqual(self.client.post("/api/v1/hot-work-permits/", self.body(), format="json").status_code, 400)

    def test_revoke_and_no_delete(self):
        self.client.force_authenticate(self.officer)
        pid = self.client.post("/api/v1/hot-work-permits/", self.body(), format="json").data["id"]
        self.assertEqual(self.client.delete(f"/api/v1/hot-work-permits/{pid}/").status_code, 405)
        r = self.client.post(f"/api/v1/hot-work-permits/{pid}/revoke/")
        self.assertFalse(r.data["is_active"])
        self.assertIsNotNone(r.data["revoked_at"])
        r = self.client.patch(f"/api/v1/hot-work-permits/{pid}/", {"description": "x"}, format="json")
        self.assertEqual(r.status_code, 400)


class FirePolicyTests(APITestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone

        from accounts.models import ServiceToken

        from .models import HotWorkPermit

        self.zone = Zone.objects.create(name="Bay 2", camera_ids=["CAM-02"])
        Zone.objects.create(name="Bay 3", camera_ids=["CAM-03"])
        now = timezone.now()
        self.permit = HotWorkPermit.objects.create(
            zone=self.zone, description="Welding", starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(hours=1)
        )
        _, key = ServiceToken.issue("cam", ServiceToken.Kind.CAMERA)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")

    def fire(self, camera, alert_type="FIRE", severity="LOW"):
        import uuid

        return self.client.post(
            "/api/v1/camera-events/",
            {"event_id": str(uuid.uuid4()), "camera_id": camera, "alert_type": alert_type, "severity": severity, "description": "Fire detected (conf 0.81)"},
            format="json",
        )

    def test_fire_inside_permit_is_downgraded_not_dropped(self):
        r = self.fire("CAM-02")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["severity"], "MEDIUM")
        self.assertEqual(r.data["hot_work_permit"], self.permit.id)
        self.assertIn("within hot-work permit", r.data["description"])

    def test_fire_elsewhere_is_critical_whatever_the_camera_says(self):
        r = self.fire("CAM-03", severity="LOW")
        self.assertEqual(r.data["severity"], "CRITICAL")
        self.assertIsNone(r.data["hot_work_permit"])
        self.assertIn("no active hot-work permit in Bay 3", r.data["description"])

    def test_smoke_levels(self):
        self.assertEqual(self.fire("CAM-02", "SMOKE").data["severity"], "LOW")
        self.assertEqual(self.fire("CAM-03", "SMOKE").data["severity"], "HIGH")
        self.assertEqual(self.fire("CAM-99", "SMOKE").data["severity"], "HIGH")  # unzoned camera

    def test_expired_or_revoked_permit_gives_no_cover(self):
        from django.utils import timezone

        self.permit.revoked_at = timezone.now()
        self.permit.save()
        self.assertEqual(self.fire("CAM-02").data["severity"], "CRITICAL")

    def test_fire_rule_cannot_be_disabled(self):
        from alerts.models import AlertConfig

        admin = User.objects.create_user(email="a@x.io", password="pw12345678")
        admin.role = Role.ADMIN
        admin.save()
        self.client.credentials()
        self.client.force_authenticate(admin)
        cfg = AlertConfig.objects.get(alert_type="FIRE", zone=None)
        r = self.client.patch(f"/api/v1/alert-config/{cfg.id}/", {"is_enabled": False}, format="json")
        self.assertEqual(r.status_code, 400)
        smoke = AlertConfig.objects.get(alert_type="SMOKE", zone=None)
        r = self.client.patch(f"/api/v1/alert-config/{smoke.id}/", {"is_enabled": False}, format="json")
        self.assertEqual(r.status_code, 200)
