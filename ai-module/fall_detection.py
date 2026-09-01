"""Camera-side fall detection for the Site-Safe vision pipeline.

Dependency-free (no OpenCV, torch, or Ultralytics import), the same
convention as proximity.py and inactivity.py, so the geometry and
persistence logic can be tested without loading a model or opening a
camera. It consumes 17-keypoint COCO-format pose output (the shape
Ultralytics' YOLO11-pose models emit: keypoints.xy is [N, 17, 2],
keypoints.conf is [N, 17]) rather than any specific model API.

Detection follows the two-signal design from the project's Chapter 3
proposal: a person is in a collapsed posture when their confidently
detected keypoints form a bounding box wider than it is tall (a standing
person's keypoint box is taller than wide; a person lying down is the
reverse), AND their hip keypoints sit at or below their knee keypoints
(a standing torso holds hips well above the knees). Both signals are
required, matching the original design's "both conditions must be met
simultaneously" — using either alone is far too easy to trigger with an
ordinary crouch or a bend to pick something up.

A collapsed reading on one sampled frame is not a fall: a person is
tracked between frames by a confidence-weighted keypoint centroid, and a
fall is confirmed only once that track has read as collapsed for a
configured persistence duration (three seconds by design) of continuous,
non-interrupted observation. This mirrors the persistence and re-arm
behaviour already implemented in inactivity.py: a confirmed fall latches
until the tracked posture clears, so a person who remains on the ground
does not generate a repeating stream of alerts.

Camera-local tracks, not worker identities: association can be lost or
swapped when people cross, occlude one another, or move farther than
max_match_distance between sampled frames, exactly as documented in
inactivity.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

Point = tuple[float, float]
Keypoints = Sequence[Point]
Confidences = Sequence[float]

# COCO 17-keypoint order, as emitted by Ultralytics YOLO11-pose models.
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16
NUM_KEYPOINTS = 17

HIP_INDEXES = (LEFT_HIP, RIGHT_HIP)
KNEE_INDEXES = (LEFT_KNEE, RIGHT_KNEE)

DEFAULT_MIN_KEYPOINT_CONF = 0.5
DEFAULT_MIN_KEYPOINTS_FOR_BBOX = 4
DEFAULT_SPAN_RATIO_THRESHOLD = 1.2
DEFAULT_PERSISTENCE_SECONDS = 3.0
DEFAULT_MAX_MISSING_UPDATES = 2
DEFAULT_MINIMUM_OBSERVATIONS = 2
DEFAULT_MAX_MATCH_DISTANCE = 150.0


def _validate_pose(xy: Keypoints, conf: Confidences) -> None:
    if len(xy) != NUM_KEYPOINTS or len(conf) != NUM_KEYPOINTS:
        raise ValueError(f"pose must have exactly {NUM_KEYPOINTS} keypoints and confidences")


def confident_points(
    xy: Keypoints, conf: Confidences, indexes: Sequence[int], min_conf: float
) -> list[Point]:
    return [xy[i] for i in indexes if conf[i] >= min_conf]


def weighted_centroid(xy: Keypoints, conf: Confidences) -> Point | None:
    """Confidence-weighted mean of all keypoints, for cross-frame tracking.

    Returns None when every keypoint confidence is zero (nothing detected),
    which should not happen for a real detection but is handled rather than
    dividing by zero.
    """
    _validate_pose(xy, conf)
    total = sum(conf)
    if total <= 0:
        return None
    x = sum(px * c for (px, _py), c in zip(xy, conf)) / total
    y = sum(py * c for (_px, py), c in zip(xy, conf)) / total
    return (x, y)


def span_ratio(
    xy: Keypoints,
    conf: Confidences,
    *,
    min_conf: float = DEFAULT_MIN_KEYPOINT_CONF,
    min_keypoints: int = DEFAULT_MIN_KEYPOINTS_FOR_BBOX,
) -> float | None:
    """Horizontal / vertical extent of the confidently detected keypoints.

    A ratio greater than 1 means the keypoint bounding box is wider than
    tall. Returns None when too few keypoints are confidently detected to
    trust the bounding box (occlusion, a partial view, a poor angle) rather
    than guessing from an unreliable box.
    """
    _validate_pose(xy, conf)
    points = confident_points(xy, conf, range(NUM_KEYPOINTS), min_conf)
    if len(points) < min_keypoints:
        return None
    xs = [px for px, _py in points]
    ys = [py for _px, py in points]
    horizontal = max(xs) - min(xs)
    vertical = max(ys) - min(ys)
    if vertical <= 0:
        return None
    return horizontal / vertical


def hips_at_or_below_knees(
    xy: Keypoints,
    conf: Confidences,
    *,
    min_conf: float = DEFAULT_MIN_KEYPOINT_CONF,
) -> bool | None:
    """Whether the average hip Y is at or below the average knee Y.

    Image Y increases downward, so "below" means a numerically larger Y.
    Returns None when neither hip nor a knee keypoint (of either side) is
    confidently detected, rather than assuming a posture that can't be
    observed.
    """
    _validate_pose(xy, conf)
    hips = confident_points(xy, conf, HIP_INDEXES, min_conf)
    knees = confident_points(xy, conf, KNEE_INDEXES, min_conf)
    if not hips or not knees:
        return None
    hip_y = sum(y for _x, y in hips) / len(hips)
    knee_y = sum(y for _x, y in knees) / len(knees)
    return hip_y >= knee_y


def is_collapsed_posture(
    xy: Keypoints,
    conf: Confidences,
    *,
    span_ratio_threshold: float = DEFAULT_SPAN_RATIO_THRESHOLD,
    min_conf: float = DEFAULT_MIN_KEYPOINT_CONF,
    min_keypoints_for_bbox: int = DEFAULT_MIN_KEYPOINTS_FOR_BBOX,
) -> bool:
    """True only when both the span-ratio and hip/knee signals affirmatively
    agree the person is down. Either signal being unmeasurable (too few
    confident keypoints) returns False rather than assuming the worst —
    consistent with proximity.py and inactivity.py's handling of degenerate
    input, and deliberately biased against false positives from missing
    data rather than toward catching every possible fall.
    """
    ratio = span_ratio(xy, conf, min_conf=min_conf, min_keypoints=min_keypoints_for_bbox)
    if ratio is None or ratio <= span_ratio_threshold:
        return False
    collapsed = hips_at_or_below_knees(xy, conf, min_conf=min_conf)
    return bool(collapsed)


def describe(event: dict) -> str:
    """Human-readable API description for a confirmed fall event."""
    return (
        f"Possible fall: collapsed posture sustained for "
        f"{event['collapsed_seconds']:.1f}s in camera view "
        f"(temporary track {event['track_id']})"
    )


def alert_payload(event: dict, camera_id: str) -> dict:
    """Return the existing alert API shape for a camera-level fall event."""
    return {
        "alert_type": "FALL",
        "severity": "CRITICAL",
        "source": "AI_CAMERA",
        "description": describe(event),
        "camera_id": camera_id,
    }


def _centroid_distance(a: Point, b: Point) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


@dataclass
class _Track:
    track_id: int
    centroid: Point
    collapsed_since: float | None = None
    observations_while_collapsed: int = 0
    missing_updates: int = 0
    armed: bool = True


class FallTracker:
    """Tracks multiple detected people and emits one event per confirmed,
    sustained fall.

    ``update`` should be called only on sampled frames the pose model
    actually ran on. It accepts an explicit monotonic timestamp so
    irregularly sampled frames still use elapsed seconds rather than
    assuming a fixed frame rate, the same contract as InactivityTracker.
    """

    def __init__(
        self,
        persistence_seconds: float = DEFAULT_PERSISTENCE_SECONDS,
        *,
        span_ratio_threshold: float = DEFAULT_SPAN_RATIO_THRESHOLD,
        min_keypoint_conf: float = DEFAULT_MIN_KEYPOINT_CONF,
        min_keypoints_for_bbox: int = DEFAULT_MIN_KEYPOINTS_FOR_BBOX,
        max_missing_updates: int = DEFAULT_MAX_MISSING_UPDATES,
        minimum_observations: int = DEFAULT_MINIMUM_OBSERVATIONS,
        max_match_distance: float = DEFAULT_MAX_MATCH_DISTANCE,
    ) -> None:
        if persistence_seconds <= 0:
            raise ValueError("persistence_seconds must be greater than zero")
        if span_ratio_threshold <= 0:
            raise ValueError("span_ratio_threshold must be greater than zero")
        if max_missing_updates < 0:
            raise ValueError("max_missing_updates must be zero or greater")
        if minimum_observations < 1:
            raise ValueError("minimum_observations must be at least one")
        if max_match_distance <= 0:
            raise ValueError("max_match_distance must be greater than zero")

        self.persistence_seconds = float(persistence_seconds)
        self.span_ratio_threshold = float(span_ratio_threshold)
        self.min_keypoint_conf = float(min_keypoint_conf)
        self.min_keypoints_for_bbox = int(min_keypoints_for_bbox)
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

    def _new_track(self, centre: Point, collapsed: bool, now: float) -> int:
        # A newly created track's first observation must count immediately —
        # otherwise a person already collapsed in the very frame their track
        # is created (a fall that happened just before the camera picked
        # them up, or simply the first sampled frame) loses that frame from
        # the persistence clock, delaying confirmation by one full sample.
        track_id = self._next_track_id
        self._next_track_id += 1
        self._tracks[track_id] = _Track(
            track_id=track_id,
            centroid=centre,
            collapsed_since=now if collapsed else None,
            observations_while_collapsed=1 if collapsed else 0,
        )
        return track_id

    def _associations(self, centres: list[Point]) -> dict[int, int]:
        """Greedily pair each track/detection once, nearest distance first."""
        candidates: list[tuple[float, int, int]] = []
        for track_id, track in self._tracks.items():
            for detection_index, centre in enumerate(centres):
                distance = _centroid_distance(track.centroid, centre)
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
        people: Sequence[tuple[Keypoints, Confidences]],
        *,
        now: float,
    ) -> list[dict]:
        """Feed one sampled detector frame's poses; return newly confirmed events.

        ``people`` is a sequence of (keypoints_xy, keypoints_conf) pairs, one
        per detected person. Each element of keypoints_xy is an (x, y) pair;
        keypoints_conf is the matching per-keypoint confidence — the shape
        Ultralytics pose output converts to directly.
        """
        if self._last_update_time is not None and now < self._last_update_time:
            raise ValueError("now must not move backwards")
        self._last_update_time = now

        centres: list[Point | None] = []
        collapsed_flags: list[bool] = []
        for xy, conf in people:
            _validate_pose(xy, conf)
            centres.append(weighted_centroid(xy, conf))
            collapsed_flags.append(
                is_collapsed_posture(
                    xy,
                    conf,
                    span_ratio_threshold=self.span_ratio_threshold,
                    min_conf=self.min_keypoint_conf,
                    min_keypoints_for_bbox=self.min_keypoints_for_bbox,
                )
            )

        # A pose with no usable keypoints at all can't be centred or tracked;
        # drop it from this frame rather than raise, since a detector can
        # legitimately emit a near-empty pose for a heavily occluded person.
        usable = [(c, collapsed_flags[i]) for i, c in enumerate(centres) if c is not None]
        valid_centres = [c for c, _ in usable]
        valid_collapsed = [flag for _, flag in usable]

        matches = self._associations(valid_centres)
        matched_detection_indexes = set(matches.values())
        events: list[dict] = []

        for track_id, track in list(self._tracks.items()):
            detection_index = matches.get(track_id)
            if detection_index is None:
                track.missing_updates += 1
                if track.missing_updates > self.max_missing_updates:
                    del self._tracks[track_id]
                continue

            track.missing_updates = 0
            track.centroid = valid_centres[detection_index]
            collapsed = valid_collapsed[detection_index]

            if not collapsed:
                track.collapsed_since = None
                track.observations_while_collapsed = 0
                track.armed = True
                continue

            if track.collapsed_since is None:
                track.collapsed_since = now
                track.observations_while_collapsed = 1
            else:
                track.observations_while_collapsed += 1

            collapsed_seconds = now - track.collapsed_since
            if (
                track.armed
                and track.observations_while_collapsed >= self.minimum_observations
                and collapsed_seconds >= self.persistence_seconds
            ):
                track.armed = False
                events.append(
                    {
                        "event_type": "FALL",
                        "track_id": track.track_id,
                        "centroid": track.centroid,
                        "collapsed_seconds": collapsed_seconds,
                        "collapsed_since": track.collapsed_since,
                        "detected_at": now,
                    }
                )

        for detection_index, centre in enumerate(valid_centres):
            if detection_index not in matched_detection_indexes:
                self._new_track(centre, valid_collapsed[detection_index], now)

        return events
