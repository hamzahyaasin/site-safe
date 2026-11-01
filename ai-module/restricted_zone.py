"""Unidentified people in a restricted zone.

A camera that covers a restricted zone raises a ZONE_BREACH when someone it
cannot identify stays in view: anyone without a readable badge is treated as
not allowed there. Identified workers are judged by the API instead, from
their badge sighting (an identified worker not assigned to the zone raises
its own ZONE_BREACH), so the camera reports only people with no badge.

A badge can take a few seconds to read (turned away, too far), so a person
must stay unidentified for ``grace_seconds`` before the alert. A track that
has shown a badge at any time is never reported: identity.IdentityTracker
lets an identity lapse after its badge has been out of sight for a while,
but the tracked person is still that worker.

Stays follow danger_areas.DangerAreaTracker, with the whole picture as the
area: one alert per person per stay, and again only after they have been out
of view for ``clear_seconds``. Without QR decoding nobody can be identified,
so the caller must not use this at all.

This module has no camera or model imports, so it is tested without OpenCV
or weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import danger_areas

DEFAULT_GRACE_SECONDS = 10.0
SEVERITY = "HIGH"
# Slightly beyond the picture, so feet on its bottom edge (y = 1.0) count as inside.
WHOLE_PICTURE = ((-0.01, -0.01), (1.01, -0.01), (1.01, 1.01), (-0.01, 1.01))
AREA_ID = 0


@dataclass
class RestrictedZoneWatcher:
    grace_seconds: float = DEFAULT_GRACE_SECONDS
    stays: danger_areas.DangerAreaTracker = field(init=False)
    identified: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.stays = danger_areas.DangerAreaTracker(persistence_seconds=self.grace_seconds)

    def reset(self) -> None:
        self.stays.reset()
        self.identified.clear()

    def update(
        self,
        people: list[tuple[int, danger_areas.Point, str | None]],
        tracked: set[int],
        zone: str | None,
        now: float,
    ) -> list[dict]:
        """Feed one sample; return people newly confirmed as unidentified in the zone.

        ``people`` holds (track id, foot point, badge or None) for everyone in
        view, ``tracked`` every track id the identity tracker still follows,
        and ``zone`` the restricted zone's name, or None when the camera's zone
        is not restricted (which forgets every stay).
        """
        if zone is None:
            self.reset()
            return []
        self.identified = {tid for tid in self.identified if tid in tracked}
        self.identified.update(tid for tid, _, badge in people if badge)
        unidentified = [(tid, foot) for tid, foot, _ in people if tid not in self.identified]
        area = danger_areas.Area(AREA_ID, zone, WHOLE_PICTURE, SEVERITY)
        return [
            {"zone": zone, "person": e["person"], "seconds_in_view": e["seconds_inside"]}
            for e in self.stays.update(unidentified, [area], now)
        ]


def describe(event: dict, camera_id: str) -> str:
    return (
        f"Unidentified person in restricted zone {event['zone']} on {camera_id} "
        f"(no readable badge for {event['seconds_in_view']:g} s)"
    )


def alert_payload(event: dict, camera_id: str) -> dict:
    return {
        "alert_type": "ZONE_BREACH",
        "severity": SEVERITY,
        "description": describe(event, camera_id),
        "camera_id": camera_id,
    }
