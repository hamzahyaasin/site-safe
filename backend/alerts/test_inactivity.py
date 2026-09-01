"""Tests for camera-side inactivity tracking.

The production decision module is dependency-free, so these tests are
discoverable by the project's standard Django test command without importing
OpenCV, torch, Ultralytics, or opening a camera.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User
from alerts.models import Alert, AlertSource, AlertType, Severity


AI_MODULE_DIR = Path(__file__).resolve().parents[2] / "ai-module"
if str(AI_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODULE_DIR))

import inactivity  # noqa: E402  (path is intentionally prepared above)


PERSON_A = (0.0, 0.0, 20.0, 100.0)
PERSON_B = (200.0, 0.0, 240.0, 100.0)


def shifted(box, dx=0.0, dy=0.0):
    x1, y1, x2, y2 = box
    return x1 + dx, y1 + dy, x2 + dx, y2 + dy


class InactivityGeometryTests(SimpleTestCase):
    def test_centroid_and_distance_use_box_centre(self):
        self.assertEqual(inactivity.centroid(PERSON_A), (10.0, 50.0))
        self.assertEqual(
            inactivity.centroid_distance((10.0, 50.0), (13.0, 54.0)),
            5.0,
        )

    def test_invalid_box_and_configuration_are_rejected(self):
        with self.assertRaises(ValueError):
            inactivity.centroid((0.0, 1.0, 2.0))
        with self.assertRaises(ValueError):
            inactivity.centroid((10.0, 0.0, 5.0, 20.0))
        with self.assertRaises(ValueError):
            inactivity.InactivityTracker(timeout_seconds=0)
        with self.assertRaises(ValueError):
            inactivity.InactivityTracker(movement_threshold=-1)


class InactivityTrackerTests(SimpleTestCase):
    def make_tracker(self, **overrides):
        options = {
            "timeout_seconds": 10,
            "movement_threshold": 10,
            "minimum_observations": 3,
            "max_match_distance": 100,
        }
        options.update(overrides)
        return inactivity.InactivityTracker(**options)

    def test_timeout_uses_elapsed_time_across_sampled_frames(self):
        tracker = self.make_tracker()
        self.assertEqual(tracker.update([PERSON_A], now=100.0), [])
        self.assertEqual(tracker.update([shifted(PERSON_A, dx=2)], now=104.0), [])
        self.assertEqual(tracker.update([shifted(PERSON_A, dx=-2)], now=109.9), [])

        events = tracker.update([PERSON_A], now=110.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "INACTIVITY")
        self.assertEqual(events[0]["track_id"], 1)
        self.assertEqual(events[0]["stationary_seconds"], 10.0)

    def test_movement_resets_the_stationary_timeout(self):
        tracker = self.make_tracker()
        tracker.update([PERSON_A], now=0.0)
        tracker.update([PERSON_A], now=5.0)
        self.assertEqual(tracker.update([shifted(PERSON_A, dx=20)], now=9.0), [])
        self.assertEqual(tracker.update([shifted(PERSON_A, dx=20)], now=18.9), [])

        events = tracker.update([shifted(PERSON_A, dx=20)], now=19.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stationary_since"], 9.0)

    def test_alert_latches_then_movement_rearms_the_same_track(self):
        tracker = self.make_tracker(minimum_observations=2)
        tracker.update([PERSON_A], now=0.0)
        first = tracker.update([PERSON_A], now=10.0)
        self.assertEqual(len(first), 1)
        self.assertEqual(tracker.update([PERSON_A], now=20.0), [])

        tracker.update([shifted(PERSON_A, dx=20)], now=21.0)
        second = tracker.update([shifted(PERSON_A, dx=20)], now=31.0)

        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["track_id"], first[0]["track_id"])

    def test_multiple_people_are_tracked_independently_when_order_changes(self):
        tracker = self.make_tracker(minimum_observations=2)
        tracker.update([PERSON_A, PERSON_B], now=0.0)
        tracker.update([shifted(PERSON_A, dx=20), PERSON_B], now=5.0)

        events = tracker.update([PERSON_B, shifted(PERSON_A, dx=20)], now=10.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["track_id"], 2)
        self.assertEqual(events[0]["centroid"], inactivity.centroid(PERSON_B))

    def test_short_missed_detection_is_tolerated_but_cannot_emit(self):
        tracker = self.make_tracker(minimum_observations=2, max_missing_updates=1)
        tracker.update([PERSON_A], now=0.0)
        self.assertEqual(tracker.update([], now=10.0), [])

        events = tracker.update([PERSON_A], now=11.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["track_id"], 1)

    def test_stale_track_is_dropped_and_returning_person_waits_again(self):
        tracker = self.make_tracker(minimum_observations=2, max_missing_updates=1)
        tracker.update([PERSON_A], now=0.0)
        tracker.update([], now=5.0)
        tracker.update([], now=10.0)
        self.assertEqual(tracker.active_track_count, 0)

        self.assertEqual(tracker.update([PERSON_A], now=20.0), [])
        events = tracker.update([PERSON_A], now=30.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["track_id"], 2)

    def test_description_is_explicitly_camera_level(self):
        tracker = self.make_tracker(minimum_observations=2)
        tracker.update([PERSON_A], now=0.0)
        event = tracker.update([PERSON_A], now=10.0)[0]

        description = inactivity.describe(event)

        self.assertIn("camera view", description)
        self.assertIn("temporary track 1", description)


class CameraInactivityAlertApiTests(APITestCase):
    def test_existing_alert_api_accepts_camera_level_inactivity_event(self):
        officer = User.objects.create_user(
            email="inactivity-test@example.com",
            password="test-password",
        )
        officer.role = Role.SAFETY_OFFICER
        officer.save(update_fields=["role"])
        self.client.force_authenticate(officer)

        # SQLite (used by isolated test settings) does not implement the JSON
        # ``contains`` lookup used for camera-to-zone resolution. PostgreSQL
        # does; mocking only that lookup keeps this test focused on the alert
        # ingestion contract and camera id persistence.
        with patch("alerts.serializers.Zone.objects.for_camera") as for_camera:
            for_camera.return_value.first.return_value = None
            event = {
                "track_id": 7,
                "stationary_seconds": 300.0,
            }
            response = self.client.post(
                "/api/alerts/",
                inactivity.alert_payload(event, "CAM-BAY-2"),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alert = Alert.objects.get(pk=response.data["id"])
        self.assertEqual(alert.alert_type, AlertType.INACTIVITY)
        self.assertEqual(alert.severity, Severity.MEDIUM)
        self.assertEqual(alert.source, AlertSource.AI_CAMERA)
        self.assertEqual(alert.camera_id, "CAM-BAY-2")
        self.assertIsNone(alert.worker)
