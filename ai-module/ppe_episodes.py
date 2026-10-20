"""Per-person PPE violation episodes for the camera pipeline (FR-05).

The PPE detector reports missing equipment per frame, per box. Alerting on
each frame would flood the dashboard, and a single global cooldown per class
would merge two people missing a helmet into one alert. Instead each
violation box is tracked between frames as one person's *episode*:

* An episode is confirmed only after the violation has been seen for
  ``persistence_seconds`` and in at least ``min_hits`` frames, with gaps no
  longer than ``max_gap_seconds``; a single-frame flicker never alerts.
* A confirmed episode raises exactly one alert, then stays open while the
  violation keeps being seen. It closes once the box has been unseen for
  ``clear_seconds``; the same violation appearing after that is a new
  episode and a new alert.
* Boxes are matched to tracks of the same class by centre distance relative
  to box size. A box carrying a QR badge also matches the open track with
  the same badge, wherever it moved, so an identified worker is never
  alerted twice for one episode.

Like the other trackers this module has no camera or model imports, so it
is tested without OpenCV or weights.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_PERSISTENCE_SECONDS = 1.0
DEFAULT_MIN_HITS = 3
DEFAULT_MAX_GAP_SECONDS = 0.5
DEFAULT_CLEAR_SECONDS = 10.0
# A box matches a track when their centres are at most this many box sizes apart.
DEFAULT_MAX_MATCH_DISTANCE = 1.0

Box = tuple[float, float, float, float]


@dataclass
class _Track:
    track_id: int
    cls: str
    box: Box
    first_seen: float
    last_seen: float
    hits: int = 1
    peak_conf: float = 0.0
    badge: str | None = None
    alerted: bool = False


def _centre(box: Box) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _size(box: Box) -> float:
    return max(box[2] - box[0], box[3] - box[1], 1.0)


def _distance(a: Box, b: Box) -> float:
    """Centre distance in units of the larger box's size."""
    (ax, ay), (bx, by) = _centre(a), _centre(b)
    return math.hypot(ax - bx, ay - by) / max(_size(a), _size(b))


class EpisodeTracker:
    def __init__(
        self,
        persistence_seconds: float = DEFAULT_PERSISTENCE_SECONDS,
        min_hits: int = DEFAULT_MIN_HITS,
        max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
        clear_seconds: float = DEFAULT_CLEAR_SECONDS,
        max_match_distance: float = DEFAULT_MAX_MATCH_DISTANCE,
    ):
        if persistence_seconds < 0:
            raise ValueError("persistence_seconds must be zero or greater")
        if min_hits < 1:
            raise ValueError("min_hits must be at least one")
        if clear_seconds <= 0:
            raise ValueError("clear_seconds must be greater than zero")
        self.persistence_seconds = persistence_seconds
        self.min_hits = min_hits
        self.max_gap_seconds = max_gap_seconds
        self.clear_seconds = clear_seconds
        self.max_match_distance = max_match_distance
        self.tracks: list[_Track] = []
        self._next_id = 1

    def reset(self) -> None:
        self.tracks = []

    def update(
        self,
        detections: list[tuple[str, float, Box, str | None]],
        now: float,
    ) -> list[dict]:
        """Feed one frame's (class, conf, box, badge) violations; return newly confirmed episodes."""
        matched: set[int] = set()
        unmatched = []
        for det in detections:
            track = self._match(det, matched)
            if track is None:
                unmatched.append(det)
            else:
                matched.add(track.track_id)
                self._observe(track, det, now)
        for name, conf, box, badge in unmatched:
            track = _Track(self._next_id, name, box, now, now, peak_conf=conf, badge=badge)
            self._next_id += 1
            self.tracks.append(track)
            matched.add(track.track_id)

        events = []
        for track in self.tracks:
            if track.track_id in matched and not track.alerted and self._confirmed(track):
                track.alerted = True
                events.append(
                    {
                        "track_id": track.track_id,
                        "class": track.cls,
                        "confidence": track.peak_conf,
                        "badge": track.badge,
                        "box": track.box,
                        "seen_seconds": track.last_seen - track.first_seen,
                        "hits": track.hits,
                    }
                )
        self.tracks = [t for t in self.tracks if not self._expired(t, now)]
        return events

    def _match(self, det, taken: set[int]) -> _Track | None:
        name, _, box, badge = det
        candidates = [t for t in self.tracks if t.cls == name and t.track_id not in taken]
        if badge:
            same_badge = [t for t in candidates if t.badge == badge]
            if same_badge:
                return max(same_badge, key=lambda t: t.last_seen)
        # A track that already belongs to another worker cannot take this box.
        candidates = [t for t in candidates if not (badge and t.badge and t.badge != badge)]
        best = min(candidates, key=lambda t: _distance(t.box, box), default=None)
        if best is not None and _distance(best.box, box) <= self.max_match_distance:
            return best
        return None

    def _observe(self, track: _Track, det, now: float) -> None:
        _, conf, box, badge = det
        if not track.alerted and now - track.last_seen > self.max_gap_seconds:
            # The candidate broke off before it was confirmed: start again.
            track.first_seen, track.hits, track.peak_conf = now, 0, 0.0
        track.box = box
        track.last_seen = now
        track.hits += 1
        track.peak_conf = max(track.peak_conf, conf)
        if badge:
            track.badge = badge

    def _confirmed(self, track: _Track) -> bool:
        return track.hits >= self.min_hits and track.last_seen - track.first_seen >= self.persistence_seconds

    def _expired(self, track: _Track, now: float) -> bool:
        gap = now - track.last_seen
        if track.alerted:
            return gap >= self.clear_seconds
        return gap > self.max_gap_seconds
