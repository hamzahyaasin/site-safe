#!/usr/bin/env python3
"""Outage recovery of camera events (NFR-02).

Simulates an API outage without touching the running server: the camera's
real outbox (ai-module/event_outbox.py) sends through a local TCP proxy, and
the proxy is switched off for the outage. Procedure:

1. Proxy down. Queue ``--events`` events spread over ``--outage`` seconds
   while the outbox keeps trying (and backing off).
2. Halfway through, stop the outbox and open a new one on the same file,
   simulating a camera process restart.
3. Proxy up. Time until the outbox is empty.
4. Check through the API that every event_id is stored exactly once.

    SITESAFE_DEVICE_KEY=<simulator camera token> SITESAFE_EMAIL=... SITESAFE_PASSWORD=... \\
      python tools/measure/recovery.py --events 100 --outage 300
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "ai-module"))
import common  # noqa: E402
from event_outbox import DEFAULT_MAX_BACKOFF, EventOutbox  # noqa: E402


class SwitchableProxy:
    """TCP forwarder on 127.0.0.1 that can be stopped (connections refused) and started."""

    def __init__(self, target_host: str, target_port: int):
        self.target = (target_host, target_port)
        self.loop = asyncio.new_event_loop()
        self.server = None
        self.port = None
        self.writers: set = set()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    async def _pipe(self, reader, writer):
        try:
            while data := await reader.read(65536):
                writer.write(data)
                await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            writer.close()

    async def _handle(self, client_r, client_w):
        self.writers.add(client_w)
        try:
            up_r, up_w = await asyncio.open_connection(*self.target)
        except OSError:
            client_w.close()
            self.writers.discard(client_w)
            return
        self.writers.add(up_w)
        try:
            await asyncio.gather(self._pipe(client_r, up_w), self._pipe(up_r, client_w))
        finally:
            self.writers.discard(client_w)
            self.writers.discard(up_w)

    def _call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(10)

    def start(self):
        async def go():
            self.server = await asyncio.start_server(self._handle, "127.0.0.1", self.port or 0)
            self.port = self.server.sockets[0].getsockname()[1]

        self._call(go())

    def stop(self):
        """Refuse new connections and cut open ones, as a real outage would.

        Without cutting them, keep-alive connections would keep working and
        wait_closed() would wait on them indefinitely.
        """

        async def go():
            if self.server:
                self.server.close()
                for writer in list(self.writers):
                    writer.transport.abort()
                self.writers.clear()
                await asyncio.wait_for(self.server.wait_closed(), 5)
                self.server = None

        self._call(go())


def make_sender(base_url: str, key: str):
    import requests

    session = requests.Session()
    session.headers["Authorization"] = f"Device {key}"

    def send(payload):
        return session.post(f"{base_url}/v1/camera-events/", json=payload, timeout=5).status_code

    return send


def run(args) -> dict:
    import requests

    target = urlparse(args.api)
    proxy = SwitchableProxy(target.hostname, target.port or 80)
    proxy.start()  # learn a port, then take it down for the outage
    proxy.stop()
    proxied = f"{target.scheme}://127.0.0.1:{proxy.port}{target.path.rstrip('/')}"
    outbox_path = Path(tempfile.mkdtemp(prefix="sitesafe-recovery-")) / "outbox.sqlite3"

    def open_outbox():
        box = EventOutbox(outbox_path, make_sender(proxied, args.device_key), max_backoff=args.max_backoff)
        box.start(interval=0.5)
        return box

    box = open_outbox()
    event_ids, restarted_at = [], None
    t_start = time.monotonic()
    spacing = args.outage / max(args.events, 1)
    for i in range(args.events):
        event = common.camera_event(args.camera_id, f"outage recovery {i + 1}/{args.events}")
        event_ids.append(box.enqueue(event))
        if restarted_at is None and i + 1 >= args.events // 2:
            box.stop(flush_timeout=0)
            box.close()
            box = open_outbox()  # same file: a restarted camera process
            restarted_at = time.monotonic() - t_start
        time.sleep(spacing)
    remaining = args.outage - (time.monotonic() - t_start)
    if remaining > 0:
        time.sleep(remaining)
    queued_during_outage = box.stats()["pending"]

    proxy.start()
    t_restore = time.monotonic()
    while box.stats()["pending"] and time.monotonic() - t_restore < args.timeout:
        time.sleep(0.2)
    recovery_s = time.monotonic() - t_restore
    stats = box.stats()
    box.stop(flush_timeout=0)
    box.close()
    proxy.stop()

    # Verify what the API stored, directly (not through the proxy).
    officer = requests.Session()
    officer.headers["Authorization"] = f"Bearer {common.login(args.api, args.email, args.password)}"
    stored = {}
    for alert in officer.get(f"{args.api.rstrip('/')}/alerts/", timeout=60).json():
        eid = str(alert.get("event_id"))
        if eid in set(event_ids):
            stored[eid] = stored.get(eid, 0) + 1
    if args.resolve:
        for alert in officer.get(f"{args.api.rstrip('/')}/alerts/", params={"is_resolved": "false"}, timeout=60).json():
            if str(alert.get("event_id")) in stored:
                officer.post(f"{args.api.rstrip('/')}/alerts/{alert['id']}/resolve/", timeout=10)

    lost = [e for e in event_ids if e not in stored]
    duplicated = [e for e, n in stored.items() if n > 1]
    return {
        "settings": {
            "events": args.events,
            "outage_s": args.outage,
            "sender_restart_at_s": restarted_at,
            "max_backoff_s": args.max_backoff,
            "recovery_timeout_s": args.timeout,
        },
        "queued_when_restored": queued_during_outage,
        "recovery_s": recovery_s,
        "outbox_after": stats,
        "stored_once": sum(1 for n in stored.values() if n == 1),
        "lost": len(lost),
        "duplicated": len(duplicated),
        "target": "all events stored exactly once within 60 s of restoring the API (proposed NFR-02)",
        "passed": not lost and not duplicated and recovery_s <= 60,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default=os.environ.get("SITESAFE_API_BASE", "http://127.0.0.1:8000/api"))
    ap.add_argument("--device-key", default=None)
    ap.add_argument("--email", default=None)
    ap.add_argument("--password", default=None)
    ap.add_argument("--events", type=int, default=100)
    ap.add_argument("--outage", type=float, default=300.0, help="Outage length in seconds")
    ap.add_argument(
        "--max-backoff",
        type=float,
        default=DEFAULT_MAX_BACKOFF,
        help=f"Outbox retry ceiling (default: the camera's, {DEFAULT_MAX_BACKOFF:g} s)",
    )
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--camera-id", default="MEASURE-CAM")
    ap.add_argument("--resolve", action="store_true")
    args = ap.parse_args(argv)
    args.device_key = common.env_or(args.device_key, "SITESAFE_DEVICE_KEY")
    args.email = common.env_or(args.email, "SITESAFE_EMAIL")
    args.password = common.env_or(args.password, "SITESAFE_PASSWORD")

    result = run(args)
    path = common.save_result("recovery", result)
    print(
        f"{args.events} events over a {args.outage:.0f}s outage: recovered in {result['recovery_s']:.1f}s, "
        f"lost {result['lost']}, duplicated {result['duplicated']}"
    )
    print(f"saved {path}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
