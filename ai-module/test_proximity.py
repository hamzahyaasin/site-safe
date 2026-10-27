"""Vehicle proximity: geometry, and one alert per person per encounter with a vehicle."""

import unittest

import proximity

PERSON = (0.0, 0.0, 20.0, 100.0)
NEAR_TRUCK = ((70.0, 0.0, 170.0, 100.0), "truck")
FAR_TRUCK = ((170.0, 0.0, 270.0, 100.0), "truck")
ON_TRUCK = ((10.0, 10.0, 90.0, 90.0), "truck")
# A second worker far from the first, beside their own vehicle.
OTHER = (500.0, 0.0, 520.0, 100.0)
OTHER_CAR = ((540.0, 0.0, 640.0, 100.0), "car")
STEP = 0.3  # the person/vehicle detector samples every third frame (10 fps clip)


def run(tracker, frames, start=0.0):
    """Feed (people, vehicles) samples STEP apart; return the confirmed events."""
    events = []
    for i, (people, vehicles) in enumerate(frames):
        events += tracker.update(people, vehicles, now=start + i * STEP)
    return events


class ProximityGeometryTests(unittest.TestCase):
    def test_bbox_gap_handles_overlap_axis_gap_and_diagonal_gap(self):
        self.assertEqual(proximity.bbox_gap(PERSON, (10.0, 10.0, 30.0, 60.0)), 0.0)
        self.assertEqual(proximity.bbox_gap(PERSON, NEAR_TRUCK[0]), 50.0)
        self.assertAlmostEqual(proximity.bbox_gap(PERSON, (50.0, 140.0, 90.0, 180.0)), 50.0)

    def test_normalised_gap_is_scale_invariant_and_rejects_zero_height(self):
        self.assertEqual(proximity.normalised_gap(PERSON, NEAR_TRUCK[0]), 0.5)
        scaled_person = tuple(value * 2 for value in PERSON)
        scaled_vehicle = tuple(value * 2 for value in NEAR_TRUCK[0])
        self.assertEqual(proximity.normalised_gap(scaled_person, scaled_vehicle), 0.5)
        self.assertIsNone(proximity.normalised_gap((0.0, 5.0, 10.0, 5.0), NEAR_TRUCK[0]))

    def test_closest_proximity_selects_nearest_pair_within_threshold(self):
        event = proximity.closest_proximity([PERSON], [FAR_TRUCK, NEAR_TRUCK], threshold=1.0)
        self.assertIsNotNone(event)
        self.assertEqual(event["vehicle_label"], "truck")
        self.assertEqual(event["normalised_gap"], 0.5)
        self.assertFalse(event["overlapping"])

    def test_closest_proximity_returns_none_when_every_pair_is_too_far(self):
        self.assertIsNone(proximity.closest_proximity([PERSON], [FAR_TRUCK], threshold=1.0))

    def test_event_severity_and_description_reflect_overlap(self):
        event = proximity.closest_proximity([PERSON], [((10.0, 10.0, 30.0, 80.0), "car")], threshold=1.0)
        self.assertEqual(proximity.severity_for(event), "CRITICAL")
        self.assertIn("car", proximity.describe(event))
        self.assertIn("overlapping", proximity.describe(event))

    def test_split_detections_keeps_people_and_supported_vehicles_only(self):
        boxes = [PERSON, NEAR_TRUCK[0], FAR_TRUCK[0], (1.0, 2.0, 3.0, 4.0)]
        persons, vehicles = proximity.split_detections(boxes, [0, 7, 2, 16])
        self.assertEqual(persons, [PERSON])
        self.assertEqual(vehicles, [(NEAR_TRUCK[0], "truck"), (FAR_TRUCK[0], "car")])


class EncounterTests(unittest.TestCase):
    def test_waits_for_persistence(self):
        t = proximity.ProximityTracker(persistence=3)
        self.assertEqual(run(t, [([(1, PERSON)], [NEAR_TRUCK])] * 2), [])
        events = run(t, [([(1, PERSON)], [NEAR_TRUCK])], start=0.6)
        self.assertEqual([(e["person"], e["vehicle_label"]) for e in events], [(1, "truck")])

    def test_a_single_spurious_box_raises_nothing(self):
        t = proximity.ProximityTracker(persistence=3)
        frames = [([(1, PERSON)], [NEAR_TRUCK])] + [([(1, PERSON)], [FAR_TRUCK])] * 10
        self.assertEqual(run(t, frames), [])

    def test_a_long_gap_restarts_an_unconfirmed_encounter(self):
        t = proximity.ProximityTracker(persistence=3)
        frames = [([(1, PERSON)], [NEAR_TRUCK])] * 2 + [([(1, PERSON)], [])] * 5 + [([(1, PERSON)], [NEAR_TRUCK])]
        self.assertEqual(run(t, frames), [], "near 2 samples, 1.5 s away, near 1 sample: never 3 in a row")

    def test_flickering_vehicle_alerts_once(self):
        # The 27 Oct live run: one worker beside a car the detector kept losing
        # for up to 4 s raised an alert every 15 s cooldown.
        t = proximity.ProximityTracker()
        near, lost = ([(1, PERSON)], [NEAR_TRUCK]), ([(1, PERSON)], [])
        frames = ([near] * 3 + [lost] * 13) * 40  # 192 s
        self.assertEqual(len(run(t, frames)), 1)

    def test_alerts_again_only_after_the_clear_time(self):
        t = proximity.ProximityTracker(clear_seconds=15.0)
        near, away = ([(1, PERSON)], [NEAR_TRUCK]), ([(1, PERSON)], [FAR_TRUCK])
        events = run(t, [near] * 5 + [away] * 40 + [near] * 5)  # 12 s away: same encounter
        self.assertEqual(len(events), 1)
        events += run(t, [away] * 60 + [near] * 5, start=15.0)  # 18 s away: a new one
        self.assertEqual(len(events), 2)

    def test_two_workers_two_alerts(self):
        t = proximity.ProximityTracker()
        events = run(t, [([(1, PERSON), (2, OTHER)], [NEAR_TRUCK, OTHER_CAR])] * 5)
        self.assertEqual(sorted(e["person"] for e in events), [1, 2])

    def test_reports_the_closest_point_and_its_severity(self):
        t = proximity.ProximityTracker(persistence=3)
        events = run(t, [([(1, PERSON)], [NEAR_TRUCK]), ([(1, PERSON)], [ON_TRUCK]), ([(1, PERSON)], [NEAR_TRUCK])])
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["overlapping"])
        self.assertEqual(proximity.severity_for(events[0]), "CRITICAL")

    def test_person_refound_under_a_new_id_is_not_alerted_again(self):
        t = proximity.ProximityTracker()
        run(t, [([(1, PERSON)], [NEAR_TRUCK])] * 5)
        moved = (5.0, 2.0, 25.0, 102.0)
        events = run(t, [([(7, moved)], [NEAR_TRUCK])] * 5, start=2.0)
        self.assertEqual(events, [])

    def test_someone_at_the_same_spot_later_is_someone_else(self):
        # 40-scene test video: a person beside a car at 28 s stood where another
        # had been beside a car at 14 s; only a recent loss counts as re-found.
        t = proximity.ProximityTracker()
        run(t, [([(1, PERSON)], [NEAR_TRUCK])] * 5)
        moved = (5.0, 2.0, 25.0, 102.0)
        events = run(t, [([(7, moved)], [NEAR_TRUCK])] * 5, start=1.2 + proximity.REFOUND_SECONDS + 1)
        self.assertEqual([e["person"] for e in events], [7])

    def test_someone_else_beside_a_tracked_worker_is_alerted(self):
        t = proximity.ProximityTracker()
        run(t, [([(1, PERSON)], [NEAR_TRUCK])] * 5)
        beside = (5.0, 2.0, 25.0, 102.0)
        events = run(t, [([(1, PERSON), (7, beside)], [NEAR_TRUCK])] * 5, start=2.0)
        self.assertEqual([e["person"] for e in events], [7])

    def test_reset_forgets_open_encounters(self):
        t = proximity.ProximityTracker()
        run(t, [([(1, PERSON)], [NEAR_TRUCK])] * 5)
        t.reset()
        self.assertEqual(len(run(t, [([(1, PERSON)], [NEAR_TRUCK])] * 5, start=2.0)), 1)


class PipelineTests(unittest.TestCase):
    def test_payload_names_the_badge_holder(self):
        import inference

        event = proximity.closest_proximity([PERSON], [ON_TRUCK], threshold=1.0)
        payload = inference.with_badge(inference.proximity_payload(event, "CAM-01"), "SSW1:abc")
        self.assertEqual(
            (payload["alert_type"], payload["severity"], payload["badge_code"]),
            ("VEHICLE_PROXIMITY", "CRITICAL", "SSW1:abc"),
        )


if __name__ == "__main__":
    unittest.main()
