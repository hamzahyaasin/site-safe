"""Camera-side worker activity: sightings, idle start/end, outbox routing."""

from __future__ import annotations

import time
import unittest
from datetime import datetime

import inactivity
import inference


class ActivityEventTests(unittest.TestCase):
    def test_payload_and_routing(self):
        p = inference.activity_payload("SIGHTING", "SSW1:abc", "CAM-01", 1_760_000_000.0)
        self.assertEqual(p["_endpoint"], "camera-activity")
        self.assertEqual(datetime.fromisoformat(p["occurred_at"]).timestamp(), 1_760_000_000.0)

        class Session:
            def __init__(self):
                self.calls = []

            def post(self, url, json, timeout):
                self.calls.append((url, json))

                class R:
                    status_code = 200

                return R()

        session = Session()
        send = inference.make_sender(session)
        send(p)
        send({"alert_type": "FALL"})
        (url1, body1), (url2, _) = session.calls
        self.assertTrue(url1.endswith("/v1/camera-activity/"))
        self.assertNotIn("_endpoint", body1)
        self.assertIn("_endpoint", p, "the queued payload must not be mutated")
        self.assertTrue(url2.endswith("/v1/camera-events/"))

    def test_sighting_throttle(self):
        t = inference.SightingThrottle(interval=60)
        self.assertTrue(t.due("A", 0))
        self.assertFalse(t.due("A", 30))
        self.assertTrue(t.due("B", 30))
        self.assertTrue(t.due("A", 61))

    def test_wall_clock(self):
        perf = time.perf_counter()
        self.assertAlmostEqual(inference.wall_clock(perf - 10), time.time() - 10, delta=0.05)
        # With --video-clock the pipeline's time is the clip position: an event
        # 30 s before the current frame happened 30 s before now.
        self.assertAlmostEqual(inference.wall_clock(12.0, 42.0), time.time() - 30, delta=0.05)

    def test_inactivity_reports_resumed_movement(self):
        tracker = inactivity.InactivityTracker(timeout_seconds=5, movement_threshold=10)
        box = (100, 100, 150, 250)
        events = []
        for t in range(0, 8):
            events += tracker.update([box], now=float(t))
            self.assertEqual(tracker.resumed, [])
        self.assertEqual(len(events), 1)
        moved = (160, 100, 210, 250)
        tracker.update([moved], now=8.0)
        self.assertEqual(len(tracker.resumed), 1)
        self.assertEqual(tracker.resumed[0]["resumed_at"], 8.0)
        tracker.update([moved], now=9.0)
        self.assertEqual(tracker.resumed, [], "reported once per resumption")

    def test_moving_without_prior_idle_is_not_a_resumption(self):
        tracker = inactivity.InactivityTracker(timeout_seconds=5, movement_threshold=10)
        tracker.update([(100, 100, 150, 250)], now=0.0)
        tracker.update([(200, 100, 250, 250)], now=1.0)
        self.assertEqual(tracker.resumed, [])


if __name__ == "__main__":
    unittest.main()
