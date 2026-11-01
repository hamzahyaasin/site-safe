"""A restricted zone's camera reports people it cannot identify as a ZONE_BREACH."""

import uuid

from rest_framework.test import APITestCase

from accounts.models import ServiceToken
from alerts.models import Alert, AlertConfig, AlertType
from sitemap.models import Zone


class UnidentifiedBreachTests(APITestCase):
    def setUp(self):
        self.crane = Zone.objects.create(name="Crane", camera_ids=["CAM-09"], risk_level="RESTRICTED")
        self.bay = Zone.objects.create(name="Bay 1", camera_ids=["CAM-01"])
        _, key = ServiceToken.issue("cams", ServiceToken.Kind.CAMERA)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")

    def post_event(self, camera_id="CAM-09"):
        return self.client.post(
            "/api/v1/camera-events/",
            {
                "event_id": str(uuid.uuid4()),
                "camera_id": camera_id,
                "alert_type": "ZONE_BREACH",
                "severity": "HIGH",
                "description": f"Unidentified person in restricted zone Crane on {camera_id}",
            },
            format="json",
        )

    def config(self, camera_id):
        return self.client.get("/api/v1/camera-config/", {"camera_id": camera_id}).data

    def test_camera_config_says_whether_the_zone_is_restricted(self):
        self.assertTrue(self.config("CAM-09")["zone_restricted"])
        self.assertFalse(self.config("CAM-01")["zone_restricted"])
        self.assertFalse(self.config("CAM-77")["zone_restricted"], "camera in no zone")
        self.crane.is_active = False
        self.crane.save()
        self.assertFalse(self.config("CAM-09")["zone_restricted"], "inactive zone")

    def test_restricted_zone_camera_raises_an_unattributed_breach(self):
        r = self.post_event()
        self.assertEqual(r.status_code, 201, r.data)
        alert = Alert.objects.get()
        self.assertEqual((alert.alert_type, alert.camera_id, alert.worker), (AlertType.ZONE_BREACH, "CAM-09", None))

    def test_breach_from_a_camera_whose_zone_is_not_restricted_is_dropped(self):
        self.assertEqual(self.post_event("CAM-01").status_code, 202)
        self.crane.risk_level = "HIGH"
        self.crane.save()
        self.assertEqual(self.post_event().status_code, 202, "zone changed after the camera's last config fetch")
        self.assertEqual(Alert.objects.count(), 0)

    def test_zone_breach_rule_switches_them_off(self):
        AlertConfig.objects.update_or_create(
            alert_type=AlertType.ZONE_BREACH, zone=None, defaults={"is_enabled": False}
        )
        self.assertEqual(self.post_event().status_code, 202)
        self.assertEqual(Alert.objects.count(), 0)
