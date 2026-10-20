"""Alert evidence (FR-29): snapshot validation, storage, idempotency, access and retention."""

import base64
import contextlib
import io
import shutil
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from sitemap.models import Zone

from .models import Alert, AlertConfig, AlertType


def image_bytes(fmt="JPEG", size=(64, 48)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, format=fmt)
    return buf.getvalue()


def b64(data):
    return base64.b64encode(data).decode("ascii")


class EvidenceTestCase(APITestCase):
    url = "/api/v1/camera-events/"

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        media = override_settings(MEDIA_ROOT=self.media)
        media.enable()
        self.addCleanup(media.disable)
        _, self.key = ServiceToken.issue("cam-1", ServiceToken.Kind.CAMERA)
        Zone.objects.create(name="Bay 1", camera_ids=["CAM-01"])

    def stored_files(self):
        return sorted(p.name for p in Path(self.media).rglob("*.jpg"))

    def payload(self, **over):
        body = {
            "event_id": str(uuid.uuid4()),
            "camera_id": "CAM-01",
            "alert_type": "PPE_VIOLATION",
            "severity": "HIGH",
            "description": "Missing PPE: no-helmet",
            "confidence": 0.81,
            "model_version": "sitesafe_v5.pt@0123456789ab",
            "snapshot": b64(image_bytes()),
        }
        body.update(over)
        return body

    def post(self, body):
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {self.key}")
        r = self.client.post(self.url, body, format="json")
        self.client.credentials()
        return r

    def user(self, role):
        user = User.objects.create_user(email=f"{role.lower()}@x.io", password="pw12345678")
        user.role = role
        user.save()
        return user


class CameraSnapshotIngestTests(EvidenceTestCase):
    def test_stores_snapshot_and_model_version(self):
        r = self.post(self.payload())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        alert = Alert.objects.get()
        self.assertEqual(alert.model_version, "sitesafe_v5.pt@0123456789ab")
        self.assertTrue(alert.snapshot.name.startswith("alert_snapshots/"))
        self.assertEqual(len(self.stored_files()), 1)
        self.assertEqual(r.data["snapshot"], f"/api/alerts/{alert.pk}/snapshot/")
        self.assertEqual(r.data["model_version"], "sitesafe_v5.pt@0123456789ab")
        self.assertEqual(r.data["confidence"], 0.81)

    def test_duplicate_event_does_not_store_second_image(self):
        body = self.payload()
        first = self.post(body)
        second = self.post(body)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["id"], first.data["id"])
        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(len(self.stored_files()), 1)

    def test_concurrent_duplicate_leaves_no_orphan_image(self):
        body = self.payload()

        def lose_the_race(alert, *args, **kwargs):
            # The other delivery of this event commits first.
            Alert.objects.bulk_create(
                [Alert(alert_type=alert.alert_type, severity=alert.severity, event_id=alert.event_id)]
            )
            raise IntegrityError("duplicate event_id")

        # Without this the view's atomic block would roll the competing row back too.
        no_savepoint = mock.patch("django.db.transaction.atomic", lambda *a, **k: contextlib.nullcontext())
        with mock.patch.object(Alert, "save", lose_the_race), no_savepoint:
            r = self.post(body)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(self.stored_files(), [])

    def test_event_without_snapshot(self):
        body = self.payload()
        del body["snapshot"]
        r = self.post(body)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(r.data["snapshot"])
        self.assertEqual(self.stored_files(), [])

    def test_older_camera_payload_without_evidence_fields(self):
        body = self.payload()
        del body["snapshot"], body["model_version"]
        r = self.post(body)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["model_version"], "")

    def test_rejects_invalid_snapshots(self):
        cases = {
            "not base64": "this is not base64!!",
            "png": b64(image_bytes("PNG")),
            "garbage": b64(b"\xff\xd8\xff" + b"\x00" * 64),
        }
        for name, value in cases.items():
            with self.subTest(name):
                r = self.post(self.payload(snapshot=value))
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("snapshot", r.data)
        self.assertEqual(Alert.objects.count(), 0)
        self.assertEqual(self.stored_files(), [])

    @override_settings(ALERT_SNAPSHOT_MAX_BYTES=1024)
    def test_rejects_oversized_snapshot(self):
        r = self.post(self.payload(snapshot=b64(image_bytes(size=(400, 400)) + b"\x00" * 2048)))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at most 1 KB", str(r.data["snapshot"]))

    @override_settings(ALERT_SNAPSHOT_MAX_SIDE=32)
    def test_rejects_oversized_dimensions(self):
        r = self.post(self.payload())
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pixels", str(r.data["snapshot"]))

    @override_settings(ALERT_SNAPSHOTS_ENABLED=False)
    def test_disabled_setting_discards_image_but_keeps_model_version(self):
        r = self.post(self.payload())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(r.data["snapshot"])
        self.assertEqual(r.data["model_version"], "sitesafe_v5.pt@0123456789ab")
        self.assertEqual(self.stored_files(), [])

    def test_suppressed_event_stores_no_image(self):
        AlertConfig.objects.update_or_create(
            zone=None, alert_type=AlertType.PPE_VIOLATION, defaults={"is_enabled": False}
        )
        r = self.post(self.payload())
        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self.stored_files(), [])

    def test_deleting_alert_deletes_image(self):
        self.post(self.payload())
        Alert.objects.get().delete()
        self.assertEqual(self.stored_files(), [])


class SnapshotAccessTests(EvidenceTestCase):
    def setUp(self):
        super().setUp()
        self.post(self.payload())
        self.alert = Alert.objects.get()
        self.path = f"/api/alerts/{self.alert.pk}/snapshot/"

    def test_viewer_can_read_snapshot(self):
        self.client.force_authenticate(self.user(Role.VIEWER))
        r = self.client.get(self.path)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertIn("private", r["Cache-Control"])
        self.assertEqual(b"".join(r.streaming_content), self.alert.snapshot.open("rb").read())

    def test_image_accept_header_is_honoured(self):
        # Mobile and <img> clients ask for image/*; DRF must not answer 406.
        self.client.force_authenticate(self.user(Role.VIEWER))
        r = self.client.get(self.path, HTTP_ACCEPT="image/*")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        missing = Alert.objects.create(alert_type=AlertType.FALL, severity="CRITICAL")
        r = self.client.get(f"/api/alerts/{missing.pk}/snapshot/", HTTP_ACCEPT="image/*")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(r["Content-Type"], "application/json")

    def test_anonymous_and_device_tokens_are_refused(self):
        self.assertEqual(self.client.get(self.path).status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {self.key}")
        self.assertIn(self.client.get(self.path).status_code, (401, 403))

    def test_alert_without_snapshot_is_404(self):
        self.client.force_authenticate(self.user(Role.SAFETY_OFFICER))
        other = Alert.objects.create(alert_type=AlertType.FALL, severity="CRITICAL")
        r = self.client.get(f"/api/alerts/{other.pk}/snapshot/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_alert_detail_lists_evidence(self):
        self.client.force_authenticate(self.user(Role.VIEWER))
        r = self.client.get(f"/api/alerts/{self.alert.pk}/")
        self.assertEqual(r.data["snapshot"], self.path)
        self.assertEqual(r.data["model_version"], "sitesafe_v5.pt@0123456789ab")

    def test_snapshot_is_not_writable_through_alert_api(self):
        self.client.force_authenticate(self.user(Role.SAFETY_OFFICER))
        r = self.client.patch(f"/api/alerts/{self.alert.pk}/", {"snapshot": None, "model_version": "x"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.snapshot)
        self.assertEqual(self.alert.model_version, "sitesafe_v5.pt@0123456789ab")


class SnapshotRetentionTests(EvidenceTestCase):
    def test_purges_only_expired_snapshots(self):
        self.post(self.payload())
        self.post(self.payload())
        old, recent = Alert.objects.order_by("pk")
        Alert.objects.filter(pk=old.pk).update(timestamp=timezone.now() - timedelta(days=31))
        old_file = old.snapshot.name

        out = io.StringIO()
        call_command("purge_alert_snapshots", "--days", "30", "--dry-run", stdout=out)
        self.assertIn("1 snapshot(s)", out.getvalue())
        self.assertEqual(len(self.stored_files()), 2)

        call_command("purge_alert_snapshots", "--days", "30", stdout=io.StringIO())
        old.refresh_from_db()
        recent.refresh_from_db()
        self.assertFalse(old.snapshot)
        self.assertTrue(recent.snapshot)
        self.assertEqual(self.stored_files(), [Path(recent.snapshot.name).name])
        self.assertNotIn(Path(old_file).name, self.stored_files())
        self.assertEqual(old.model_version, "sitesafe_v5.pt@0123456789ab")

    @override_settings(ALERT_SNAPSHOT_RETENTION_DAYS=0)
    def test_default_retention_comes_from_settings(self):
        self.post(self.payload())
        Alert.objects.update(timestamp=timezone.now() - timedelta(seconds=1))
        call_command("purge_alert_snapshots", stdout=io.StringIO())
        self.assertEqual(self.stored_files(), [])
