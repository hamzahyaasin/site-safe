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
from dataclasses import dataclass, field

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
DEFAULT_PERSISTENCE = 3  # evaluated frames (samples) near a vehicle before confirming
# An unconfirmed encounter restarts if the person is not near a vehicle for longer than this.
DEFAULT_MAX_GAP_SECONDS = 1.0
# An encounter ends once the person has not been near any vehicle for this long;
# only then can they be alerted again. A small or partly hidden vehicle drops out
# of detection for seconds at a time (up to 4 s in the 27 Oct test clip).
DEFAULT_CLEAR_SECONDS = 15.0
# A new track this soon after an alerted person was last near a vehicle, within one
# of their person-heights, is that person re-found (identity drops a track after 3 s
# unseen). Later, or farther, it is someone else.
REFOUND_SECONDS = 5.0

Box = tuple[float, float, float, float]


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


@dataclass
class _Encounter:
    person: int
    first_seen: float
    last_seen: float
    box: Box
    closest: dict
    hits: int = 0
    alerted: bool = False


def _centre(box: Box) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


@dataclass
class ProximityTracker:
    """One alert per person per encounter with a vehicle.

    People are followed between frames by identity.IdentityTracker; this
    tracker is fed each sample's (track id, person box) pairs. A person near
    a vehicle (within ``threshold`` person-heights) starts an encounter,
    which is confirmed after ``persistence`` samples near one with no gap
    longer than ``max_gap_seconds``, so a single spurious box never alerts.
    A confirmed encounter raises exactly one alert, reported at its closest
    point so far, and stays open while the person keeps coming near
    vehicles. It ends once they have not been near any vehicle for
    ``clear_seconds``; only then can the same person be alerted again.

    Vehicle detections flicker, so the earlier design (re-arm on the first
    sample without a breach, one camera-wide cooldown) alerted one worker
    beside one parked car every cooldown period, and merged two workers at
    risk into one alert. If the person detector loses someone and finds them
    again close by under a new track id, an alerted encounter continues
    instead of alerting twice; someone appearing there later than
    ``REFOUND_SECONDS`` is treated as a different person.
    """

    threshold: float = DEFAULT_THRESHOLD
    persistence: int = DEFAULT_PERSISTENCE
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS
    clear_seconds: float = DEFAULT_CLEAR_SECONDS
    encounters: dict[int, _Encounter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.persistence = max(1, self.persistence)

    def reset(self) -> None:
        self.encounters.clear()

    def update(self, people: list[tuple[int, Box]], vehicles: list, now: float) -> list[dict]:
        """Feed one sample; return newly confirmed encounters.

        Each event is ``closest_proximity``'s dict plus ``person`` (track id).
        """
        present = {pid for pid, _ in people}
        events = []
        for pid, box in people:
            near = closest_proximity([box], vehicles, self.threshold)
            if near is None:
                continue
            enc = self.encounters.get(pid) or self._refound(pid, box, present, now)
            if enc is None or (not enc.alerted and now - enc.last_seen > self.max_gap_seconds):
                enc = _Encounter(pid, first_seen=now, last_seen=now, box=box, closest=near)
            self.encounters[pid] = enc
            enc.last_seen, enc.box = now, box
            enc.hits += 1
            if near["normalised_gap"] < enc.closest["normalised_gap"]:
                enc.closest = near
            if not enc.alerted and enc.hits >= self.persistence:
                enc.alerted = True
                events.append({**enc.closest, "person": pid})
        self.encounters = {p: e for p, e in self.encounters.items() if now - e.last_seen < self.clear_seconds}
        return events

    def _refound(self, pid: int, box: Box, present: set[int], now: float) -> _Encounter | None:
        """A recent alerted encounter of someone no longer tracked, within one person-height of ``box``."""
        for key, enc in list(self.encounters.items()):
            if (
                enc.alerted
                and enc.person not in present
                and now - enc.last_seen <= REFOUND_SECONDS
                and math.dist(_centre(enc.box), _centre(box)) <= box_height(enc.box)
            ):
                del self.encounters[key]
                enc.person = pid
                return enc
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
