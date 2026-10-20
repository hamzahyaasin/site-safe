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

            def enqueue(self, payload):
                self.items.append(payload)

        rules = inference.CameraRules(session=None, camera_id="CAM-01")
        rules.rules = {"FALL": {"is_enabled": False}, "INACTIVITY": {"threshold_seconds": 90}}
        box = Box()
        self.assertFalse(inference.queue_event(box, rules, {"alert_type": "FALL"}))
        self.assertTrue(inference.queue_event(box, rules, inference.ppe_payload("no-helmet", 0.8, "CAM-01")))
        self.assertEqual(len(box.items), 1)
        self.assertEqual(rules.threshold("INACTIVITY"), 90.0)

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
