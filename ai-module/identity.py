"""QR badge identification for camera events.

Workers wear a printed QR badge encoding ``SSW1:<code>``. Each sampled frame
the camera decodes visible badges and attaches each one to the person box
that contains it. Person boxes are followed across samples by overlap, so
an identity persists while the badge is briefly turned away. An event is
attributed to a worker only when that is unambiguous:

* A badge inside two overlapping person boxes is not assigned.
* A point covered by two identified people is not identified.
* An identity expires when its person is lost, or after ``identity_ttl``
  seconds without seeing the badge again.

Anything else stays unidentified; the API never guesses a worker.
"""

from __future__ import annotations

from dataclasses import dataclass

Box = tuple[float, float, float, float]
Point = tuple[float, float]

BADGE_PREFIX = "SSW1:"
DEFAULT_IDENTITY_TTL = 30.0
DEFAULT_TRACK_TTL = 3.0
MATCH_IOU = 0.3
# Badges are often worn on helmets at the very top of the person box.
TOP_MARGIN = 0.15


def parse_badge(text: str | None) -> str | None:
    """Return the full payload if ``text`` is a Site-Safe badge, else None."""
    if not text or not text.startswith(BADGE_PREFIX) or len(text) <= len(BADGE_PREFIX):
        return None
    return text.strip()


def box_center(box: Box) -> Point:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def contains(box: Box, point: Point, top_margin: float = 0.0) -> bool:
    x1, y1, x2, y2 = box
    y1 -= (y2 - y1) * top_margin
    return x1 <= point[0] <= x2 and y1 <= point[1] <= y2


def iou(a: Box, b: Box) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])  # noqa: E731
    return inter / (area(a) + area(b) - inter)


class QrDecoder:
    """Thin wrapper over OpenCV's built-in QR detector (no extra dependency)."""

    def __init__(self):
        import cv2

        self._detector = cv2.QRCodeDetector()

    def decode(self, frame) -> list[tuple[str, Point]]:
        """Return (badge_payload, centre) for each Site-Safe badge in the frame."""
        try:
            ok, texts, points, _ = self._detector.detectAndDecodeMulti(frame)
        except Exception:  # noqa: BLE001 - a decoder failure must not stop inference
            return []
        if not ok or points is None:
            return []
        hits = []
        for text, quad in zip(texts, points):
            badge = parse_badge(text)
            if badge:
                xs = [float(p[0]) for p in quad]
                ys = [float(p[1]) for p in quad]
                hits.append((badge, (sum(xs) / len(xs), sum(ys) / len(ys))))
        return hits


@dataclass
class _Track:
    box: Box
    last_seen: float
    badge: str | None = None
    badge_seen: float = 0.0


class IdentityTracker:
    def __init__(
        self,
        identity_ttl: float = DEFAULT_IDENTITY_TTL,
        track_ttl: float = DEFAULT_TRACK_TTL,
    ):
        self.identity_ttl = identity_ttl
        self.track_ttl = track_ttl
        self.tracks: list[_Track] = []

    def reset(self) -> None:
        self.tracks = []

    def update(self, person_boxes: list[Box], badges: list[tuple[str, Point]], now: float) -> None:
        # 1. Follow existing people by best overlap (greedy, one-to-one).
        unmatched = list(range(len(person_boxes)))
        pairs = sorted(
            (
                (iou(t.box, person_boxes[j]), i, j)
                for i, t in enumerate(self.tracks)
                for j in unmatched
            ),
            reverse=True,
        )
        used_tracks: set[int] = set()
        for score, i, j in pairs:
            if score < MATCH_IOU or i in used_tracks or j not in unmatched:
                continue
            self.tracks[i].box = person_boxes[j]
            self.tracks[i].last_seen = now
            used_tracks.add(i)
            unmatched.remove(j)
        for j in unmatched:
            self.tracks.append(_Track(box=person_boxes[j], last_seen=now))

        # 2. Drop lost people and stale identities.
        self.tracks = [t for t in self.tracks if now - t.last_seen <= self.track_ttl]
        for t in self.tracks:
            if t.badge and now - t.badge_seen > self.identity_ttl:
                t.badge = None

        # 3. Attach each badge to the single current person containing it.
        current = [t for t in self.tracks if t.last_seen == now]
        for badge, centre in badges:
            holders = [t for t in current if contains(t.box, centre, TOP_MARGIN)]
            if len(holders) != 1:
                continue  # ambiguous or outside every person: leave unassigned
            for t in self.tracks:
                if t.badge == badge and t is not holders[0]:
                    t.badge = None  # a badge identifies one person only
            holders[0].badge = badge
            holders[0].badge_seen = now

    def identify(self, point: Point) -> str | None:
        """Badge of the one identified current person containing ``point``."""
        matches = {t.badge for t in self.tracks if t.badge and contains(t.box, point)}
        holders = [t for t in self.tracks if contains(t.box, point)]
        if len(matches) == 1 and len(holders) == 1:
            return matches.pop()
        return None

    def identify_box(self, box: Box) -> str | None:
        return self.identify(box_center(box))
