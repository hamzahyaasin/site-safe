"""Alert evidence (FR-29): a JPEG of the frame that confirmed an event, and
an identifier for the weights that produced it.

Each AI alert carries ``model_version`` (``<weights file>@<first 12 hex of
its SHA-256>``) so an incident can be traced to the exact model, even after
weights are retrained under the same file name, and optionally a snapshot:
the raw, unannotated frame downscaled so its longer side is at most
``DEFAULT_MAX_SIDE`` pixels and JPEG-encoded. The whole frame is kept rather
than a crop because proximity and fire alerts need the surrounding scene to
be checked by a person.

This module has no model imports so it can be unit-tested without weights.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

# 640 px keeps a worker's helmet and vest legible at typical CCTV distances
# while a frame stays around 30-80 KB, well under the API's 512 KB limit.
DEFAULT_MAX_SIDE = 640
DEFAULT_JPEG_QUALITY = 80
HASH_PREFIX_CHARS = 12


@lru_cache(maxsize=None)
def model_version(path: str | Path) -> str:
    """``sitesafe_v5.pt@1a2b3c4d5e6f``; ``unknown`` part if the file is unreadable."""
    p = Path(path)
    digest = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return f"{p.name}@unknown"
    return f"{p.name}@{digest.hexdigest()[:HASH_PREFIX_CHARS]}"


def encode_snapshot(
    frame: np.ndarray,
    max_side: int = DEFAULT_MAX_SIDE,
    quality: int = DEFAULT_JPEG_QUALITY,
) -> bytes | None:
    """JPEG bytes of ``frame`` scaled down to ``max_side``; None if encoding fails."""
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        frame = cv2.resize(frame, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return buf.tobytes() if ok else None


class FrameSnapshot:
    """Encode the current frame at most once, and only if an event needs it.

    Most frames confirm no event, so encoding is deferred until the first
    ``get()``; several events confirmed on the same frame share one JPEG.
    With ``enabled`` False (the privacy switch) ``get()`` always returns None.
    """

    def __init__(self, frame: np.ndarray, enabled: bool = True):
        self._frame = frame
        self._enabled = enabled
        self._jpeg: bytes | None = None
        self._done = False

    def get(self) -> bytes | None:
        if not self._enabled:
            return None
        if not self._done:
            self._jpeg = encode_snapshot(self._frame)
            self._done = True
        return self._jpeg
