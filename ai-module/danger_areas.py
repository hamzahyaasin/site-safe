"""Danger areas drawn on the camera picture (FR-32).

An area is a polygon in image fractions (0-1 of width and height), drawn on
the Cameras page, such as a crane's swing radius or an excavation edge. A
person is inside when the bottom-centre of their box, where their feet are,
is inside the polygon; the box centre would put someone standing in front
of an area "inside" it.

Each person (identity.IdentityTracker track) raises one alert per entry:
after ``persistence_seconds`` inside and at least ``min_hits`` samples with
no gap longer than ``max_gap_seconds``, so walking past a corner raises
nothing. They can be alerted for that area
again only after ``clear_seconds`` outside it. If the person detector loses
someone and finds them again under a new track id near where an alerted
person was, within a few seconds, the open entry continues instead of
alerting twice.

This module has no camera or model imports, so it is tested without OpenCV
or weights.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

DEFAULT_PERSISTENCE_SECONDS = 1.0
DEFAULT_MIN_HITS = 2
# An unconfirmed entry restarts if the person is out of the area longer than this.
DEFAULT_MAX_GAP_SECONDS = 1.0
DEFAULT_CLEAR_SECONDS = 10.0
# A new track id this close (image fractions) to a lost alerted person, within
# REFOUND_SECONDS of their last sample inside, continues their entry. Later it is
# someone else (identity drops a track after 3 s unseen).
REFOUND_DISTANCE = 0.15
REFOUND_SECONDS = 5.0

Point = tuple[float, float]
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class Area:
    id: int
    name: str
    polygon: tuple[Point, ...]
    severity: str = "HIGH"


def parse_areas(raw: list[dict] | None) -> list[Area]:
    """Areas from the camera-config API; malformed entries are skipped, never guessed."""
    areas = []
    for item in raw or []:
        try:
            polygon = tuple((float(x), float(y)) for x, y in item["polygon"])
            if len(polygon) >= 3:
                areas.append(Area(int(item["id"]), str(item["name"]), polygon, str(item.get("severity") or "HIGH")))
        except (KeyError, TypeError, ValueError):
            continue
    return areas


def foot_point(box: Box, width: int, height: int) -> Point:
    """Bottom-centre of a person box, as fractions of the image size."""
    x1, _, x2, y2 = box
    return ((x1 + x2) / 2 / width, y2 / height)


def contains(polygon: tuple[Point, ...], point: Point) -> bool:
    """Ray casting; a point on an edge may fall either side, which is fine at pixel scale."""
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


@dataclass
class _Entry:
    area_id: int
    person: int
    first_seen: float
    last_seen: float
    point: Point
    hits: int = 1
    alerted: bool = False


@dataclass
class DangerAreaTracker:
    persistence_seconds: float = DEFAULT_PERSISTENCE_SECONDS
    min_hits: int = DEFAULT_MIN_HITS
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS
    clear_seconds: float = DEFAULT_CLEAR_SECONDS
    entries: dict[tuple[int, int], _Entry] = field(default_factory=dict)
    occupied: set[int] = field(default_factory=set)

    def reset(self) -> None:
        self.entries.clear()
        self.occupied.clear()

    def update(self, people: list[tuple[int, Point]], areas: list[Area], now: float) -> list[dict]:
        """Feed one sample of (person id, foot point); return newly confirmed entries.

        ``occupied`` afterwards holds the ids of areas someone is inside now.
        """
        present = {pid for pid, _ in people}
        by_id = {a.id: a for a in areas}
        self.occupied = set()
        events = []
        for area in areas:
            for pid, point in people:
                if not contains(area.polygon, point):
                    continue
                self.occupied.add(area.id)
                key = (area.id, pid)
                entry = self.entries.get(key)
                if entry is None:
                    entry = self._refound(area.id, pid, point, present, now) or _Entry(area.id, pid, now, now, point)
                    self.entries[key] = entry
                    if entry.first_seen == now:
                        continue
                if not entry.alerted and now - entry.last_seen > self.max_gap_seconds:
                    entry.first_seen, entry.hits = now, 0  # stepped out before it was confirmed: start again
                entry.last_seen, entry.point = now, point
                entry.hits += 1
                if not entry.alerted and entry.hits >= self.min_hits and now - entry.first_seen >= self.persistence_seconds:
                    entry.alerted = True
                    events.append(
                        {
                            "area_id": area.id,
                            "area": area.name,
                            "severity": area.severity,
                            "person": pid,
                            "point": point,
                            "seconds_inside": round(now - entry.first_seen, 1),
                        }
                    )
        # Forget entries outside for clear_seconds, and areas that no longer exist.
        self.entries = {
            k: e for k, e in self.entries.items() if e.area_id in by_id and now - e.last_seen < self.clear_seconds
        }
        return events

    def _refound(self, area_id: int, pid: int, point: Point, present: set[int], now: float) -> _Entry | None:
        """An alerted entry of a person who is no longer tracked, close to this new track."""
        for key, entry in list(self.entries.items()):
            if (
                entry.area_id == area_id
                and entry.alerted
                and entry.person not in present
                and now - entry.last_seen <= REFOUND_SECONDS
                and math.dist(entry.point, point) <= REFOUND_DISTANCE
            ):
                del self.entries[key]
                entry.person = pid
                return entry
        return None


def describe(event: dict, camera_id: str) -> str:
    return f"Person entered danger area '{event['area']}' on {camera_id} (inside {event['seconds_inside']:g} s)"


def alert_payload(event: dict, camera_id: str) -> dict:
    return {
        "alert_type": "DANGER_AREA",
        "severity": event["severity"],
        "description": describe(event, camera_id),
        "camera_id": camera_id,
    }
