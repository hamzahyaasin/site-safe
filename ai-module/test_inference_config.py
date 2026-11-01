from __future__ import annotations

from contextlib import redirect_stderr
import io
import sys
import unittest
from unittest.mock import patch

import numpy as np

import inference


class InferenceConfigurationTests(unittest.TestCase):
    def test_display_annotations_do_not_mutate_raw_frame(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        raw_frame, display_frame = inference.frame_views(frame)
        inference.plot_detections(
            display_frame,
            {0: "no-helmet"},
            np.array([[10.0, 10.0, 40.0, 40.0]]),
            np.array([0.9]),
            np.array([0]),
        )
        self.assertIs(raw_frame, frame)
        self.assertFalse(np.any(raw_frame))
        self.assertTrue(np.any(display_frame))

    def test_ppe_conf_is_configurable(self):
        with patch.object(sys, "argv", ["inference.py", "--ppe-conf", "0.42"]):
            args = inference.parse_args()
        self.assertEqual(args.ppe_conf, 0.42)

    def test_loop_and_no_display_flags(self):
        with patch.object(sys, "argv", ["inference.py", "--loop", "--no-display"]):
            args = inference.parse_args()
        self.assertTrue(args.loop and args.no_display)
        with patch.object(sys, "argv", ["inference.py"]):
            args = inference.parse_args()
        self.assertFalse(args.loop or args.no_display)

    def test_only_files_on_disk_can_loop(self):
        self.assertTrue(inference.is_file_source(__file__))
        self.assertFalse(inference.is_file_source(0))
        self.assertFalse(inference.is_file_source("rtsp://192.168.1.20/stream"))
        self.assertFalse(inference.is_file_source("/no/such/clip.mp4"))

    def test_event_label_reads_ppe_class_from_payload(self):
        payload = inference.ppe_payload("no-helmet", 0.5, "CAM-01")
        self.assertEqual(inference.event_label(payload), "no-helmet")
        self.assertEqual(inference.event_label({"alert_type": "FALL"}), "FALL")
        self.assertEqual(inference.event_label({"kind": "SIGHTING"}), "SIGHTING")

    def test_recording_outbox_writes_time_and_forwards(self):
        import json
        import tempfile

        class Inner:
            def __init__(self):
                self.queued = []

            def enqueue(self, payload, snapshot=None):
                self.queued.append(payload)

            def stats(self):
                return {"pending": len(self.queued)}

            def close(self):
                pass

        inner = Inner()
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/events.jsonl"
            rec = inference.RecordingOutbox(inner, path, lambda: 12.3456)
            rec.enqueue(inference.ppe_payload("no-vest", 0.7, "CAM-01", "SSW1:ali"))
            self.assertEqual(rec.stats(), {"pending": 1})
            rec.close()
            (line,) = open(path).read().splitlines()
        record = json.loads(line)
        self.assertEqual((record["t"], record["event"], record["badge"]), (12.346, "no-vest", "SSW1:ali"))

    def test_video_clock_needs_a_file_and_no_loop(self):
        for argv in (["--video-clock", "--source", "0"], ["--video-clock", "--loop", "--source", __file__]):
            with patch.object(sys, "argv", ["inference.py", *argv]):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        inference.parse_args()
        with patch.object(sys, "argv", ["inference.py", "--video-clock", "--source", __file__]):
            self.assertTrue(inference.parse_args().video_clock)

    def test_ppe_conf_rejects_out_of_range_value(self):
        with patch.object(sys, "argv", ["inference.py", "--ppe-conf", "1.1"]):
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    inference.parse_args()


class CameraRulesTests(unittest.TestCase):
    def test_no_credentials_in_source(self):
        from pathlib import Path

        source = Path(inference.__file__).read_text()
        self.assertNotIn("ADMIN_PASSWORD", source)
        self.assertNotIn("@gmail.com", source)

    def test_rules_default_to_enabled_until_loaded(self):
        rules = inference.CameraRules(session=None, camera_id="CAM-01")
        self.assertTrue(rules.enabled("FALL"))
        self.assertIsNone(rules.threshold("INACTIVITY"))

    def test_disabled_rule_skips_queue(self):
        class Box:
            def __init__(self):
                self.items = []

            def enqueue(self, payload, snapshot=None):
                self.items.append(payload)

        rules = inference.CameraRules(session=None, camera_id="CAM-01")
        rules.rules = {"FALL": {"is_enabled": False}, "INACTIVITY": {"threshold_seconds": 90}}
        box = Box()
        self.assertFalse(inference.queue_event(box, rules, {"alert_type": "FALL"}))
        self.assertTrue(inference.queue_event(box, rules, inference.ppe_payload("no-helmet", 0.8, "CAM-01")))
        self.assertEqual(len(box.items), 1)
        self.assertEqual(rules.threshold("INACTIVITY"), 90.0)

    def test_refresh_reads_whether_the_zone_is_restricted(self):
        class Session:
            def __init__(self, body):
                self.body = body

            def get(self, *args, **kwargs):
                body = self.body
                return type("R", (), {"status_code": 200, "json": lambda self: body})()

        rules = inference.CameraRules(session=Session({"zone": "Crane", "zone_restricted": True}), camera_id="CAM-09")
        self.assertFalse(rules.zone_restricted, "nothing is restricted until the config is loaded")
        self.assertTrue(rules.refresh())
        self.assertEqual((rules.zone, rules.zone_restricted), ("Crane", True))
        rules.session = Session({"zone": "Crane"})
        rules.refresh()
        self.assertFalse(rules.zone_restricted, "an older API without the field means not restricted")

    def test_device_key_header(self):
        session = inference.build_api_session("ss_test")
        self.assertEqual(session.headers["Authorization"], "Device ss_test")
        self.assertNotIn("Authorization", inference.build_api_session("").headers)


class DeviceTests(unittest.TestCase):
    def test_explicit_device_kept(self):
        self.assertEqual(inference.pick_device("cpu"), "cpu")

    def test_auto_prefers_accelerator(self):
        import torch

        with patch.object(torch.cuda, "is_available", return_value=False), \
             patch.object(torch.backends.mps, "is_available", return_value=True):
            self.assertEqual(inference.pick_device("auto"), "mps")
        with patch.object(torch.cuda, "is_available", return_value=False), \
             patch.object(torch.backends.mps, "is_available", return_value=False):
            self.assertEqual(inference.pick_device("auto"), "cpu")


if __name__ == "__main__":
    unittest.main()
