"""FR-05: one alert per person per PPE violation episode.

Acceptance criterion: two people with the same violation give two alerts;
a single-frame flicker gives none.

    python -m unittest test_ppe_episodes
"""

import unittest

import ppe_episodes

FPS = 10
STEP = 1 / FPS
LEFT = (100.0, 50.0, 140.0, 90.0)
RIGHT = (400.0, 50.0, 440.0, 90.0)


def shifted(box, dx):
    return (box[0] + dx, box[1], box[2] + dx, box[3])


def run(tracker, frames, start=0.0):
    """Feed a list of per-frame detection lists at FPS; return all events."""
    events = []
    for i, dets in enumerate(frames):
        events += tracker.update(dets, now=start + i * STEP)
    return events


def seen(box, cls="no-helmet", conf=0.6, badge=None, person=None):
    return (cls, conf, box, badge, person)


class AcceptanceTests(unittest.TestCase):
    def test_two_people_with_same_violation_give_two_alerts(self):
        t = ppe_episodes.EpisodeTracker()
        events = run(t, [[seen(LEFT), seen(RIGHT)]] * (2 * FPS))
        self.assertEqual(len(events), 2)
        self.assertEqual({e["class"] for e in events}, {"no-helmet"})
        self.assertNotEqual(events[0]["track_id"], events[1]["track_id"])

    def test_single_frame_flicker_gives_none(self):
        t = ppe_episodes.EpisodeTracker()
        self.assertEqual(run(t, [[seen(LEFT)]] + [[]] * (2 * FPS)), [])

    def test_repeated_isolated_flickers_never_confirm(self):
        # One detection every second never builds a continuous episode.
        t = ppe_episodes.EpisodeTracker()
        frames = [[seen(LEFT)] if i % FPS == 0 else [] for i in range(10 * FPS)]
        self.assertEqual(run(t, frames), [])


class EpisodeTests(unittest.TestCase):
    def test_continuous_violation_alerts_once(self):
        t = ppe_episodes.EpisodeTracker()
        events = run(t, [[seen(LEFT)]] * (60 * FPS))
        self.assertEqual(len(events), 1)
        self.assertGreaterEqual(events[0]["seen_seconds"], ppe_episodes.DEFAULT_PERSISTENCE_SECONDS)

    def test_alert_waits_for_persistence(self):
        t = ppe_episodes.EpisodeTracker(persistence_seconds=1.0)
        self.assertEqual(run(t, [[seen(LEFT)]] * 5), [])  # 0.4 s
        self.assertEqual(len(run(t, [[seen(LEFT)]] * 10, start=0.5)), 1)

    def test_clear_then_reappear_is_a_new_alert(self):
        t = ppe_episodes.EpisodeTracker(clear_seconds=5.0)
        first = run(t, [[seen(LEFT)]] * (2 * FPS))
        gap = run(t, [[]] * (6 * FPS), start=2.0)
        again = run(t, [[seen(LEFT)]] * (2 * FPS), start=8.0)
        self.assertEqual((len(first), len(gap), len(again)), (1, 0, 1))

    def test_brief_loss_does_not_realert(self):
        # Occlusion shorter than clear_seconds continues the same episode.
        t = ppe_episodes.EpisodeTracker(clear_seconds=5.0)
        run(t, [[seen(LEFT)]] * (2 * FPS))
        run(t, [[]] * (3 * FPS), start=2.0)
        self.assertEqual(run(t, [[seen(LEFT)]] * (2 * FPS), start=5.0), [])

    def test_person_moving_keeps_one_episode(self):
        t = ppe_episodes.EpisodeTracker()
        frames = [[seen(shifted(LEFT, 8 * i))] for i in range(5 * FPS)]
        self.assertEqual(len(run(t, frames)), 1)

    def test_different_violations_of_one_person_alert_separately(self):
        t = ppe_episodes.EpisodeTracker()
        vest = (100.0, 90.0, 160.0, 200.0)
        events = run(t, [[seen(LEFT), seen(vest, cls="no-vest")]] * (2 * FPS))
        self.assertEqual(sorted(e["class"] for e in events), ["no-helmet", "no-vest"])

    def test_peak_confidence_reported(self):
        t = ppe_episodes.EpisodeTracker()
        frames = [[seen(LEFT, conf=c)] for c in (0.3, 0.9, 0.4, 0.5, 0.4, 0.3, 0.4, 0.3, 0.4, 0.3, 0.4, 0.3)]
        (event,) = run(t, frames)
        self.assertEqual(event["confidence"], 0.9)


class BadgeTests(unittest.TestCase):
    def test_identified_worker_who_jumps_keeps_one_episode(self):
        # A badge match survives a jump too large for distance matching.
        t = ppe_episodes.EpisodeTracker(clear_seconds=5.0)
        run(t, [[seen(LEFT, badge="SSW1:ali")]] * (2 * FPS))
        self.assertEqual(run(t, [[seen(RIGHT, badge="SSW1:ali")]] * (2 * FPS), start=2.0), [])

    def test_two_identified_workers_close_together_alert_separately(self):
        t = ppe_episodes.EpisodeTracker()
        near = shifted(LEFT, 20)
        events = run(t, [[seen(LEFT, badge="SSW1:ali"), seen(near, badge="SSW1:sara")]] * (2 * FPS))
        self.assertEqual(sorted(e["badge"] for e in events), ["SSW1:ali", "SSW1:sara"])

    def test_badge_learned_mid_episode_is_reported(self):
        t = ppe_episodes.EpisodeTracker()
        frames = [[seen(LEFT)]] * 3 + [[seen(LEFT, badge="SSW1:ali")]] * (2 * FPS)
        (event,) = run(t, frames)
        self.assertEqual(event["badge"], "SSW1:ali")

    def test_other_workers_track_is_not_taken(self):
        # Sara appearing where Ali's open episode was does not hide her violation.
        t = ppe_episodes.EpisodeTracker(clear_seconds=5.0)
        run(t, [[seen(LEFT, badge="SSW1:ali")]] * (2 * FPS))
        events = run(t, [[seen(LEFT, badge="SSW1:sara")]] * (2 * FPS), start=2.5)
        self.assertEqual([e["badge"] for e in events], ["SSW1:sara"])


class DuplicateBoxTests(unittest.TestCase):
    """Boxes recorded from one person in a live webcam run (640x360 frames)."""

    VEST_OUTER = (125.0, 239.0, 475.0, 359.0)
    VEST_INNER = (196.0, 238.0, 416.0, 359.0)  # IoU 0.63 with VEST_OUTER
    HELMET_A = (279.0, 114.0, 384.0, 166.0)
    HELMET_B = (282.0, 93.0, 385.0, 161.0)  # IoU 0.63 with HELMET_A
    HELMET_C = (260.0, 103.0, 384.0, 157.0)
    HELMET_D = (264.0, 74.0, 373.0, 148.0)  # IoU 0.50 with HELMET_C

    def one_person(self):
        return [
            seen(self.VEST_OUTER, cls="no-vest", conf=0.64),
            seen(self.VEST_INNER, cls="no-vest", conf=0.55),
            seen(self.HELMET_A, conf=0.37),
            seen(self.HELMET_B, conf=0.22),
        ]

    def test_duplicate_boxes_of_one_person_give_one_alert_per_item(self):
        t = ppe_episodes.EpisodeTracker()
        events = run(t, [self.one_person()] * (2 * FPS))
        self.assertEqual(sorted(e["class"] for e in events), ["no-helmet", "no-vest"])

    def test_least_overlapping_live_pair_is_merged(self):
        merged = ppe_episodes.merge_duplicates([seen(self.HELMET_C, conf=0.6), seen(self.HELMET_D, conf=0.45)])
        self.assertEqual(merged, [seen(self.HELMET_C, conf=0.6)])

    def test_flickering_duplicate_does_not_reopen_episodes(self):
        # The weak box drops in and out for a minute; only one alert per item.
        t = ppe_episodes.EpisodeTracker()
        frames = []
        for i in range(60 * FPS):
            frame = self.one_person()[:3]
            if (i // (7 * FPS)) % 2:  # weak helmet box present in alternate 7 s spells
                frame.append(seen(self.HELMET_B, conf=0.22))
            frames.append(frame)
        self.assertEqual(len(run(t, frames)), 2)

    def test_merge_keeps_badge_from_weaker_box(self):
        merged = ppe_episodes.merge_duplicates([seen(self.HELMET_A, conf=0.37), seen(self.HELMET_B, conf=0.22, badge="SSW1:ali")])
        self.assertEqual(merged, [seen(self.HELMET_A, conf=0.37, badge="SSW1:ali")])

    def test_overlapping_boxes_with_different_badges_stay_apart(self):
        dets = [seen(self.HELMET_A, badge="SSW1:ali"), seen(self.HELMET_B, badge="SSW1:sara")]
        self.assertEqual(len(ppe_episodes.merge_duplicates(dets)), 2)

    def test_different_classes_are_not_merged(self):
        dets = [seen(self.HELMET_A, cls="no-helmet"), seen(self.HELMET_A, cls="no-goggles")]
        self.assertEqual(len(ppe_episodes.merge_duplicates(dets)), 2)

    # Second live run: one head as three boxes, and a second person's
    # shoulder at the left edge of the frame.
    HEAD_MID = (265.0, 89.0, 389.0, 153.0)
    HEAD_TOP = (275.0, 60.0, 379.0, 137.0)
    HEAD_TALL = (265.0, 89.0, 388.0, 218.0)  # IoU 0.26 with HEAD_TOP, centre inside it
    MY_VEST = (176.0, 237.0, 506.0, 360.0)
    EDGE_VEST = (0.0, 233.0, 105.0, 358.0)

    def test_three_box_head_gives_one_alert_when_middle_box_drops_out(self):
        t = ppe_episodes.EpisodeTracker()
        frames = []
        for i in range(20 * FPS):
            frame = [seen(self.HEAD_TOP, conf=0.30), seen(self.HEAD_TALL, conf=0.28)]
            if i % 3:  # the strongest box is missed every third frame
                frame.append(seen(self.HEAD_MID, conf=0.47))
            frames.append(frame)
        self.assertEqual(len(run(t, frames)), 1)

    def test_second_person_at_frame_edge_is_a_second_alert(self):
        t = ppe_episodes.EpisodeTracker()
        frame = [seen(self.MY_VEST, cls="no-vest", conf=0.68), seen(self.EDGE_VEST, cls="no-vest", conf=0.41)]
        self.assertEqual(len(run(t, [frame] * (2 * FPS))), 2)

    def test_heads_side_by_side_stay_separate(self):
        right = shifted(self.HEAD_MID, 110)  # touching neighbour, no centre inside
        self.assertEqual(len(ppe_episodes.merge_duplicates([seen(self.HEAD_MID), seen(right)])), 2)

    def test_violation_back_within_clear_time_is_same_episode(self):
        t = ppe_episodes.EpisodeTracker()
        run(t, [[seen(LEFT)]] * (2 * FPS))
        run(t, [[]] * (20 * FPS), start=2.0)  # away 20 s, under the 30 s default
        self.assertEqual(run(t, [[seen(LEFT)]] * (2 * FPS), start=22.0), [])


class ValidationTests(unittest.TestCase):
    def test_rejects_invalid_settings(self):
        with self.assertRaises(ValueError):
            ppe_episodes.EpisodeTracker(min_hits=0)
        with self.assertRaises(ValueError):
            ppe_episodes.EpisodeTracker(clear_seconds=0)
        with self.assertRaises(ValueError):
            ppe_episodes.EpisodeTracker(persistence_seconds=-1)


if __name__ == "__main__":
    unittest.main()


class PersonAssociationTests(unittest.TestCase):
    """Violations are tied to the tracked person whose box contains them (live webcam, 27 Oct)."""

    def test_head_box_jumping_within_one_person_alerts_once(self):
        # A webcam head box moved more than its own size as the person leaned:
        # by box distance alone this became a second episode and a second alert.
        t = ppe_episodes.EpisodeTracker()
        moved = shifted(LEFT, 70)
        frames = [[seen(LEFT, person=1)]] * (2 * FPS) + [[seen(moved, person=1)]] * (3 * FPS)
        self.assertEqual(len(run(t, frames)), 1)

    def test_without_person_the_jump_is_a_new_episode(self):
        # Documents the fallback: with no person detector, box distance decides.
        t = ppe_episodes.EpisodeTracker()
        frames = [[seen(LEFT)]] * (2 * FPS) + [[seen(shifted(LEFT, 70))]] * (3 * FPS)
        self.assertEqual(len(run(t, frames)), 2)

    def test_two_people_side_by_side_still_alert_twice(self):
        t = ppe_episodes.EpisodeTracker()
        near = shifted(LEFT, 30)  # within one box size of LEFT
        events = run(t, [[seen(LEFT, person=1), seen(near, person=2)]] * (2 * FPS))
        self.assertEqual(len(events), 2)

    def test_two_boxes_of_one_class_on_one_person_are_one_violation(self):
        # e.g. both hands without gloves: one person, one episode, one alert.
        t = ppe_episodes.EpisodeTracker()
        right_hand = shifted(LEFT, 200)
        frames = [[seen(LEFT, "no-gloves", person=1), seen(right_hand, "no-gloves", person=1)]] * (2 * FPS)
        self.assertEqual(len(run(t, frames)), 1)

    def test_episode_of_another_present_person_is_not_taken_by_distance(self):
        t = ppe_episodes.EpisodeTracker()
        run(t, [[seen(LEFT, person=1)]] * (2 * FPS))
        # Person 2 appears right where person 1's box was; person 1 is still tracked.
        events = run(t, [[seen(LEFT, person=1), seen(shifted(LEFT, 10), person=2)]] * (2 * FPS), start=2.0)
        self.assertEqual(len(events), 1, "person 2 gets their own episode")

    def test_new_person_id_near_a_lost_persons_episode_continues_it(self):
        # The person detector lost the worker for a moment and re-found them
        # as a new track: same place, same violation, no second alert.
        t = ppe_episodes.EpisodeTracker()
        events = run(t, [[seen(LEFT, person=1)]] * (2 * FPS))
        events += run(t, [[]] * (2 * FPS), start=2.0)
        events += run(t, [[seen(shifted(LEFT, 5), person=7)]] * (2 * FPS), start=4.0)
        self.assertEqual(len(events), 1)
