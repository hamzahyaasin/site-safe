"""Alert list filters: by camera, and the newest N (used by the mobile camera screen)."""

import uuid

from rest_framework.test import APITestCase

from accounts.models import Role, User

from .models import Alert, AlertType, Severity


class AlertFilterTests(APITestCase):
    url = "/api/alerts/"

    def setUp(self):
        u = User.objects.create_user(email=f"v-{uuid.uuid4().hex[:6]}@x.io", password="pw12345678")
        u.role = Role.VIEWER
        u.save()
        self.client.force_authenticate(u)
        self.cam1 = [
            Alert.objects.create(alert_type=AlertType.PPE_VIOLATION, severity=Severity.HIGH, camera_id="CAM-01")
            for _ in range(3)
        ]
        Alert.objects.create(alert_type=AlertType.FALL, severity=Severity.CRITICAL, camera_id="CAM-02")

    def test_filter_by_camera(self):
        r = self.client.get(self.url, {"camera_id": "CAM-01"})
        self.assertEqual(sorted(a["id"] for a in r.data), sorted(a.pk for a in self.cam1))

    def test_newest_n(self):
        r = self.client.get(self.url, {"camera_id": "CAM-01", "limit": 2})
        newest = sorted(self.cam1, key=lambda a: (a.timestamp, a.pk), reverse=True)[:2]
        self.assertEqual(len(r.data), 2)
        self.assertEqual({a["id"] for a in r.data}, {a.pk for a in newest})
        for bad in ("0", "-1", "abc", "501"):
            with self.subTest(bad):
                self.assertEqual(self.client.get(self.url, {"limit": bad}).status_code, 400)
        self.assertEqual(self.client.get(f"{self.url}{self.cam1[0].pk}/", {"limit": 1}).status_code, 200, "detail ignores limit")
