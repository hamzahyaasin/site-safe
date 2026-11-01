#!/usr/bin/env python3
"""Smart vest simulator for demonstrations and integration tests.

Sends vest telemetry (GPS, battery, SOS, gas) to the Site-Safe vest gateway API
exactly as a physical vest gateway would, so zone history, restricted-zone
and capacity breaches, SOS alerts, offline detection and the live map can be
shown without hardware.

Use a token created with ``--simulator``; the backend then marks every
resulting alert SIMULATED, so it is labelled in the dashboard and excluded
from report figures:

    python manage.py create_service_token vest-sim --kind VEST_GATEWAY --simulator
    SITESAFE_DEVICE_KEY=ss_... python tools/vest_simulator.py tools/vest_scenarios/demo.json

A scenario lists vests (which must already be registered) with waypoints.
Each vest walks its waypoints at the given speed and can press SOS when it
reaches a waypoint index (``sos_at``) or go silent after one (``stop_at``)
to show offline detection. A vest with ``gas_ppm`` reports that gas level
throughout, and ``gas_leak_at`` raises it to ``gas_leak_ppm`` for
``gas_leak_seconds`` from that waypoint on, to show the GAS alert.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field

EARTH_RADIUS_M = 6_371_000.0


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two (lat, lng) points in metres."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


@dataclass
class Vest:
    vest_id: str
    waypoints: list[tuple[float, float]]
    speed_mps: float = 1.2
    battery_start: int = 90
    battery_drain_per_min: float = 0.5
    sos_at: int | None = None
    stop_at: int | None = None
    gas_ppm: int | None = None
    gas_leak_at: int | None = None
    gas_leak_ppm: int = 3000
    gas_leak_seconds: float = 30.0

    @classmethod
    def from_dict(cls, d: dict) -> "Vest":
        points = [tuple(map(float, p)) for p in d["waypoints"]]
        if not points:
            raise ValueError(f"vest {d.get('vest_id')!r} has no waypoints")
        for lat, lng in points:
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError(f"vest {d['vest_id']!r} has an invalid waypoint ({lat}, {lng})")
        return cls(
            vest_id=str(d["vest_id"]),
            waypoints=points,
            speed_mps=float(d.get("speed_mps", 1.2)),
            battery_start=int(d.get("battery_start", 90)),
            battery_drain_per_min=float(d.get("battery_drain_per_min", 0.5)),
            sos_at=d.get("sos_at"),
            stop_at=d.get("stop_at"),
            gas_ppm=d.get("gas_ppm"),
            gas_leak_at=d.get("gas_leak_at"),
            gas_leak_ppm=int(d.get("gas_leak_ppm", 3000)),
            gas_leak_seconds=float(d.get("gas_leak_seconds", 30)),
        )


@dataclass
class Frame:
    t: float  # seconds from scenario start
    vest_id: str
    payload: dict = field(default_factory=dict)


def position_at(vest: Vest, t: float) -> tuple[tuple[float, float], int]:
    """(lat, lng) after walking for ``t`` seconds, and the last waypoint index reached."""
    travelled = vest.speed_mps * t
    for i in range(len(vest.waypoints) - 1):
        a, b = vest.waypoints[i], vest.waypoints[i + 1]
        leg = distance_m(a, b)
        if travelled <= leg or i == len(vest.waypoints) - 2:
            f = 1.0 if leg == 0 else min(travelled / leg, 1.0)
            pos = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            return pos, i + 1 if f >= 1.0 else i
        travelled -= leg
    return vest.waypoints[-1], len(vest.waypoints) - 1


def route_seconds(vest: Vest) -> float:
    total = sum(distance_m(a, b) for a, b in zip(vest.waypoints, vest.waypoints[1:]))
    return total / vest.speed_mps if vest.speed_mps > 0 else 0.0


def build_frames(vests: list[Vest], interval: float, hold: float = 0.0) -> list[Frame]:
    """Every telemetry message the scenario will send, in time order.

    A vest reports every ``interval`` seconds until it finishes its route
    (plus ``hold`` seconds standing still) or reaches ``stop_at``.
    """
    frames: list[Frame] = []
    for vest in vests:
        end = route_seconds(vest) + hold
        t = 0.0
        sos_sent = False
        leak_from = None
        while t <= end + 1e-9:
            (lat, lng), reached = position_at(vest, t)
            if vest.stop_at is not None and reached >= vest.stop_at:
                payload = {"latitude": round(lat, 7), "longitude": round(lng, 7)}
                frames.append(Frame(t, vest.vest_id, {**payload, **_battery(vest, t)}))
                break  # goes silent: the backend should mark it offline
            payload = {"latitude": round(lat, 7), "longitude": round(lng, 7), **_battery(vest, t)}
            if vest.gas_leak_at is not None and reached >= vest.gas_leak_at and leak_from is None:
                leak_from = t
            if leak_from is not None and t - leak_from < vest.gas_leak_seconds:
                payload["gas_ppm"] = vest.gas_leak_ppm
            elif vest.gas_ppm is not None:
                payload["gas_ppm"] = vest.gas_ppm
            if vest.sos_at is not None and reached >= vest.sos_at and not sos_sent:
                payload["sos_active"] = True
                sos_sent = True
            frames.append(Frame(t, vest.vest_id, payload))
            t += interval
    frames.sort(key=lambda f: (f.t, f.vest_id))
    return frames


def _battery(vest: Vest, t: float) -> dict:
    level = vest.battery_start - vest.battery_drain_per_min * t / 60.0
    return {"battery_level": max(0, min(100, int(round(level))))}


def load_scenario(path: str) -> tuple[list[Vest], float, float]:
    with open(path) as fh:
        data = json.load(fh)
    vests = [Vest.from_dict(v) for v in data["vests"]]
    return vests, float(data.get("interval_seconds", 5)), float(data.get("hold_seconds", 0))


def send(api: str, key: str, frame: Frame) -> int:
    import requests

    r = requests.post(
        api.rstrip("/") + "/v1/vests/telemetry/",
        json={"vest_id": frame.vest_id, **frame.payload},
        headers={"Authorization": f"Device {key}"},
        timeout=5,
    )
    return r.status_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", help="Scenario JSON file")
    parser.add_argument("--api", default=os.environ.get("SITESAFE_API_BASE", "http://127.0.0.1:8000/api"))
    parser.add_argument("--speedup", type=float, default=1.0, help="Run the scenario this many times faster")
    parser.add_argument("--dry-run", action="store_true", help="Print messages instead of sending them")
    args = parser.parse_args(argv)

    vests, interval, hold = load_scenario(args.scenario)
    frames = build_frames(vests, interval, hold)
    key = os.environ.get("SITESAFE_DEVICE_KEY", "")
    if not args.dry_run and not key:
        print("Set SITESAFE_DEVICE_KEY to a vest gateway simulator token.", file=sys.stderr)
        return 2

    print(f"{len(frames)} messages from {len(vests)} vest(s), about {frames[-1].t / args.speedup:.0f}s")
    start = time.monotonic()
    failures = 0
    for frame in frames:
        wait = frame.t / args.speedup - (time.monotonic() - start)
        if wait > 0 and not args.dry_run:
            time.sleep(wait)
        if args.dry_run:
            print(f"t={frame.t:6.1f}s {frame.vest_id} {json.dumps(frame.payload)}")
            continue
        try:
            code = send(args.api, key, frame)
        except Exception as exc:  # noqa: BLE001 - report and keep the scenario running
            code, failures = str(exc), failures + 1
        else:
            failures += code != 200
        tag = " SOS" if frame.payload.get("sos_active") else ""
        print(f"t={frame.t:6.1f}s {frame.vest_id}{tag} -> {code}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
