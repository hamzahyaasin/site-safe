"""Live view: send the operator's annotated frame to the dashboard.

The capture loop calls :meth:`LiveFeed.offer` with each display frame; that
only stores a reference. A background thread encodes the newest frame as a
small JPEG and posts it at most ``fps`` times a second. Frames are never
queued: if the network is slow the older frame is simply replaced, so the
live view lags by at most one frame and capture is never blocked.

Unlike alert events, live frames are disposable. Nothing goes through the
outbox, a failed post is not retried, and the server keeps only the latest
frame per camera. This module has no model imports so it can be tested
without weights.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import cv2
import numpy as np

DEFAULT_FPS = 5.0
DEFAULT_WIDTH = 640
DEFAULT_QUALITY = 70
# After a failed post (API down, token missing) wait this long before the next.
ERROR_BACKOFF_SECONDS = 5.0

# A sender posts one JPEG and returns the HTTP status code; it raises on
# transport failure.
Sender = Callable[[bytes], int]


def encode_frame(frame: np.ndarray, width: int = DEFAULT_WIDTH, quality: int = DEFAULT_QUALITY) -> bytes | None:
    """JPEG of ``frame`` scaled down to ``width`` pixels wide; None if encoding fails."""
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    if w > width:
        frame = cv2.resize(frame, (width, max(1, round(h * width / w))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return buf.tobytes() if ok else None


class LiveFeed:
    def __init__(
        self,
        sender: Sender,
        *,
        fps: float = DEFAULT_FPS,
        width: int = DEFAULT_WIDTH,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.sender = sender
        self.interval = 1.0 / fps
        self.width = width
        self.clock = clock
        self.sent = 0
        self.failed = 0
        self.last_error: str | None = None
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._next_send = 0.0

    def offer(self, frame: np.ndarray) -> None:
        """Make ``frame`` the one to send next. The caller must not draw on it afterwards."""
        with self._lock:
            self._frame = frame
        self._wake.set()

    def send_pending(self) -> bool:
        """Send the newest frame if one is waiting and the rate allows. Returns True if a post was made."""
        now = self.clock()
        if now < self._next_send:
            return False
        with self._lock:
            frame, self._frame = self._frame, None
        if frame is None:
            return False
        jpeg = encode_frame(frame, self.width)
        if jpeg is None:
            return False
        try:
            code = self.sender(jpeg)
            error = None if code in (200, 202, 204) else f"HTTP {code}"
        except Exception as exc:  # noqa: BLE001 - any transport failure just skips this frame
            error = f"{type(exc).__name__}: {exc}"
        if error:
            self.failed += 1
            self.last_error = error
            self._next_send = now + ERROR_BACKOFF_SECONDS
        else:
            self.sent += 1
            self.last_error = None
            self._next_send = now + self.interval
        return True

    def start(self) -> None:
        if self._thread is not None:
            return

        def run() -> None:
            while not self._stop.is_set():
                self._wake.wait(timeout=self.interval)
                self._wake.clear()
                wait = self._next_send - self.clock()
                if wait > 0 and self._stop.wait(wait):
                    break
                self.send_pending()

        self._thread = threading.Thread(target=run, name="sitesafe-live", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
