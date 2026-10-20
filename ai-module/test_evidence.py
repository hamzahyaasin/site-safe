"""Alert evidence (FR-29): model identifier, snapshot encoding, outbox wiring."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

import evidence
import inference


class ModelVersionTests(unittest.TestCase):
    def test_names_file_and_short_sha256(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "weights.pt"
            path.write_bytes(b"model-bytes")
            expected = hashlib.sha256(b"model-bytes").hexdigest()[:12]
            self.assertEqual(evidence.model_version(path), f"weights.pt@{expected}")

    def test_unreadable_weights_are_marked_unknown(self):
        self.assertEqual(evidence.model_version("/nonexistent/x.pt"), "x.pt@unknown")


class SnapshotTests(unittest.TestCase):
    def test_large_frame_is_downscaled_jpeg(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[:, :960] = (0, 0, 255)
        jpeg = evidence.encode_snapshot(frame)
        self.assertTrue(jpeg.startswith(b"\xff\xd8\xff"))
        decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape[:2], (360, 640))

    def test_small_frame_keeps_its_size(self):
        jpeg = evidence.encode_snapshot(np.zeros((120, 160, 3), dtype=np.uint8))
        decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape[:2], (120, 160))

    def test_frame_snapshot_encodes_once_and_respects_privacy_switch(self):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        shot = evidence.FrameSnapshot(frame)
        self.assertIs(shot.get(), shot.get())
        self.assertIsNone(evidence.FrameSnapshot(frame, enabled=False).get())


class QueueEventTests(unittest.TestCase):
    class Outbox:
        def __init__(self):
            self.items = []

        def enqueue(self, payload, snapshot=None):
            self.items.append((payload, snapshot))

    class Rules:
        def __init__(self, enabled=True):
            self._enabled = enabled

        def enabled(self, alert_type):
            return self._enabled

    class CountingSnapshot:
        def __init__(self):
            self.calls = 0

        def get(self):
            self.calls += 1
            return b"jpeg"

    def test_snapshot_and_model_version_go_to_the_outbox(self):
        outbox, shot = self.Outbox(), self.CountingSnapshot()
        payload = inference.with_model(inference.ppe_payload("no-helmet", 0.8, "CAM-01"), "sitesafe_v5.pt@abc")
        self.assertTrue(inference.queue_event(outbox, self.Rules(), payload, shot))
        sent, snapshot = outbox.items[0]
        self.assertEqual(sent["model_version"], "sitesafe_v5.pt@abc")
        self.assertEqual(snapshot, b"jpeg")

    def test_disabled_rule_skips_encoding(self):
        outbox, shot = self.Outbox(), self.CountingSnapshot()
        self.assertFalse(inference.queue_event(outbox, self.Rules(False), {"alert_type": "FALL"}, shot))
        self.assertEqual(shot.calls, 0)
        self.assertEqual(outbox.items, [])

    def test_snapshots_can_be_switched_off_by_environment(self):
        with patch.object(sys, "argv", ["inference.py"]):
            with patch.dict(os.environ, {inference.SNAPSHOTS_ENV: "0"}):
                self.assertTrue(inference.parse_args().no_snapshots)
            with patch.dict(os.environ, {inference.SNAPSHOTS_ENV: "1"}):
                self.assertFalse(inference.parse_args().no_snapshots)


if __name__ == "__main__":
    unittest.main()
