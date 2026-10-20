"""Fire and smoke confirmation for the camera pipeline.

A detector flags fire or smoke per frame; flames flicker and reflections
cause single-frame false positives, so an event is confirmed only when the
class keeps appearing for ``persistence_seconds`` with at most short gaps.
After an alert the class is latched: it re-arms only once the scene has been
clear for ``clear_seconds``, so a burning area raises one alert, not one per
frame, and a new fire after it is out raises a new one.

Severity is decided by the server from hot-work permits; the camera reports
what it saw and how confident it was.
"""

from __future__ import annotations

from dataclasses import dataclass

CLASSES = ("fire", "smoke")
DEFAULT_CONF = 0.45
DEFAULT_PERSISTENCE_SECONDS = 2.0
DEFAULT_MAX_GAP_SECONDS = 1.0
DEFAULT_CLEAR_SECONDS = 30.0
DEFAULT_MIN_BOX_FRACTION = 0.0005  # ignore specks smaller than 0.05% of the frame


def normalise_class(name: str) -> str | None:
    n = name.strip().lower()
    if "fire" in n or "flame" in n:
        return "fire"
    if "smoke" in n:
        return "smoke"
    return None


@dataclass
class _State:
    first_seen: float | None = None
    last_seen: float | None = None
    peak_conf: float = 0.0
    largest_box: tuple[float, float, float, float] | None = None
    latched: bool = False


class FireTracker:
    def __init__(
        self,
        persistence_seconds: float = DEFAULT_PERSISTENCE_SECONDS,
        max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
        clear_seconds: float = DEFAULT_CLEAR_SECONDS,
        min_box_fraction: float = DEFAULT_MIN_BOX_FRACTION,
    ):
        if persistence_seconds <= 0:
            raise ValueError("persistence_seconds must be greater than zero")
        self.persistence_seconds = persistence_seconds
        self.max_gap_seconds = max_gap_seconds
        self.clear_seconds = clear_seconds
        self.min_box_fraction = min_box_fraction
        self.states = {c: _State() for c in CLASSES}

    def reset(self) -> None:
        self.states = {c: _State() for c in CLASSES}

    def update(
        self,
        detections: list[tuple[str, float, tuple[float, float, float, float]]],
        frame_area: float,
        now: float,
    ) -> list[dict]:
        """Feed one sampled frame's (class, conf, box) detections; return confirmed events."""
        seen: dict[str, tuple[float, tuple]] = {}
        for name, conf, box in detections:
            cls = normalise_class(name)
            if cls is None:
                continue
            area = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
            if frame_area > 0 and area / frame_area < self.min_box_fraction:
                continue
            if cls not in seen or conf > seen[cls][0]:
                seen[cls] = (conf, box)

        events = []
        for cls, state in self.states.items():
            if cls in seen:
                conf, box = seen[cls]
                if state.last_seen is None or now - state.last_seen > self.max_gap_seconds:
                    if not state.latched:
                        state.first_seen, state.peak_conf, state.largest_box = now, 0.0, None
                state.last_seen = now
                if conf > state.peak_conf:
                    state.peak_conf = conf
                if state.largest_box is None or _area(box) > _area(state.largest_box):
                    state.largest_box = box
                if not state.latched and now - state.first_seen >= self.persistence_seconds:
                    state.latched = True
                    events.append(
                        {
                            "class": cls,
                            "confidence": state.peak_conf,
                            "seen_seconds": now - state.first_seen,
                            "box": state.largest_box,
                            "box_fraction": _area(state.largest_box) / frame_area if frame_area else 0.0,
                        }
                    )
            elif state.last_seen is not None:
                gap = now - state.last_seen
                if state.latched and gap >= self.clear_seconds:
                    self.states[cls] = _State()  # scene clear: re-arm
                elif not state.latched and gap > self.max_gap_seconds:
                    self.states[cls] = _State()  # candidate broke off before confirming
        return events


def _area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def describe(event: dict) -> str:
    what = "Fire" if event["class"] == "fire" else "Smoke"
    return (
        f"{what} detected for {event['seen_seconds']:.1f}s in camera view "
        f"(peak conf {event['confidence']:.2f}, {event['box_fraction'] * 100:.1f}% of frame)"
    )


def alert_payload(event: dict, camera_id: str) -> dict:
    return {
        "alert_type": "FIRE" if event["class"] == "fire" else "SMOKE",
        # Provisional: the server sets the final severity from hot-work permits.
        "severity": "CRITICAL" if event["class"] == "fire" else "HIGH",
        "description": describe(event),
        "camera_id": camera_id,
        "confidence": round(float(event["confidence"]), 4),
    }
