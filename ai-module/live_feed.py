"""Live view: send the operator's annotated frame to the dashboard.

The capture loop calls :meth:`LiveFeed.offer` with each display frame; that
only stores a reference. A background thread encodes the newest frame as a
small JPEG and posts it at most ``fps`` times a second. Frames are never
queued: if the network is slow the older frame is simply replaced, so the
live view lags by at most one frame and capture is never blocked.

Unlike alert events, live frames are disposable (see latest_sender): nothing
goes through the outbox, a failed post is not retried, and the server keeps
only the latest frame per camera. This module has no model imports so it can
be tested without weights.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import cv2
import numpy as np

from latest_sender import ERROR_BACKOFF_SECONDS, LatestSender  # noqa: F401 - re-exported for callers

DEFAULT_FPS = 5.0
DEFAULT_WIDTH = 640
DEFAULT_QUALITY = 70

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


class LiveFeed(LatestSender):
    """Annotated frames to the dashboard: encoded as JPEG in the sending thread, at most ``fps`` a second."""

    def __init__(
        self,
        sender: Sender,
        *,
        fps: float = DEFAULT_FPS,
        width: int = DEFAULT_WIDTH,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(
            sender, interval=1.0 / fps, encode=lambda frame: encode_frame(frame, width), clock=clock, name="sitesafe-live"
        )
        self.width = width
