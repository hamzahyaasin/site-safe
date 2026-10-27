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
* The detector sometimes reports one body part twice, as two same-class
  boxes overlapping less than its own NMS removes (IoU 0.50-0.63 in a live
  run), sometimes three for one head. Same-class boxes in one frame are
  merged first when they overlap by ``duplicate_iou`` or more, or when one
  box's centre lies inside the other and they overlap by at least
  ``nested_iou``; boxes with different badges are never merged. Otherwise one
  person becomes two episodes and the weaker box, flickering around the
  candidate threshold, keeps reopening new ones.
* Each violation can carry the id of the tracked person whose box contains
  it (identity.IdentityTracker). Boxes are matched to tracks of the same
  class by, in order: the same QR badge, the same person, then centre
  distance relative to box size. A small head box can jump more than its own
  size as someone leans towards a webcam (live run, 27 Oct: one person,
  three no-helmet alerts in five seconds); while it stays inside the same
  person it stays the same episode. Same-class boxes on one person in one
  frame (both hands without gloves) are one violation, and an episode of
  another person who is still in view is never taken by distance. Without a
  person detector, distance alone decides.

Like the other trackers this module has no camera or model imports, so it
is tested without OpenCV or weights.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

DEFAULT_PERSISTENCE_SECONDS = 1.0
DEFAULT_MIN_HITS = 3
DEFAULT_MAX_GAP_SECONDS = 0.5
# A violation must stay unseen this long before the person can be alerted
# again. With 10 s, a 55 s live webcam run alerted one person up to four
# times for the same item as weak detections dropped out and returned.
DEFAULT_CLEAR_SECONDS = 30.0
# Same-class boxes in one frame overlapping at least this much are one person.
DEFAULT_DUPLICATE_IOU = 0.4
# ...as are boxes where one centre lies inside the other, from this overlap up.
# A second live run had one head as a short and a tall box at IoU 0.26.
DEFAULT_NESTED_IOU = 0.2
# A box matches a track when their centres are at most this many box sizes apart.
DEFAULT_MAX_MATCH_DISTANCE = 1.0

Box = tuple[float, float, float, float]


class Violation(NamedTuple):
    """One missing-PPE box in one frame."""

    cls: str
    conf: float
    box: Box
    badge: str | None = None
    person: int | None = None


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
    person: int | None = None
    alerted: bool = False


def _centre(box: Box) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _size(box: Box) -> float:
    return max(box[2] - box[0], box[3] - box[1], 1.0)


def _iou(a: Box, b: Box) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / (_area(a) + _area(b) - inter)


def _area(box: Box) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def _contains_centre(outer: Box, inner: Box) -> bool:
    x, y = _centre(inner)
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def _same_part(a: Box, b: Box, duplicate_iou: float, nested_iou: float) -> bool:
    overlap = _iou(a, b)
    if overlap >= duplicate_iou:
        return True
    return overlap >= nested_iou and (_contains_centre(a, b) or _contains_centre(b, a))


def _same_violation(a: Violation, b: Violation, duplicate_iou: float, nested_iou: float) -> bool:
    if a.cls != b.cls:
        return False
    if a.badge and b.badge and a.badge != b.badge:
        return False
    if a.person is not None and b.person is not None:
        # One person has one episode per class; two people never merge.
        return a.person == b.person
    return _same_part(a.box, b.box, duplicate_iou, nested_iou)


def merge_duplicates(
    detections: list[Violation | tuple],
    duplicate_iou: float = DEFAULT_DUPLICATE_IOU,
    nested_iou: float = DEFAULT_NESTED_IOU,
) -> list[Violation]:
    """Collapse same-class boxes that belong to one person's one violation.

    The most confident box of a group is kept; it takes a badge or person
    from a merged box if it has none.
    """
    kept: list[Violation] = []
    for det in sorted((Violation(*d) for d in detections), key=lambda d: d.conf, reverse=True):
        for i, k in enumerate(kept):
            if _same_violation(k, det, duplicate_iou, nested_iou):
                kept[i] = k._replace(badge=k.badge or det.badge, person=k.person if k.person is not None else det.person)
                break
        else:
            kept.append(det)
    return kept


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
        duplicate_iou: float = DEFAULT_DUPLICATE_IOU,
        nested_iou: float = DEFAULT_NESTED_IOU,
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
        self.duplicate_iou = duplicate_iou
        self.nested_iou = nested_iou
        self.tracks: list[_Track] = []
        self._next_id = 1

    def reset(self) -> None:
        self.tracks = []

    def update(
        self,
        detections: list[Violation | tuple],
        now: float,
        people: set[int] | None = None,
    ) -> list[dict]:
        """Feed one frame's violations; return newly confirmed episodes.

        Each detection is a Violation or a tuple (class, conf, box[, badge[,
        person]]). ``people`` holds the ids of everyone currently tracked;
        by default, the people this frame's violations belong to.
        """
        dets = merge_duplicates(detections, self.duplicate_iou, self.nested_iou)
        present = set(people) if people is not None else {d.person for d in dets if d.person is not None}
        matched: set[int] = set()
        # Identity first (badge, then person) so an identified box is never
        # claimed by a nearer box of someone else; then distance.
        pending = []
        for det in dets:
            track = self._match_identity(det, matched)
            if track is None:
                pending.append(det)
            else:
                matched.add(track.track_id)
                self._observe(track, det, now)
        for det in pending:
            track = self._match_distance(det, matched, present)
            if track is None:
                track = _Track(self._next_id, det.cls, det.box, now, now, peak_conf=det.conf, badge=det.badge, person=det.person)
                self._next_id += 1
                self.tracks.append(track)
            else:
                self._observe(track, det, now)
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

    def _match_identity(self, det: Violation, taken: set[int]) -> _Track | None:
        candidates = [t for t in self.tracks if t.cls == det.cls and t.track_id not in taken]
        for key in ("badge", "person"):
            value = getattr(det, key)
            if value is None:
                continue
            same = [t for t in candidates if getattr(t, key) == value]
            if same:
                return max(same, key=lambda t: t.last_seen)
        return None

    def _match_distance(self, det: Violation, taken: set[int], present: set[int]) -> _Track | None:
        def belongs_to_someone_else(t: _Track) -> bool:
            if det.badge and t.badge and t.badge != det.badge:
                return True
            # A person who is still in view keeps their own episode.
            return det.person is not None and t.person is not None and t.person != det.person and t.person in present

        candidates = [
            t for t in self.tracks if t.cls == det.cls and t.track_id not in taken and not belongs_to_someone_else(t)
        ]
        best = min(candidates, key=lambda t: _distance(t.box, det.box), default=None)
        if best is not None and _distance(best.box, det.box) <= self.max_match_distance:
            return best
        return None

    def _observe(self, track: _Track, det: Violation, now: float) -> None:
        if not track.alerted and now - track.last_seen > self.max_gap_seconds:
            # The candidate broke off before it was confirmed: start again.
            track.first_seen, track.hits, track.peak_conf = now, 0, 0.0
        track.box = det.box
        track.last_seen = now
        track.hits += 1
        track.peak_conf = max(track.peak_conf, det.conf)
        if det.badge:
            track.badge = det.badge
        if det.person is not None:
            track.person = det.person

    def _confirmed(self, track: _Track) -> bool:
        return track.hits >= self.min_hits and track.last_seen - track.first_seen >= self.persistence_seconds

    def _expired(self, track: _Track, now: float) -> bool:
        gap = now - track.last_seen
        if track.alerted:
            return gap >= self.clear_seconds
        return gap > self.max_gap_seconds
