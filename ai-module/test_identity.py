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
        self.assertEqual(
            [badge for *_, badge in inference.badged_violations(dets, t)],
            [ALI, SARA, None],
        )

    def test_unidentified_boxes_stay_separate(self):
        # Two unidentified people must reach the episode tracker as two boxes.
        dets = [("no-vest", 0.4, (0, 0, 1, 1)), ("no-vest", 0.7, (5, 5, 6, 6))]
        self.assertEqual(
            inference.badged_violations(dets, None),
            [("no-vest", 0.4, (0, 0, 1, 1), None), ("no-vest", 0.7, (5, 5, 6, 6), None)],
        )

    def test_payload_carries_badge(self):
        self.assertEqual(inference.ppe_payload("no-helmet", 0.9, "CAM-01", ALI)["badge_code"], ALI)
        self.assertNotIn("badge_code", inference.ppe_payload("no-helmet", 0.9, "CAM-01"))
        self.assertNotIn("badge_code", inference.with_badge({"a": 1}, None))


if __name__ == "__main__":
    unittest.main()
