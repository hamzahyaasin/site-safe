"""Device-token ingest, idempotency, rule enforcement and validation."""

import uuid
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from sitemap.models import Zone
from workers.models import SmartVest, Worker

from .models import Alert, AlertConfig, AlertType
from . import notify


def device(client, key):
    client.credentials(HTTP_AUTHORIZATION=f"Device {key}")


class CameraEventTests(APITestCase):
    url = "/api/v1/camera-events/"

    def setUp(self):
        self.token, self.key = ServiceToken.issue("cam-1", ServiceToken.Kind.CAMERA)
        self.zone = Zone.objects.create(name="Bay 1", camera_ids=["CAM-01"])

    def payload(self, **over):
        body = {
            "event_id": str(uuid.uuid4()),
            "camera_id": "CAM-01",
            "alert_type": "PPE_VIOLATION",
            "severity": "HIGH",
            "description": "Missing PPE: no-helmet",
            "confidence": 0.81,
        }
        body.update(over)
        return body

    def test_anonymous_refused(self):
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_human_jwt_refused(self):
        officer = User.objects.create_user(email="o@x.io", password="pw12345678")
        officer.role = Role.SAFETY_OFFICER
        officer.save()
        self.client.force_authenticate(officer)
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_revoked_token_refused(self):
        self.token.is_active = False
        self.token.save()
        device(self.client, self.key)
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_gateway_token_cannot_post_camera_events(self):
        _, gkey = ServiceToken.issue("gw", ServiceToken.Kind.VEST_GATEWAY)
        device(self.client, gkey)
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_device_token_cannot_use_human_endpoints(self):
        device(self.client, self.key)
        for path in ("/api/alerts/", "/api/workers/", "/api/v1/profile/", "/api/dashboard/stats/"):
            r = self.client.get(path)
            self.assertIn(
                r.status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                path,
            )

    def test_stores_event_once_per_event_id(self):
        device(self.client, self.key)
        body = self.payload()
        first = self.client.post(self.url, body, format="json")
        second = self.client.post(self.url, body, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Alert.objects.count(), 1)
        alert = Alert.objects.get()
        self.assertEqual(alert.source, "AI_CAMERA")
        self.assertAlmostEqual(alert.confidence, 0.81)

    def test_disabled_rule_suppresses(self):
        AlertConfig.objects.filter(alert_type=AlertType.PPE_VIOLATION, zone=None).update(
            is_enabled=False
        )
        device(self.client, self.key)
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(r.data["status"], "suppressed")
        self.assertEqual(Alert.objects.count(), 0)

    def test_zone_rule_overrides_global(self):
        AlertConfig.objects.filter(alert_type=AlertType.PPE_VIOLATION, zone=None).update(
            is_enabled=False
        )
        AlertConfig.objects.create(zone=self.zone, alert_type=AlertType.PPE_VIOLATION, is_enabled=True)
        device(self.client, self.key)
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_camera_scoped_token(self):
        _, scoped = ServiceToken.issue("cam-2", ServiceToken.Kind.CAMERA, ["CAM-02"])
        device(self.client, scoped)
        r = self.client.post(self.url, self.payload(camera_id="CAM-01"), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.client.post(self.url, self.payload(camera_id="CAM-02"), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_invalid_payloads_rejected(self):
        device(self.client, self.key)
        bad = [
            self.payload(confidence=1.5),
            self.payload(alert_type="SOS"),
            self.payload(event_id="not-a-uuid"),
            self.payload(camera_id=""),
            self.payload(severity="EXTREME"),
        ]
        for body in bad:
            r = self.client.post(self.url, body, format="json")
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, body)
        self.assertEqual(Alert.objects.count(), 0)


class CameraConfigTests(APITestCase):
    url = "/api/v1/camera-config/"

    def setUp(self):
        _, self.key = ServiceToken.issue("cam-1", ServiceToken.Kind.CAMERA, ["CAM-01"])
        self.zone = Zone.objects.create(name="Bay 1", camera_ids=["CAM-01"])

    def test_returns_effective_rules(self):
        AlertConfig.objects.create(
            zone=self.zone, alert_type=AlertType.INACTIVITY, threshold_seconds=90
        )
        AlertConfig.objects.filter(alert_type=AlertType.FALL, zone=None).update(is_enabled=False)
        device(self.client, self.key)
        r = self.client.get(self.url, {"camera_id": "CAM-01"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["zone"], "Bay 1")
        self.assertEqual(r.data["rules"]["INACTIVITY"]["threshold_seconds"], 90)
        self.assertFalse(r.data["rules"]["FALL"]["is_enabled"])

    def test_other_camera_forbidden(self):
        device(self.client, self.key)
        r = self.client.get(self.url, {"camera_id": "CAM-09"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class DetectionIngestTests(APITestCase):
    url = "/api/v1/detections/"

    def test_requires_camera_token_and_valid_bbox(self):
        body = {
            "camera_id": "CAM-01",
            "class_name": "no-helmet",
            "confidence": 0.7,
            "bbox": [10, 10, 50, 80],
            "frame_timestamp": "2026-10-16T10:00:00Z",
        }
        r = self.client.post(self.url, body, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
        _, key = ServiceToken.issue("cam", ServiceToken.Kind.CAMERA)
        device(self.client, key)
        r = self.client.post(self.url, {**body, "bbox": [50, 10, 10, 80]}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.client.post(self.url, body, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)


class VestIngestTests(APITestCase):
    def setUp(self):
        _, self.key = ServiceToken.issue("gw", ServiceToken.Kind.VEST_GATEWAY)
        self.worker = Worker.objects.create(name="Ali", vest_id="V-1")
        self.vest = SmartVest.objects.create(vest_id="V-1", worker=self.worker)

    def test_telemetry_requires_gateway_token(self):
        r = self.client.post("/api/v1/vests/telemetry/", {"vest_id": "V-1"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_telemetry_validation(self):
        device(self.client, self.key)
        bad = [
            {"vest_id": "V-1", "latitude": 95, "longitude": 10},
            {"vest_id": "V-1", "latitude": 33.6},
            {"vest_id": "V-1", "battery_level": 140},
            {"latitude": 33.6, "longitude": 73.0},
        ]
        for body in bad:
            r = self.client.post("/api/v1/vests/telemetry/", body, format="json")
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, body)

    def test_telemetry_sos_creates_one_alert(self):
        device(self.client, self.key)
        body = {"vest_id": "V-1", "latitude": 33.6, "longitude": 73.0, "sos_active": True}
        self.assertEqual(self.client.post("/api/v1/vests/telemetry/", body, format="json").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/vests/telemetry/", body, format="json").status_code, 200)
        self.assertEqual(Alert.objects.filter(alert_type=AlertType.SOS).count(), 1)

    def test_unknown_vest_404(self):
        device(self.client, self.key)
        r = self.client.post("/api/v1/vests/telemetry/", {"vest_id": "nope"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_alert_ingest_requires_gateway(self):
        body = {"vest_id": "V-1", "alert_type": "SOS", "severity": "CRITICAL"}
        self.assertEqual(
            self.client.post("/api/alerts/ingest/", body, format="json").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        device(self.client, self.key)
        self.assertEqual(
            self.client.post("/api/alerts/ingest/", body, format="json").status_code,
            status.HTTP_201_CREATED,
        )


class AlertConfigRuleTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="a@x.io", password="pw12345678")
        self.admin.role = Role.ADMIN
        self.admin.save()
        self.client.force_authenticate(self.admin)

    def test_defaults_seeded_for_every_type(self):
        types = set(AlertConfig.objects.filter(zone=None).values_list("alert_type", flat=True))
        self.assertEqual(types, set(AlertType.values))

    def test_sos_cannot_be_disabled(self):
        cfg = AlertConfig.objects.get(alert_type=AlertType.SOS, zone=None)
        r = self.client.patch(f"/api/v1/alert-config/{cfg.id}/", {"is_enabled": False}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_rule_rejected(self):
        r = self.client.post(
            "/api/v1/alert-config/", {"alert_type": "FALL", "zone": None}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_threshold_rejected(self):
        cfg = AlertConfig.objects.get(alert_type=AlertType.INACTIVITY, zone=None)
        r = self.client.patch(
            f"/api/v1/alert-config/{cfg.id}/", {"threshold_seconds": -1}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class NotificationRuleTests(APITestCase):
    def setUp(self):
        notify.RUN_INLINE = True
        self.addCleanup(setattr, notify, "RUN_INLINE", False)
        self.on = User.objects.create_user(email="on@x.io", password="pw12345678")
        self.off = User.objects.create_user(email="off@x.io", password="pw12345678")
        from accounts.models import UserPreferences

        UserPreferences.objects.create(user=self.off, notify_push=False, notify_email=False)

    def _create(self, alert_type):
        with self.captureOnCommitCallbacks(execute=True):
            return Alert.objects.create(alert_type=alert_type, severity="HIGH", camera_id="CAM-01")

    def test_respects_rule_and_preferences(self):
        from django.core import mail

        with mock.patch("sitesafe.notifications.send_push_notification") as push:
            self._create(AlertType.FALL)  # seeded: push + email on
        push.assert_called_once()
        self.assertEqual(push.call_args.args[0], [self.on.id])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["on@x.io"])

    def test_rule_disables_channels(self):
        from django.core import mail

        AlertConfig.objects.filter(alert_type=AlertType.FALL, zone=None).update(
            notify_push=False, notify_email=False
        )
        with mock.patch("sitesafe.notifications.send_push_notification") as push:
            self._create(AlertType.FALL)
        push.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

    def test_provider_failure_does_not_break_storage(self):
        with mock.patch(
            "sitesafe.notifications.send_push_notification", side_effect=RuntimeError("down")
        ):
            alert = self._create(AlertType.FALL)
        self.assertTrue(Alert.objects.filter(pk=alert.pk).exists())
