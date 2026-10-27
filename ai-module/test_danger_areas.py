"""FR-32: one alert per person per entry into a danger area drawn on the camera picture."""

import unittest

import danger_areas as da

AREA = da.Area(7, "Crane swing", ((0.2, 0.5), (0.6, 0.5), (0.6, 0.95), (0.2, 0.95)), "CRITICAL")
INSIDE = (0.4, 0.8)
OUTSIDE = (0.8, 0.8)
STEP = 0.2  # the person detector samples every third frame


def run(tracker, frames, start=0.0, areas=(AREA,)):
    events = []
    for i, people in enumerate(frames):
        events += tracker.update(people, list(areas), now=start + i * STEP)
    return events


class GeometryTests(unittest.TestCase):
    def test_feet_not_box_centre_decide(self):
        # A tall person standing just above the area: the box centre is outside, the feet inside.
        box = (500.0, 40.0, 560.0, 600.0)
        self.assertEqual(da.foot_point(box, 1000, 700), (0.53, 600 / 700))
        self.assertTrue(da.contains(AREA.polygon, da.foot_point(box, 1000, 700)))
        self.assertFalse(da.contains(AREA.polygon, (0.53, 320 / 700)), "box centre is above the area")

    def test_concave_polygon(self):
        l_shape = ((0, 0), (1, 0), (1, 0.3), (0.3, 0.3), (0.3, 1), (0, 1))
        self.assertTrue(da.contains(l_shape, (0.1, 0.9)))
        self.assertFalse(da.contains(l_shape, (0.8, 0.8)))

    def test_parse_skips_malformed_areas(self):
        areas = da.parse_areas(
            [
                {"id": 1, "name": "A", "polygon": [[0, 0], [1, 0], [1, 1]], "severity": "HIGH"},
                {"id": 2, "name": "two points", "polygon": [[0, 0], [1, 1]]},
                {"id": 3, "polygon": [[0, 0], [1, 0], [1, 1]]},
                {"id": "x", "name": "bad id", "polygon": [[0, 0], [1, 0], [1, 1]]},
            ]
        )
        self.assertEqual([a.id for a in areas], [1])
        self.assertEqual(da.parse_areas(None), [])


class EntryTests(unittest.TestCase):
    def test_staying_inside_alerts_once(self):
        t = da.DangerAreaTracker()
        events = run(t, [[(1, INSIDE)]] * 50)
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]["area"], events[0]["severity"], events[0]["person"]), ("Crane swing", "CRITICAL", 1))
        self.assertGreaterEqual(events[0]["seconds_inside"], da.DEFAULT_PERSISTENCE_SECONDS)
        self.assertEqual(t.occupied, {7})

    def test_passing_a_corner_raises_nothing(self):
        t = da.DangerAreaTracker()
        self.assertEqual(run(t, [[(1, INSIDE)], [(1, INSIDE)], [(1, OUTSIDE)]] + [[(1, OUTSIDE)]] * 20), [])
        self.assertEqual(t.occupied, set())

    def test_stepping_out_restarts_an_unconfirmed_entry(self):
        t = da.DangerAreaTracker()
        frames = [[(1, INSIDE)]] * 3 + [[(1, OUTSIDE)]] * 8 + [[(1, INSIDE)]] * 2
        self.assertEqual(run(t, frames), [], "inside 0.4 s, out 1.6 s, inside 0.2 s: never 1 s in a row")

    def test_two_people_two_alerts(self):
        t = da.DangerAreaTracker()
        events = run(t, [[(1, INSIDE), (2, (0.3, 0.9))]] * 10)
        self.assertEqual(sorted(e["person"] for e in events), [1, 2])

    def test_re_alert_only_after_the_clear_time_outside(self):
        t = da.DangerAreaTracker()
        events = run(t, [[(1, INSIDE)]] * 10)
        events += run(t, [[(1, OUTSIDE)]] * 20 + [[(1, INSIDE)]] * 10, start=2.0)  # 4 s out: same entry
        self.assertEqual(len(events), 1)
        events += run(t, [[(1, OUTSIDE)]] * 60 + [[(1, INSIDE)]] * 10, start=10.0)  # 12 s out: new entry
        self.assertEqual(len(events), 2)

    def test_person_refound_under_a_new_id_is_not_alerted_again(self):
        t = da.DangerAreaTracker()
        events = run(t, [[(1, INSIDE)]] * 10)
        events += run(t, [[]] * 5, start=2.0)  # detector lost them
        events += run(t, [[(9, (0.42, 0.81))]] * 10, start=3.0)
        self.assertEqual(len(events), 1)

    def test_a_different_person_nearby_is_alerted(self):
        # Person 1 is still tracked, so person 2 next to them is someone else.
        t = da.DangerAreaTracker()
        run(t, [[(1, INSIDE)]] * 10)
        events = run(t, [[(1, INSIDE), (2, (0.42, 0.81))]] * 10, start=2.0)
        self.assertEqual([e["person"] for e in events], [2])

    def test_removed_or_switched_off_area_is_forgotten(self):
        t = da.DangerAreaTracker()
        run(t, [[(1, INSIDE)]] * 10)
        self.assertEqual(run(t, [[(1, INSIDE)]] * 10, start=2.0, areas=()), [])
        self.assertEqual(t.entries, {})
        self.assertEqual(t.occupied, set())

    def test_payload(self):
        event = {"area": "Crane swing", "severity": "CRITICAL", "seconds_inside": 1.2}
        p = da.alert_payload(event, "CAM-09")
        self.assertEqual((p["alert_type"], p["severity"], p["camera_id"]), ("DANGER_AREA", "CRITICAL", "CAM-09"))
        self.assertIn("'Crane swing' on CAM-09", p["description"])


class PipelineTests(unittest.TestCase):
    def test_rules_poll_brings_the_areas(self):
        import inference

        class Session:
            def get(self, url, params, timeout):
                class R:
                    status_code = 200

                    def json(self):
                        return {"zone": "Crane", "rules": {}, "areas": [{"id": 7, "name": "Crane swing", "polygon": [[0.2, 0.5], [0.6, 0.5], [0.6, 0.95]], "severity": "CRITICAL"}]}

                return R()

        rules = inference.CameraRules(Session(), "CAM-09")
        self.assertTrue(rules.refresh())
        self.assertEqual([(a.id, a.name, a.severity) for a in rules.areas], [(7, "Crane swing", "CRITICAL")])
        self.assertLessEqual(inference.RULES_REFRESH_SECONDS, 15, "a new area takes effect quickly")

    def test_areas_are_drawn_and_named_in_the_banner(self):
        import numpy as np

        import inference

        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        inference.draw_danger_areas(frame, [AREA], occupied={7})
        self.assertGreater(frame[80, 80, 2], 0, "red fill inside an occupied area")
        self.assertEqual(frame[10, 190].tolist(), [0, 0, 0], "nothing outside")
        banner = np.zeros((100, 200, 3), dtype=np.uint8)
        inference.draw_status_bar(banner, [("no-helmet", 0.9)], danger_area="Crane swing")
        self.assertGreater(banner[5, 5, 2], banner[5, 5, 1], "red banner, outranking the PPE violation")


if __name__ == "__main__":
    unittest.main()
