"""QR badge parsing, decoding and person association."""

from __future__ import annotations

import unittest

import cv2
import numpy as np

import identity
import inference

ALI = "SSW1:aliBadge01"
SARA = "SSW1:saraBadge2"


def qr_frame(payloads_at: list[tuple[str, int, int]], size=(480, 640)) -> np.ndarray:
    """White frame with real QR codes drawn at (x, y) top-left positions."""
    frame = np.full((*size, 3), 255, dtype=np.uint8)
    encoder = cv2.QRCodeEncoder.create()
    for payload, x, y in payloads_at:
        qr = cv2.resize(encoder.encode(payload), (120, 120), interpolation=cv2.INTER_NEAREST)
        frame[y : y + 120, x : x + 120] = cv2.cvtColor(qr, cv2.COLOR_GRAY2BGR)
    return frame


class ParseTests(unittest.TestCase):
    def test_only_site_safe_badges(self):
        self.assertEqual(identity.parse_badge(ALI), ALI)
        self.assertIsNone(identity.parse_badge("https://example.com"))
        self.assertIsNone(identity.parse_badge("SSW1:"))
        self.assertIsNone(identity.parse_badge(None))


class DecoderTests(unittest.TestCase):
    def test_decodes_badge_and_ignores_other_qr(self):
        frame = qr_frame([(ALI, 60, 60), ("https://example.com", 400, 60)])
        hits = identity.QrDecoder().decode(frame)
        self.assertEqual([h[0] for h in hits], [ALI])
        cx, cy = hits[0][1]
        self.assertAlmostEqual(cx, 120, delta=15)
        self.assertAlmostEqual(cy, 120, delta=15)

    def test_small_badge_on_a_dark_background(self):
        # Regression: OpenCV's classic multi-code detector missed badges this size.
        frame = np.full((720, 1280, 3), 60, dtype=np.uint8)
        qr = cv2.copyMakeBorder(cv2.QRCodeEncoder.create().encode(ALI), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=255)
        frame[300:410, 600:710] = cv2.cvtColor(cv2.resize(qr, (110, 110), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
        self.assertEqual([h[0] for h in identity.QrDecoder().decode(frame)], [ALI])

    def test_blank_frame(self):
        self.assertEqual(identity.QrDecoder().decode(qr_frame([])), [])


class TrackerTests(unittest.TestCase):
    A = (0.0, 0.0, 100.0, 300.0)
    B = (200.0, 0.0, 300.0, 300.0)

    def test_badge_follows_person_between_sightings(self):
        t = identity.IdentityTracker()
        t.update([self.A], [(ALI, (50.0, 40.0))], now=0)
        moved = (10.0, 5.0, 110.0, 305.0)
        t.update([moved], [], now=1)
        self.assertEqual(t.identify_box((40.0, 20.0, 80.0, 60.0)), ALI)

    def test_two_people_identified_independently(self):
        t = identity.IdentityTracker()
        t.update([self.A, self.B], [(ALI, (50.0, 40.0)), (SARA, (250.0, 40.0))], now=0)
        self.assertEqual(t.identify((50.0, 150.0)), ALI)
        self.assertEqual(t.identify((250.0, 150.0)), SARA)

    def test_ambiguous_overlap_not_assigned(self):
        t = identity.IdentityTracker()
        overlapping = (50.0, 0.0, 150.0, 300.0)
        t.update([self.A, overlapping], [(ALI, (75.0, 40.0))], now=0)
        self.assertIsNone(t.identify((25.0, 150.0)))
        self.assertIsNone(t.identify((75.0, 150.0)))

    def test_identity_expires(self):
        t = identity.IdentityTracker(identity_ttl=5, track_ttl=3)
        t.update([self.A], [(ALI, (50.0, 40.0))], now=0)
        for now in (2, 4, 6):
            t.update([self.A], [], now=now)
        self.assertIsNone(t.identify((50.0, 150.0)))

    def test_lost_person_drops_identity(self):
        t = identity.IdentityTracker(track_ttl=3)
        t.update([self.A], [(ALI, (50.0, 40.0))], now=0)
        t.update([], [], now=4)
        t.update([self.A], [], now=5)
        self.assertIsNone(t.identify((50.0, 150.0)))

    def test_badge_moves_to_new_holder(self):
        t = identity.IdentityTracker()
        t.update([self.A, self.B], [(ALI, (50.0, 40.0))], now=0)
        t.update([self.A, self.B], [(ALI, (250.0, 40.0))], now=1)
        self.assertIsNone(t.identify((50.0, 150.0)))
        self.assertEqual(t.identify((250.0, 150.0)), ALI)

    def test_badge_on_helmet_above_box_still_assigned(self):
        t = identity.IdentityTracker()
        t.update([(0.0, 100.0, 100.0, 400.0)], [(ALI, (50.0, 80.0))], now=0)
        self.assertEqual(t.identify((50.0, 200.0)), ALI)


class BadgedViolationTests(unittest.TestCase):
    def test_each_box_gets_its_wearers_badge(self):
        t = identity.IdentityTracker()
        t.update([TrackerTests.A, TrackerTests.B], [(ALI, (50.0, 40.0)), (SARA, (250.0, 40.0))], now=0)
        dets = [
            ("no-helmet", 0.6, (30.0, 10.0, 70.0, 50.0)),
            ("no-helmet", 0.8, (230.0, 10.0, 270.0, 50.0)),
            ("no-helmet", 0.5, (500.0, 10.0, 540.0, 50.0)),
        ]
        out = inference.badged_violations(dets, t)
        self.assertEqual([v.badge for v in out], [ALI, SARA, None])
        self.assertEqual(len({out[0].person, out[1].person}), 2, "two people, two person ids")
        self.assertIsNone(out[2].person, "outside every person")

    def test_unidentified_boxes_stay_separate(self):
        # Two unidentified people must reach the episode tracker as two boxes.
        dets = [("no-vest", 0.4, (0, 0, 1, 1)), ("no-vest", 0.7, (5, 5, 6, 6))]
        self.assertEqual(
            inference.badged_violations(dets, None),
            [("no-vest", 0.4, (0, 0, 1, 1), None, None), ("no-vest", 0.7, (5, 5, 6, 6), None, None)],
        )

    def test_payload_carries_badge(self):
        self.assertEqual(inference.ppe_payload("no-helmet", 0.9, "CAM-01", ALI)["badge_code"], ALI)
        self.assertNotIn("badge_code", inference.ppe_payload("no-helmet", 0.9, "CAM-01"))
        self.assertNotIn("badge_code", inference.with_badge({"a": 1}, None))


if __name__ == "__main__":
    unittest.main()


class PersonIdTests(unittest.TestCase):
    """Stable person ids for other trackers (PPE episodes), badge or not."""

    def test_person_keeps_its_id_while_followed_and_boxes_resolve_to_it(self):
        t = identity.IdentityTracker()
        t.update([(100, 100, 200, 400), (400, 100, 500, 400)], [], now=0.0)
        ids = {tr.track_id for tr in t.tracks}
        self.assertEqual(len(ids), 2)
        left = t.person_at((130, 105, 170, 150))
        t.update([(110, 100, 210, 400), (400, 100, 500, 400)], [], now=0.1)
        self.assertEqual(t.person_at((140, 105, 180, 150)), left, "same person after moving")
        self.assertEqual(t.people(), ids)

    def test_head_box_above_the_person_box_still_belongs_to_them(self):
        t = identity.IdentityTracker()
        t.update([(100, 100, 200, 400)], [], now=0.0)
        head = (130, 70, 170, 105)  # centre at y=87.5, above y1=100 but inside the top margin
        self.assertIsNotNone(t.person_at(head))

    def test_ambiguous_or_outside_is_none(self):
        t = identity.IdentityTracker()
        t.update([(100, 100, 300, 400), (200, 100, 400, 400)], [], now=0.0)
        self.assertIsNone(t.person_at((240, 200, 260, 220)), "inside both people")
        self.assertIsNone(t.person_at((600, 200, 620, 220)), "inside nobody")

    def test_new_person_gets_a_new_id(self):
        t = identity.IdentityTracker(track_ttl=1.0)
        t.update([(100, 100, 200, 400)], [], now=0.0)
        first = t.person_at((140, 200, 160, 220))
        t.update([], [], now=2.0)  # lost
        t.update([(100, 100, 200, 400)], [], now=2.1)
        self.assertNotEqual(t.person_at((140, 200, 160, 220)), first)
