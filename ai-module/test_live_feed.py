"""Live view sender: rate limit, newest frame wins, error backoff, never blocks."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import inference
import live_feed


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class Recorder:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.sent: list[np.ndarray] = []

    def __call__(self, jpeg):
        self.sent.append(cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR))
        r = self.responses.pop(0) if self.responses else 204
        if isinstance(r, Exception):
            raise r
        return r


def frame(value: int, w: int = 1280, h: int = 720) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


class LiveFeedTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def feed(self, sender, **kw):
        return live_feed.LiveFeed(sender, clock=self.clock, **kw)

    def test_sends_newest_frame_downscaled(self):
        sender = Recorder()
        feed = self.feed(sender)
        feed.offer(frame(10))
        feed.offer(frame(200))
        self.assertTrue(feed.send_pending())
        self.assertEqual(len(sender.sent), 1)
        self.assertEqual(sender.sent[0].shape[:2], (360, 640))
        self.assertGreater(sender.sent[0].mean(), 150, "the newer frame replaced the older one")

    def test_rate_limited_to_fps(self):
        sender = Recorder()
        feed = self.feed(sender, fps=5)
        feed.offer(frame(1))
        feed.send_pending()
        feed.offer(frame(2))
        self.assertFalse(feed.send_pending(), "0.2 s have not passed")
        self.clock.t += 0.2
        self.assertTrue(feed.send_pending())
        self.assertEqual(feed.sent, 2)

    def test_nothing_to_send_without_a_new_frame(self):
        sender = Recorder()
        feed = self.feed(sender)
        feed.offer(frame(1))
        feed.send_pending()
        self.clock.t += 10
        self.assertFalse(feed.send_pending(), "the same frame is never sent twice")

    def test_errors_back_off_and_do_not_raise(self):
        sender = Recorder(ConnectionError("down"), 403)
        feed = self.feed(sender)
        feed.offer(frame(1))
        feed.send_pending()
        self.assertEqual((feed.sent, feed.failed), (0, 1))
        feed.offer(frame(2))
        self.clock.t += live_feed.ERROR_BACKOFF_SECONDS - 0.1
        self.assertFalse(feed.send_pending(), "still backing off")
        self.clock.t += 0.2
        feed.send_pending()
        self.assertEqual(feed.last_error, "HTTP 403")
        feed.offer(frame(3))
        self.clock.t += live_feed.ERROR_BACKOFF_SECONDS
        feed.send_pending()
        self.assertEqual((feed.sent, feed.failed, feed.last_error), (1, 2, None))

    def test_background_thread_sends(self):
        import time

        sender = Recorder()
        feed = live_feed.LiveFeed(sender, fps=50)
        feed.start()
        try:
            feed.offer(frame(7, 64, 48))
            deadline = time.monotonic() + 2
            while not sender.sent and time.monotonic() < deadline:
                time.sleep(0.01)
        finally:
            feed.stop()
        self.assertEqual(len(sender.sent), 1)
        self.assertEqual(sender.sent[0].shape[:2], (48, 64), "small frames are not upscaled")


class LiveOptionTests(unittest.TestCase):
    def test_live_view_switch(self):
        with patch.object(sys, "argv", ["inference.py"]):
            with patch.dict(os.environ, {inference.LIVE_ENV: "0"}):
                self.assertTrue(inference.parse_args().no_live)
            with patch.dict(os.environ, {inference.LIVE_ENV: "1"}):
                self.assertFalse(inference.parse_args().no_live)

    def test_sender_posts_jpeg_for_this_camera(self):
        calls = []

        class Session:
            def post(self, url, params, data, headers, timeout):
                calls.append((url, params, data, headers))

                class R:
                    status_code = 204

                return R()

        code = inference.make_live_sender(Session(), "CAM-01")(b"\xff\xd8jpeg")
        self.assertEqual(code, 204)
        url, params, data, headers = calls[0]
        self.assertTrue(url.endswith("/v1/camera-frames/"))
        self.assertEqual(params, {"camera_id": "CAM-01"})
        self.assertEqual(headers["Content-Type"], "image/jpeg")


if __name__ == "__main__":
    unittest.main()
