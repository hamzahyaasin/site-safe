"""Unit tests for the camera-side vehicle-proximity decision logic.

The production module deliberately has no OpenCV, torch, or Ultralytics
dependency, so its geometry and persistence behavior can be exercised by the
standard Django test command used for the rest of the project.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.test import SimpleTestCase


AI_MODULE_DIR = Path(__file__).resolve().parents[2] / "ai-module"
if str(AI_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODULE_DIR))

import proximity  # noqa: E402  (path is intentionally prepared above)


PERSON = (0.0, 0.0, 20.0, 100.0)
NEAR_TRUCK = ((70.0, 0.0, 170.0, 100.0), "truck")
FAR_TRUCK = ((170.0, 0.0, 270.0, 100.0), "truck")


class ProximityGeometryTests(SimpleTestCase):
    def test_bbox_gap_handles_overlap_axis_gap_and_diagonal_gap(self):
        self.assertEqual(proximity.bbox_gap(PERSON, (10.0, 10.0, 30.0, 60.0)), 0.0)
        self.assertEqual(proximity.bbox_gap(PERSON, NEAR_TRUCK[0]), 50.0)
        self.assertAlmostEqual(
            proximity.bbox_gap(PERSON, (50.0, 140.0, 90.0, 180.0)),
            50.0,
        )

    def test_normalised_gap_is_scale_invariant_and_rejects_zero_height(self):
        self.assertEqual(proximity.normalised_gap(PERSON, NEAR_TRUCK[0]), 0.5)
        scaled_person = tuple(value * 2 for value in PERSON)
        scaled_vehicle = tuple(value * 2 for value in NEAR_TRUCK[0])
        self.assertEqual(proximity.normalised_gap(scaled_person, scaled_vehicle), 0.5)
        self.assertIsNone(
            proximity.normalised_gap((0.0, 5.0, 10.0, 5.0), NEAR_TRUCK[0])
        )

    def test_closest_proximity_selects_nearest_pair_within_threshold(self):
        event = proximity.closest_proximity(
            [PERSON], [FAR_TRUCK, NEAR_TRUCK], threshold=1.0
        )
        self.assertIsNotNone(event)
        self.assertEqual(event["vehicle_label"], "truck")
        self.assertEqual(event["normalised_gap"], 0.5)
        self.assertFalse(event["overlapping"])

    def test_closest_proximity_returns_none_when_every_pair_is_too_far(self):
        self.assertIsNone(
            proximity.closest_proximity([PERSON], [FAR_TRUCK], threshold=1.0)
        )

    def test_event_severity_and_description_reflect_overlap(self):
        event = proximity.closest_proximity(
            [PERSON], [((10.0, 10.0, 30.0, 80.0), "car")], threshold=1.0
        )
        self.assertEqual(proximity.severity_for(event), "CRITICAL")
        self.assertIn("car", proximity.describe(event))
        self.assertIn("overlapping", proximity.describe(event))


class ProximityTrackerTests(SimpleTestCase):
    def test_tracker_waits_for_persistence_threshold(self):
        tracker = proximity.ProximityTracker(threshold=1.0, persistence=3)
        self.assertIsNone(tracker.update([PERSON], [NEAR_TRUCK]))
        self.assertIsNone(tracker.update([PERSON], [NEAR_TRUCK]))
        self.assertIsNotNone(tracker.update([PERSON], [NEAR_TRUCK]))

    def test_tracker_resets_an_incomplete_streak_when_condition_clears(self):
        tracker = proximity.ProximityTracker(threshold=1.0, persistence=2)
        self.assertIsNone(tracker.update([PERSON], [NEAR_TRUCK]))
        self.assertIsNone(tracker.update([PERSON], [FAR_TRUCK]))
        self.assertIsNone(tracker.update([PERSON], [NEAR_TRUCK]))
        self.assertIsNotNone(tracker.update([PERSON], [NEAR_TRUCK]))

    def test_tracker_rearms_only_after_condition_clears(self):
        tracker = proximity.ProximityTracker(threshold=1.0, persistence=1)
        self.assertIsNotNone(tracker.update([PERSON], [NEAR_TRUCK]))
        self.assertIsNone(tracker.update([PERSON], [NEAR_TRUCK]))
        self.assertIsNone(tracker.update([PERSON], [FAR_TRUCK]))
        self.assertIsNotNone(tracker.update([PERSON], [NEAR_TRUCK]))

    def test_split_detections_keeps_people_and_supported_vehicles_only(self):
        boxes = [PERSON, NEAR_TRUCK[0], FAR_TRUCK[0], (1.0, 2.0, 3.0, 4.0)]
        persons, vehicles = proximity.split_detections(boxes, [0, 7, 2, 16])
        self.assertEqual(persons, [PERSON])
        self.assertEqual(vehicles, [(NEAR_TRUCK[0], "truck"), (FAR_TRUCK[0], "car")])
