"""Camera-side inactivity tracking for the Site-Safe vision pipeline.

This module deliberately has no OpenCV, torch, or Ultralytics dependency so
the decision logic can be tested without loading a model or opening a camera.

The tracker associates person bounding boxes between sampled detector frames
using their centroids.  A temporary track becomes inactive only when its
centroid remains within ``movement_threshold`` pixels of the start of its
current stationary period for at least ``timeout_seconds``.  An alert is
emitted once for that period; movement beyond the threshold re-arms the track.

These are camera-local, short-lived tracks, not worker identities.  Association
can be lost or swapped when people cross, are occluded, or move farther than
``max_match_distance`` between samples.  Likewise, pixel displacement is not a
real-world distance and should be calibrated for each camera view.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Iterable, Sequence


DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_MOVEMENT_THRESHOLD = 15.0
DEFAULT_MAX_MISSING_UPDATES = 2
DEFAULT_MINIMUM_OBSERVATIONS = 3
DEFAULT_MAX_MATCH_DISTANCE = 100.0

Box = tuple[float, float, float, float]
Point = tuple[float, float]


def _normalise_box(box: Sequence[float]) -> Box:
    if len(box) != 4:
        raise ValueError("person boxes must contain [x1, y1, x2, y2]")
    x1, y1, x2, y2 = (float(value) for value in box)
    if x2 < x1 or y2 < y1:
        raise ValueError("person boxes must have x2 >= x1 and y2 >= y1")
    return x1, y1, x2, y2


def centroid(box: Sequence[float]) -> Point:
    """Return the centre point of an ``[x1, y1, x2, y2]`` box."""
    x1, y1, x2, y2 = _normalise_box(box)
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def centroid_distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def describe(event: dict) -> str:
    """Human-readable API description for a confirmed inactivity event."""
    return (
        f"Person stationary for {event['stationary_seconds']:.1f}s in camera view "
        f"(temporary track {event['track_id']})"
    )


def alert_payload(event: dict, camera_id: str) -> dict:
    """Return the existing alert API shape for a camera-level event."""
    return {
        "alert_type": "INACTIVITY",
        "severity": "MEDIUM",
        "source": "AI_CAMERA",
        "description": describe(event),
        "camera_id": camera_id,
    }


@dataclass
class _Track:
    track_id: int
    person_box: Box
    centroid: Point
    anchor_centroid: Point
    stationary_since: float
    observations: int = 1
    missing_updates: int = 0
    armed: bool = True


class InactivityTracker:
    """Track multiple detected people and emit one event per stationary period.

    ``update`` should be called only when the person detector is evaluated.  It
    accepts an explicit monotonic timestamp so irregularly sampled frames still
    use elapsed seconds rather than assuming a fixed frame rate.

    A small number of missed detector updates is tolerated.  No event is fired
    while a track is missing, and a track that exceeds ``max_missing_updates``
    is discarded.  ``minimum_observations`` prevents a pair of isolated boxes
    separated by a long time gap from being treated as persistent inactivity.
    """

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        movement_threshold: float = DEFAULT_MOVEMENT_THRESHOLD,
        *,
        max_missing_updates: int = DEFAULT_MAX_MISSING_UPDATES,
        minimum_observations: int = DEFAULT_MINIMUM_OBSERVATIONS,
        max_match_distance: float | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if movement_threshold < 0:
            raise ValueError("movement_threshold must be zero or greater")
        if max_missing_updates < 0:
            raise ValueError("max_missing_updates must be zero or greater")
        if minimum_observations < 1:
            raise ValueError("minimum_observations must be at least one")
        if max_match_distance is None:
            # Association must span more than the configured stationary-noise
            # radius, otherwise raising the movement threshold could cause a
            # still-acceptable displacement to create a brand-new track.
            max_match_distance = max(
                DEFAULT_MAX_MATCH_DISTANCE,
                float(movement_threshold) * 4.0,
            )
        if max_match_distance <= 0:
            raise ValueError("max_match_distance must be greater than zero")

        self.timeout_seconds = float(timeout_seconds)
        self.movement_threshold = float(movement_threshold)
        self.max_missing_updates = int(max_missing_updates)
        self.minimum_observations = int(minimum_observations)
        self.max_match_distance = float(max_match_distance)
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1
        self._last_update_time: float | None = None

    @property
    def active_track_count(self) -> int:
        return len(self._tracks)

    def reset(self) -> None:
        """Forget all camera-local tracks, for example after a paused stream."""
        self._tracks.clear()
        self._last_update_time = None

    def _new_track(self, box: Box, centre: Point, now: float) -> None:
        track_id = self._next_track_id
        self._next_track_id += 1
        self._tracks[track_id] = _Track(
            track_id=track_id,
            person_box=box,
            centroid=centre,
            anchor_centroid=centre,
            stationary_since=now,
        )

    def _associations(self, centres: list[Point]) -> dict[int, int]:
        """Greedily pair each track/detection once, nearest distance first."""
        candidates: list[tuple[float, int, int]] = []
        for track_id, track in self._tracks.items():
            for detection_index, centre in enumerate(centres):
                distance = centroid_distance(track.centroid, centre)
                if distance <= self.max_match_distance:
                    candidates.append((distance, track_id, detection_index))
        candidates.sort()

        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()
        matches: dict[int, int] = {}
        for _, track_id, detection_index in candidates:
            if track_id in matched_tracks or detection_index in matched_detections:
                continue
            matched_tracks.add(track_id)
            matched_detections.add(detection_index)
            matches[track_id] = detection_index
        return matches

    def update(
        self,
        person_boxes: Iterable[Sequence[float]],
        *,
        now: float | None = None,
    ) -> list[dict]:
        """Feed one sampled detector frame and return newly confirmed events.

        The result can contain more than one event because separate people can
        cross the timeout in the same sampled frame.  Each track emits only
        once until it moves beyond ``movement_threshold``.
        """
        timestamp = time.monotonic() if now is None else float(now)
        if self._last_update_time is not None and timestamp < self._last_update_time:
            raise ValueError("now must not move backwards")
        self._last_update_time = timestamp

        boxes = [_normalise_box(box) for box in person_boxes]
        centres = [centroid(box) for box in boxes]
        matches = self._associations(centres)
        matched_detection_indexes = set(matches.values())
        events: list[dict] = []

        for track_id, track in list(self._tracks.items()):
            detection_index = matches.get(track_id)
            if detection_index is None:
                track.missing_updates += 1
                if track.missing_updates > self.max_missing_updates:
                    del self._tracks[track_id]
                continue

            box = boxes[detection_index]
            centre = centres[detection_index]
            track.missing_updates = 0

            displacement = centroid_distance(track.anchor_centroid, centre)
            if displacement > self.movement_threshold:
                # A new stationary period starts at the latest observed point.
                track.anchor_centroid = centre
                track.stationary_since = timestamp
                track.observations = 1
                track.armed = True
            else:
                track.observations += 1

            track.person_box = box
            track.centroid = centre
            stationary_seconds = timestamp - track.stationary_since
            if (
                track.armed
                and track.observations >= self.minimum_observations
                and stationary_seconds >= self.timeout_seconds
            ):
                track.armed = False
                events.append(
                    {
                        "event_type": "INACTIVITY",
                        "track_id": track.track_id,
                        "person_box": track.person_box,
                        "centroid": track.centroid,
                        "stationary_seconds": stationary_seconds,
                        "stationary_since": track.stationary_since,
                        "detected_at": timestamp,
                    }
                )

        for detection_index, (box, centre) in enumerate(zip(boxes, centres)):
            if detection_index not in matched_detection_indexes:
                self._new_track(box, centre, timestamp)

        return events
