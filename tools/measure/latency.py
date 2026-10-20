#!/usr/bin/env python3
"""Event-to-dashboard latency (NFR-01).

Sends camera events to the API with a simulator camera token while a
dashboard websocket client listens. For each event it records:

* ``api_ms``: POST sent → API response received (validation, rules, storage)
* ``end_to_end_ms``: POST sent → the matching ``alert_created`` arrives on
  the dashboard socket (adds the after-commit broadcast and socket delivery)

Events are matched by ``event_id``; any not seen on the socket within the
timeout are counted as missed, never dropped from the statistics silently.

    SITESAFE_DEVICE_KEY=<simulator camera token> SITESAFE_EMAIL=... SITESAFE_PASSWORD=... \\
      python tools/measure/latency.py --count 100 --interval 0.5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


async def run(args) -> dict:
    import requests
    import websockets

    access = common.login(args.api, args.email, args.password)
    session = requests.Session()
    session.headers["Authorization"] = f"Device {args.device_key}"
    seen: dict[str, float] = {}
    pending: dict[str, float] = {}

    async with websockets.connect(common.socket_url(args.api, access), open_timeout=10) as ws:
        hello = json.loads(await ws.recv())
        if hello.get("type") != "connection_established":
            raise SystemExit(f"Unexpected first socket message: {hello}")

        async def listen():
            async for raw in ws:
                t = common.now()
                msg = json.loads(raw)
                if msg.get("type") == "alert_created":
                    eid = str((msg.get("payload") or {}).get("event_id") or "")
                    if eid in pending and eid not in seen:
                        seen[eid] = t

        listener = asyncio.create_task(listen())
        api_ms, e2e_ms, errors = [], [], []
        sent: list[tuple[str, float]] = []
        for i in range(args.count):
            event = common.camera_event(args.camera_id, f"latency probe {i + 1}/{args.count}")
            t0 = common.now()
            pending[event["event_id"]] = t0
            r = await asyncio.to_thread(session.post, f"{args.api.rstrip('/')}/v1/camera-events/", json=event, timeout=10)
            t1 = common.now()
            if r.status_code != 201:
                errors.append(f"event {i + 1}: HTTP {r.status_code} {r.text[:120]}")
                pending.pop(event["event_id"])
                continue
            api_ms.append((t1 - t0) * 1000)
            sent.append((event["event_id"], t0))
            await asyncio.sleep(args.interval)

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and any(eid not in seen for eid, _ in sent):
            await asyncio.sleep(0.05)
        listener.cancel()

    for eid, t0 in sent:
        if eid in seen:
            e2e_ms.append((seen[eid] - t0) * 1000)
    missed = [eid for eid, _ in sent if eid not in seen]

    if args.resolve and sent:
        officer = requests.Session()
        officer.headers["Authorization"] = f"Bearer {common.login(args.api, args.email, args.password)}"
        ids = {eid for eid, _ in sent}
        for alert in officer.get(f"{args.api.rstrip('/')}/alerts/", params={"is_resolved": "false"}, timeout=30).json():
            if str(alert.get("event_id")) in ids:
                officer.post(f"{args.api.rstrip('/')}/alerts/{alert['id']}/resolve/", timeout=10)

    return {
        "settings": {
            "api": args.api,
            "count": args.count,
            "interval_s": args.interval,
            "camera_id": args.camera_id,
            "socket_timeout_s": args.timeout,
        },
        "api_ms": common.summarise(api_ms),
        "end_to_end_ms": common.summarise(e2e_ms),
        "sent": len(sent),
        "delivered_on_socket": len(sent) - len(missed),
        "missed_on_socket": len(missed),
        "errors": errors,
        "target": "p95 end-to-end <= 2000 ms on the local network (proposed NFR-01)",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default=None, help="API base, default $SITESAFE_API_BASE or http://127.0.0.1:8000/api")
    ap.add_argument("--device-key", default=None, help="Simulator camera token (or $SITESAFE_DEVICE_KEY)")
    ap.add_argument("--email", default=None, help="Dashboard user (or $SITESAFE_EMAIL)")
    ap.add_argument("--password", default=None, help="(or $SITESAFE_PASSWORD)")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--interval", type=float, default=0.5, help="Seconds between events")
    ap.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for stragglers on the socket")
    ap.add_argument("--camera-id", default="MEASURE-CAM")
    ap.add_argument("--resolve", action="store_true", help="Resolve the probe alerts afterwards")
    args = ap.parse_args(argv)
    import os

    args.api = args.api or os.environ.get("SITESAFE_API_BASE", "http://127.0.0.1:8000/api")
    args.device_key = common.env_or(args.device_key, "SITESAFE_DEVICE_KEY")
    args.email = common.env_or(args.email, "SITESAFE_EMAIL")
    args.password = common.env_or(args.password, "SITESAFE_PASSWORD")

    result = asyncio.run(run(args))
    path = common.save_result("latency", result)
    e2e = result["end_to_end_ms"]
    print(f"sent {result['sent']}, delivered {result['delivered_on_socket']}, missed {result['missed_on_socket']}")
    if e2e.get("n"):
        print(f"end-to-end ms: p50 {e2e['p50']:.1f}  p95 {e2e['p95']:.1f}  max {e2e['max']:.1f}")
    print(f"saved {path}")
    return 0 if not result["missed_on_socket"] and not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
