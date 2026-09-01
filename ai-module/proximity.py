"""Person/vehicle proximity geometry for the Site-Safe vision pipeline.

Deliberately free of OpenCV, torch, and ultralytics imports: this module holds
the decision logic for vehicle proximity warnings, so it can be unit-tested
without loading a model or opening a camera.

A single camera gives no depth information, so "proximity" here is a
heuristic measured in the image plane rather than a true metric distance.
The gap between a person box and a vehicle box is normalised by the person's
pixel height, which acts as a rough proxy for how far that person is from the
camera: a worker standing near the lens is tall in pixels, one far away is
short. A threshold expressed in person-heights therefore means roughly the
same real-world distance at both ends of the frame, provided the person and
the vehicle are at comparable depth. Where that assumption breaks — a worker
standing well in front of a distant vehicle, so the two boxes overlap in the
image while being far apart in reality — the measure over-reports. This is
the principal limitation of single-camera proximity estimation.
"""

from __future__ import annotations

import math

# COCO class ids from the pretrained detector that stand in for site vehicles.
# COCO has no forklift class; forklifts and similar plant typically register as
# "truck" or "car", which is why those two carry most of the weight here.
PERSON_CLASS_ID = 0
VEHICLE_CLASS_IDS = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

DEFAULT_THRESHOLD = 1.0  # in person-heights
DEFAULT_PERSISTENCE = 3  # consecutive evaluated frames before confirming


def bbox_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Shortest edge-to-edge distance in pixels between two [x1,y1,x2,y2] boxes.

    Returns 0.0 when the boxes overlap or touch.
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(0.0, max(ax1, bx1) - min(ax2, bx2))
    dy = max(0.0, max(ay1, by1) - min(ay2, by2))
    return math.hypot(dx, dy)


def box_height(box: tuple[float, float, float, float]) -> float:
    return max(0.0, box[3] - box[1])


def normalised_gap(person: tuple, vehicle: tuple) -> float | None:
    """Gap between person and vehicle expressed in person-heights.

    Returns None for a degenerate person box (zero height), which cannot be
    used as a scale reference.
    """
    height = box_height(person)
    if height <= 0:
        return None
    return bbox_gap(person, vehicle) / height


def closest_proximity(persons: list, vehicles: list, threshold: float) -> dict | None:
    """Closest person/vehicle pair breaching the threshold, or None.

    `persons` is a list of boxes; `vehicles` is a list of (box, label) pairs.
    """
    best: dict | None = None
    for person in persons:
        for vehicle_box, label in vehicles:
            gap = normalised_gap(person, vehicle_box)
            if gap is None or gap > threshold:
                continue
            if best is None or gap < best["normalised_gap"]:
                best = {
                    "normalised_gap": gap,
                    "pixel_gap": bbox_gap(person, vehicle_box),
                    "vehicle_label": label,
                    "person_box": person,
                    "vehicle_box": vehicle_box,
                    "overlapping": bbox_gap(person, vehicle_box) == 0.0,
                }
    return best


def severity_for(event: dict) -> str:
    """Overlapping boxes mean the worker reads as inside the vehicle's
    footprint, which is treated as more urgent than merely being near it."""
    return "CRITICAL" if event["overlapping"] else "HIGH"


def describe(event: dict) -> str:
    distance = "overlapping" if event["overlapping"] else f"{event['normalised_gap']:.2f} person-heights"
    return f"Worker within proximity of {event['vehicle_label']} ({distance})"


class ProximityTracker:
    """Confirms a proximity condition only after it persists across frames.

    A single frame of detection noise — a spurious box, a momentary
    mis-classification — should not raise an alert, so a breach must hold for
    `persistence` consecutive evaluated frames before it is confirmed. Once
    confirmed, the tracker will not fire again until the condition clears,
    which prevents one worker standing beside a parked vehicle from
    generating a continuous stream of alerts.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        persistence: int = DEFAULT_PERSISTENCE,
    ) -> None:
        self.threshold = threshold
        self.persistence = max(1, persistence)
        self._streak = 0
        self._armed = True

    def update(self, persons: list, vehicles: list) -> dict | None:
        """Feed one evaluated frame. Returns a confirmed event, or None."""
        event = closest_proximity(persons, vehicles, self.threshold)
        if event is None:
            self._streak = 0
            self._armed = True
            return None

        self._streak += 1
        if self._streak >= self.persistence and self._armed:
            self._armed = False
            return event
        return None


def split_detections(boxes, class_ids) -> tuple[list, list]:
    """Partition raw detector output into person boxes and (vehicle box, label) pairs."""
    persons: list = []
    vehicles: list = []
    for box, cid in zip(boxes, class_ids):
        cid = int(cid)
        if cid == PERSON_CLASS_ID:
            persons.append(tuple(box))
        elif cid in VEHICLE_CLASS_IDS:
            vehicles.append((tuple(box), VEHICLE_CLASS_IDS[cid]))
    return persons, vehicles
