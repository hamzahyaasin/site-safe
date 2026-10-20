"""Fire/smoke confirmation: persistence, gap tolerance, latching and re-arming."""

from __future__ import annotations

import unittest

import fire_detection as fd
import inference

AREA = 640 * 480
BIG = (100.0, 100.0, 200.0, 220.0)


def run(tracker, frames):
    """frames: list of (t, detections). Returns all events."""
    events = []
    for t, dets in frames:
        events += tracker.update(dets, AREA, now=t)
    return events


class FireTrackerTests(unittest.TestCase):
    def test_single_frame_flash_is_ignored(self):
        t = fd.FireTracker(persistence_seconds=2)
        self.assertEqual(run(t, [(0, [("fire", 0.9, BIG)]), (0.5, []), (2.0, []), (3.0, [])]), [])

    def test_sustained_fire_confirms_once(self):
        t = fd.FireTracker(persistence_seconds=2)
        frames = [(i * 0.5, [("fire", 0.6 + i * 0.01, BIG)]) for i in range(20)]
        events = run(t, frames)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["class"], "fire")
        self.assertGreaterEqual(events[0]["seen_seconds"], 2)
        self.assertAlmostEqual(events[0]["confidence"], 0.6 + 4 * 0.01, places=3)

    def test_short_gaps_tolerated_long_gap_restarts(self):
        t = fd.FireTracker(persistence_seconds=2, max_gap_seconds=1)
        # flicker with 0.5s gaps still confirms
        self.assertEqual(len(run(t, [(0, [("fire", 0.8, BIG)]), (0.5, []), (1.0, [("fire", 0.8, BIG)]), (2.0, [("fire", 0.8, BIG)])])), 1)
        t2 = fd.FireTracker(persistence_seconds=2, max_gap_seconds=1)
        # a 1.5s gap restarts the clock
        self.assertEqual(run(t2, [(0, [("fire", 0.8, BIG)]), (1.5, [("fire", 0.8, BIG)]), (3.0, [])]), [])

    def test_rearms_only_after_scene_clear(self):
        t = fd.FireTracker(persistence_seconds=1, clear_seconds=10)
        burn = [(i, [("fire", 0.8, BIG)]) for i in range(5)]
        self.assertEqual(len(run(t, burn)), 1)
        # brief disappearance does not re-alert
        self.assertEqual(run(t, [(6, []), (8, [("fire", 0.8, BIG)]), (9.5, [("fire", 0.8, BIG)])]), [])
        # clear for 10s, then a new fire alerts again
        again = run(t, [(12, []), (20, []), (21, [("fire", 0.8, BIG)]), (21.6, [("fire", 0.8, BIG)]), (22.2, [("fire", 0.8, BIG)])])
        self.assertEqual([e["class"] for e in again], ["fire"])

    def test_fire_and_smoke_independent(self):
        t = fd.FireTracker(persistence_seconds=1)
        both = lambda fire_name: [("smoke", 0.5, BIG), (fire_name, 0.7, BIG)]  # noqa: E731
        events = run(t, [(0, both("Fire")), (0.6, both("flame")), (1.2, both("fire"))])
        self.assertEqual(sorted(e["class"] for e in events), ["fire", "smoke"])

    def test_tiny_boxes_and_other_classes_ignored(self):
        t = fd.FireTracker(persistence_seconds=1)
        tiny = (0.0, 0.0, 5.0, 5.0)
        self.assertEqual(run(t, [(0, [("fire", 0.9, tiny), ("person", 0.9, BIG)]), (2, [("fire", 0.9, tiny)])]), [])

    def test_payload(self):
        event = {"class": "smoke", "confidence": 0.71234, "seen_seconds": 2.4, "box": BIG, "box_fraction": 0.04}
        p = fd.alert_payload(event, "CAM-02")
        self.assertEqual((p["alert_type"], p["severity"], p["confidence"]), ("SMOKE", "HIGH", 0.7123))
        self.assertIn("Smoke detected for 2.4s", p["description"])

    def test_cli_flags(self):
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["inference.py", "--fire-conf", "0.6", "--no-fire"]):
            args = inference.parse_args()
        self.assertEqual((args.fire_conf, args.no_fire), (0.6, True))


if __name__ == "__main__":
    unittest.main()
