"""Tests for camera-side fall detection.

The production decision module is dependency-free, so these tests are
discoverable by the project's standard Django test command without
importing OpenCV, torch, Ultralytics, or opening a camera — the same
convention as test_proximity.py and test_inactivity.py.
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

import fall_detection as fall  # noqa: E402  (path is intentionally prepared above)


# A standing figure: vertical span (y: 8-200) far exceeds horizontal span
# (x: 80-120); hips (y=120) sit well above knees (y=160).
STANDING_XY = [
    (100, 10), (98, 8), (102, 8), (95, 9), (105, 9),        # nose, eyes, ears
    (90, 40), (110, 40),                                     # shoulders
    (85, 70), (115, 70),                                      # elbows
    (80, 100), (120, 100),                                    # wrists
    (95, 120), (105, 120),                                    # hips
    (95, 160), (105, 160),                                    # knees
    (95, 200), (105, 200),                                    # ankles
]

# A fallen figure: horizontal span (x: 8-195) far exceeds vertical span
# (y: 88-112); hips (y~100) sit level with knees (y~100).
FALLEN_XY = [
    (10, 100), (12, 98), (12, 102), (8, 97), (8, 103),
    (40, 95), (40, 105),
    (60, 90), (60, 110),
    (75, 88), (75, 112),
    (120, 98), (120, 102),
    (160, 97), (160, 103),
    (195, 98), (195, 102),
]

FULL_CONF = [0.9] * 17
LOW_CONF = [0.05] * 17


def shifted(xy, dx=0.0, dy=0.0):
    return [(x + dx, y + dy) for x, y in xy]


class FallGeometryTests(SimpleTestCase):
    def test_span_ratio_standing_is_below_one(self):
        ratio = fall.span_ratio(STANDING_XY, FULL_CONF)
        self.assertIsNotNone(ratio)
        self.assertLess(ratio, 1.0)

    def test_span_ratio_fallen_exceeds_threshold(self):
        ratio = fall.span_ratio(FALLEN_XY, FULL_CONF)
        self.assertIsNotNone(ratio)
        self.assertGreater(ratio, fall.DEFAULT_SPAN_RATIO_THRESHOLD)

    def test_span_ratio_none_with_too_few_confident_keypoints(self):
        sparse_conf = [0.9, 0.9, 0.9] + [0.0] * 14
        self.assertIsNone(fall.span_ratio(STANDING_XY, sparse_conf))

    def test_hips_above_knees_when_standing(self):
        self.assertFalse(fall.hips_at_or_below_knees(STANDING_XY, FULL_CONF))

    def test_hips_at_or_below_knees_when_fallen(self):
        self.assertTrue(fall.hips_at_or_below_knees(FALLEN_XY, FULL_CONF))

    def test_hips_at_or_below_knees_none_without_hip_or_knee_visibility(self):
        conf = list(FULL_CONF)
        for idx in (*fall.HIP_INDEXES, *fall.KNEE_INDEXES):
            conf[idx] = 0.0
        self.assertIsNone(fall.hips_at_or_below_knees(FALLEN_XY, conf))

    def test_weighted_centroid_ignores_low_confidence_points(self):
        conf = list(FULL_CONF)
        conf[0] = 0.9
        for i in range(1, 17):
            conf[i] = 0.0
        centroid = fall.weighted_centroid(STANDING_XY, conf)
        self.assertEqual(centroid, STANDING_XY[0])

    def test_weighted_centroid_none_when_nothing_confident(self):
        self.assertIsNone(fall.weighted_centroid(STANDING_XY, [0.0] * 17))

    def test_validate_pose_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            fall.span_ratio(STANDING_XY[:5], FULL_CONF[:5])


class CollapsedPostureTests(SimpleTestCase):
    def test_standing_is_not_collapsed(self):
        self.assertFalse(fall.is_collapsed_posture(STANDING_XY, FULL_CONF))

    def test_fallen_is_collapsed(self):
        self.assertTrue(fall.is_collapsed_posture(FALLEN_XY, FULL_CONF))

    def test_both_signals_are_required_wide_but_hips_still_high(self):
        # A wide keypoint spread (e.g. arms flung out) with hips still
        # clearly above the knees must not read as collapsed on span ratio
        # alone.
        wide_but_upright = list(STANDING_XY)
        wide_but_upright[9] = (-100, 100)   # left wrist flung far out
        wide_but_upright[10] = (300, 100)   # right wrist flung far out
        ratio = fall.span_ratio(wide_but_upright, FULL_CONF)
        self.assertGreater(ratio, fall.DEFAULT_SPAN_RATIO_THRESHOLD)
        self.assertFalse(fall.is_collapsed_posture(wide_but_upright, FULL_CONF))

    def test_low_confidence_pose_is_not_collapsed(self):
        # Neither signal is measurable, so this must not default to True.
        self.assertFalse(fall.is_collapsed_posture(FALLEN_XY, LOW_CONF))


class FallTrackerTests(SimpleTestCase):
    def make_tracker(self, **overrides):
        options = {
            "persistence_seconds": 3.0,
            "minimum_observations": 2,
            "max_match_distance": 150.0,
        }
        options.update(overrides)
        return fall.FallTracker(**options)

    def test_no_event_while_standing(self):
        tracker = self.make_tracker()
        for t in (0.0, 1.0, 2.0, 3.0):
            self.assertEqual(tracker.update([(STANDING_XY, FULL_CONF)], now=t), [])

    def test_persistence_required_before_confirming(self):
        tracker = self.make_tracker()
        self.assertEqual(tracker.update([(FALLEN_XY, FULL_CONF)], now=0.0), [])
        self.assertEqual(tracker.update([(FALLEN_XY, FULL_CONF)], now=1.5), [])
        self.assertEqual(tracker.update([(FALLEN_XY, FULL_CONF)], now=2.9), [])

        events = tracker.update([(FALLEN_XY, FULL_CONF)], now=3.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "FALL")
        self.assertEqual(events[0]["collapsed_seconds"], 3.0)

    def test_recovery_resets_the_streak(self):
        tracker = self.make_tracker()
        tracker.update([(FALLEN_XY, FULL_CONF)], now=0.0)
        tracker.update([(FALLEN_XY, FULL_CONF)], now=1.0)
        # Stands back up before the persistence threshold is reached.
        self.assertEqual(tracker.update([(STANDING_XY, FULL_CONF)], now=2.0), [])
        self.assertEqual(tracker.update([(FALLEN_XY, FULL_CONF)], now=2.5), [])

        # Only 0.5s of *this* collapsed run has elapsed, so no event yet.
        self.assertEqual(tracker.update([(FALLEN_XY, FULL_CONF)], now=3.0), [])

    def test_confirmed_fall_latches_then_recovery_rearms_same_track(self):
        tracker = self.make_tracker()
        tracker.update([(FALLEN_XY, FULL_CONF)], now=0.0)
        first = tracker.update([(FALLEN_XY, FULL_CONF)], now=3.0)
        self.assertEqual(len(first), 1)
        # Remains down: must not fire again while still collapsed.
        self.assertEqual(tracker.update([(FALLEN_XY, FULL_CONF)], now=4.0), [])

        tracker.update([(STANDING_XY, FULL_CONF)], now=5.0)
        tracker.update([(FALLEN_XY, FULL_CONF)], now=6.0)
        second = tracker.update([(FALLEN_XY, FULL_CONF)], now=9.0)

        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["track_id"], first[0]["track_id"])

    def test_multiple_people_tracked_independently(self):
        tracker = self.make_tracker()
        far_standing = (shifted(STANDING_XY, dx=400), FULL_CONF)
        far_fallen = (shifted(FALLEN_XY, dx=400), FULL_CONF)

        tracker.update([(FALLEN_XY, FULL_CONF), far_standing], now=0.0)
        events = tracker.update([(FALLEN_XY, FULL_CONF), far_fallen], now=3.0)

        # Only the person who has been down for the full window fires.
        self.assertEqual(len(events), 1)

    def test_short_missed_detection_is_tolerated(self):
        tracker = self.make_tracker(max_missing_updates=1)
        tracker.update([(FALLEN_XY, FULL_CONF)], now=0.0)
        # Detector misses this person for one sampled frame (occlusion).
        self.assertEqual(tracker.update([], now=1.0), [])

        events = tracker.update([(FALLEN_XY, FULL_CONF)], now=3.0)

        self.assertEqual(len(events), 1)

    def test_stale_track_is_dropped_after_too_many_missed_updates(self):
        tracker = self.make_tracker(max_missing_updates=1)
        tracker.update([(FALLEN_XY, FULL_CONF)], now=0.0)
        tracker.update([], now=1.0)
        tracker.update([], now=2.0)
        self.assertEqual(tracker.active_track_count, 0)

    def test_time_moving_backwards_raises(self):
        tracker = self.make_tracker()
        tracker.update([(FALLEN_XY, FULL_CONF)], now=5.0)
        with self.assertRaises(ValueError):
            tracker.update([(FALLEN_XY, FULL_CONF)], now=4.0)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            fall.FallTracker(persistence_seconds=0)
        with self.assertRaises(ValueError):
            fall.FallTracker(span_ratio_threshold=-1)

    def test_description_is_explicitly_camera_level(self):
        tracker = self.make_tracker()
        tracker.update([(FALLEN_XY, FULL_CONF)], now=0.0)
        event = tracker.update([(FALLEN_XY, FULL_CONF)], now=3.0)[0]

        description = fall.describe(event)

        self.assertIn("camera view", description)
        self.assertIn("temporary track 1", description)


class CameraFallAlertApiTests(APITestCase):
    def test_existing_alert_api_accepts_camera_level_fall_event(self):
        officer = User.objects.create_user(
            email="fall-test@example.com",
            password="test-password",
        )
        officer.role = Role.SAFETY_OFFICER
        officer.save(update_fields=["role"])
        self.client.force_authenticate(officer)

        # SQLite (used by the isolated test settings) does not implement the
        # JSON `contains` lookup used for camera-to-zone resolution; that is
        # a genuine PostgreSQL/SQLite gap, not something specific to fall
        # detection, and test_inactivity.py hits and documents the same
        # thing. Mocking only that lookup keeps this test focused on the
        # alert ingestion contract and camera id persistence.
        with patch("alerts.serializers.Zone.objects.for_camera") as for_camera:
            for_camera.return_value.first.return_value = None
            event = {"track_id": 3, "collapsed_seconds": 3.4}
            response = self.client.post(
                "/api/alerts/",
                fall.alert_payload(event, "CAM-BAY-2"),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alert = Alert.objects.get(pk=response.data["id"])
        self.assertEqual(alert.alert_type, AlertType.FALL)
        self.assertEqual(alert.severity, Severity.CRITICAL)
        self.assertEqual(alert.source, AlertSource.AI_CAMERA)
        self.assertEqual(alert.camera_id, "CAM-BAY-2")
        self.assertIsNone(alert.worker)
