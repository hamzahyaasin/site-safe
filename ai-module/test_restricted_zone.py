"""Unidentified people in a restricted zone: one ZONE_BREACH per person per stay."""

import unittest

import restricted_zone as rz

FEET = (0.5, 0.8)
STEP = 0.5


def run(watcher, frames, zone="Crane", start=0.0):
    """``frames``: per sample, a list of (track id, badge or None)."""
    events = []
    for i, people in enumerate(frames):
        sample = [(tid, FEET, badge) for tid, badge in people]
        events += watcher.update(sample, {tid for tid, _ in people}, zone, now=start + i * STEP)
    return events


class RestrictedZoneTests(unittest.TestCase):
    def test_unidentified_person_alerts_once_after_the_grace_period(self):
        w = rz.RestrictedZoneWatcher(grace_seconds=10)
        events = run(w, [[(1, None)]] * 20)  # 9.5 s
        self.assertEqual(events, [], "still within the grace period")
        events = run(w, [[(1, None)]] * 40, start=10.0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["zone"], "Crane")
        self.assertGreaterEqual(events[0]["seconds_in_view"], 10)

    def test_badge_read_within_the_grace_period_raises_nothing(self):
        w = rz.RestrictedZoneWatcher(grace_seconds=10)
        frames = [[(1, None)]] * 10 + [[(1, "SSW1:abc")]] + [[(1, None)]] * 40
        self.assertEqual(run(w, frames), [], "the badge lapsing later does not make them unidentified")

    def test_only_the_unidentified_one_of_two_people_alerts(self):
        w = rz.RestrictedZoneWatcher(grace_seconds=2)
        events = run(w, [[(1, "SSW1:abc"), (2, None)]] * 10)
        self.assertEqual([e["person"] for e in events], [2])

    def test_zone_not_restricted_raises_nothing_and_forgets_stays(self):
        w = rz.RestrictedZoneWatcher(grace_seconds=2)
        self.assertEqual(run(w, [[(1, None)]] * 10, zone=None), [])
        run(w, [[(1, None)]] * 3)
        run(w, [[(1, None)]], zone=None, start=1.5)
        self.assertEqual(run(w, [[(1, None)]] * 3, start=2.0), [], "the stay restarted after the zone changed")

    def test_again_only_after_leaving_view(self):
        w = rz.RestrictedZoneWatcher(grace_seconds=2)
        first = run(w, [[(1, None)]] * 10)
        gone = run(w, [[]] * 25, start=5.0)  # 12.5 s out of view
        back = run(w, [[(3, None)]] * 10, start=17.5)
        self.assertEqual((len(first), gone, len(back)), (1, [], 1))

    def test_feet_on_the_bottom_edge_count(self):
        w = rz.RestrictedZoneWatcher(grace_seconds=1)
        events = []
        for i in range(5):
            events += w.update([(1, (0.5, 1.0), None)], {1}, "Crane", now=i * STEP)
        self.assertEqual(len(events), 1)

    def test_payload(self):
        payload = rz.alert_payload({"zone": "Crane", "person": 1, "seconds_in_view": 10.5}, "CAM-02")
        self.assertEqual((payload["alert_type"], payload["severity"], payload["camera_id"]), ("ZONE_BREACH", "HIGH", "CAM-02"))
        self.assertIn("Unidentified person in restricted zone Crane", payload["description"])


if __name__ == "__main__":
    unittest.main()
