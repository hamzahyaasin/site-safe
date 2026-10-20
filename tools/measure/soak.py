#!/usr/bin/env python3
"""Full-stack soak test (NFR-05).

Run alongside the whole stack (API, consumers, camera pipeline) for
``--hours``. Throughout it:

* keeps a dashboard socket open and sends one probe event every
  ``--probe-interval`` seconds, recording end-to-end latency and misses;
* samples memory (RSS) and CPU of Site-Safe processes every
  ``--sample-interval`` seconds (matched by command line: daphne,
  run_mqtt_consumer, run_presence_monitor, inference.py, report-service);
* halfway through, closes the socket on purpose and times the reconnect
  (the controlled disconnect).

Writes a CSV time series and a JSON summary with memory growth per process.

    SITESAFE_DEVICE_KEY=<simulator camera token> SITESAFE_EMAIL=... SITESAFE_PASSWORD=... \\
      python tools/measure/soak.py --hours 2
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

PROCESS_PATTERNS = {
    "api": "daphne",
    "mqtt_consumer": "run_mqtt_consumer",
    "presence_monitor": "run_presence_monitor",
    "camera": "inference.py",
    "report_service": "report-service",
}


WRAPPERS = {"env", "sh", "bash", "zsh", "npm", "npm exec", "timeout"}


def find_processes():
    """The real process for each component: launchers such as ``env`` or
    ``npm`` share the command line but are not the process doing the work,
    so they are skipped and the largest matching process is kept."""
    import psutil

    found = {}
    for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        cmd = " ".join(p.info.get("cmdline") or [])
        if "soak.py" in cmd or (p.info.get("name") or "") in WRAPPERS:
            continue
        for label, pattern in PROCESS_PATTERNS.items():
            if pattern in cmd:
                rss = p.info["memory_info"].rss if p.info.get("memory_info") else 0
                if label not in found or rss > found[label][1]:
                    found[label] = (p, rss)
    found = {label: proc for label, (proc, _) in found.items()}
    for p in found.values():
        p.cpu_percent(None)  # prime CPU measurement
    return found


def growth(series):
    if len(series) < 2:
        return None
    return {"first_mb": series[0], "last_mb": series[-1], "max_mb": max(series), "change_mb": series[-1] - series[0]}


async def run(args, csv_path: Path) -> dict:
    import requests
    import websockets

    api = args.api.rstrip("/")
    session = requests.Session()
    session.headers["Authorization"] = f"Device {args.device_key}"
    procs = find_processes()
    memory = {label: [] for label in procs}
    latencies, misses, errors = [], 0, []
    reconnects, forced_reconnect_s = 0, None
    pending: dict[str, float] = {}
    seen: dict[str, float] = {}
    end = time.monotonic() + args.hours * 3600
    disconnect_at = time.monotonic() + args.hours * 1800
    ws_holder = {}

    async def socket_loop():
        nonlocal reconnects
        while time.monotonic() < end:
            try:
                access = common.login(args.api, args.email, args.password)
                async with websockets.connect(common.socket_url(args.api, access), open_timeout=10) as ws:
                    ws_holder["ws"] = ws
                    ws_holder["connected_at"] = time.monotonic()
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("type") == "alert_created":
                            eid = str((msg.get("payload") or {}).get("event_id") or "")
                            if eid in pending:
                                seen[eid] = common.now()
            except Exception as exc:  # noqa: BLE001 - keep soaking
                errors.append(f"socket: {type(exc).__name__}: {exc}"[:200])
            ws_holder.pop("ws", None)
            reconnects += 1
            await asyncio.sleep(1)

    sock = asyncio.create_task(socket_loop())
    await asyncio.sleep(2)
    next_sample = time.monotonic()
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["elapsed_s", "kind", "name", "value"])
        t0 = time.monotonic()
        while time.monotonic() < end:
            # Controlled disconnect, once, halfway through.
            if forced_reconnect_s is None and time.monotonic() >= disconnect_at and "ws" in ws_holder:
                before = ws_holder["connected_at"]
                closed_at = time.monotonic()
                await ws_holder["ws"].close()
                while ws_holder.get("connected_at") == before and time.monotonic() < end:
                    await asyncio.sleep(0.1)
                forced_reconnect_s = ws_holder["connected_at"] - closed_at
                writer.writerow([round(time.monotonic() - t0, 1), "reconnect_s", "forced_disconnect", round(forced_reconnect_s, 2)])

            event = common.camera_event(args.camera_id, "soak probe")
            pending[event["event_id"]] = common.now()
            try:
                r = await asyncio.to_thread(session.post, f"{api}/v1/camera-events/", json=event, timeout=10)
                if r.status_code != 201:
                    errors.append(f"post: HTTP {r.status_code}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"post: {type(exc).__name__}"[:200])
            await asyncio.sleep(min(args.probe_interval, max(0, end - time.monotonic())))

            # Settle probes older than 10 s.
            for eid, sent in list(pending.items()):
                if eid in seen:
                    ms = (seen.pop(eid) - pending.pop(eid)) * 1000
                    latencies.append(ms)
                    writer.writerow([round(time.monotonic() - t0, 1), "latency_ms", "end_to_end", round(ms, 1)])
                elif common.now() - sent > 10:
                    pending.pop(eid)
                    misses += 1
                    writer.writerow([round(time.monotonic() - t0, 1), "miss", "probe", eid])

            if time.monotonic() >= next_sample:
                next_sample += args.sample_interval
                for label, proc in procs.items():
                    try:
                        rss = proc.memory_info().rss / 1024**2
                        cpu = proc.cpu_percent(None)
                    except Exception:  # noqa: BLE001 - process exited
                        errors.append(f"process {label} exited")
                        continue
                    memory[label].append(rss)
                    writer.writerow([round(time.monotonic() - t0, 1), "rss_mb", label, round(rss, 1)])
                    writer.writerow([round(time.monotonic() - t0, 1), "cpu_pct", label, round(cpu, 1)])
                fh.flush()
    sock.cancel()

    return {
        "settings": {
            "hours": args.hours,
            "probe_interval_s": args.probe_interval,
            "sample_interval_s": args.sample_interval,
            "processes_found": sorted(procs),
        },
        "end_to_end_ms": common.summarise(latencies),
        "probes_missed": misses,
        # Every socket end except the forced one is an unexpected drop.
        "unexpected_socket_drops": max(0, reconnects - (1 if forced_reconnect_s is not None else 0)),
        "forced_reconnect_s": forced_reconnect_s,
        "memory": {label: growth(series) for label, series in memory.items()},
        "errors": errors[:100],
        "error_count": len(errors),
        "csv": str(csv_path),
        "target": "2 h with no missed probes, stable memory, reconnect after the forced disconnect (proposed NFR-05)",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default=os.environ.get("SITESAFE_API_BASE", "http://127.0.0.1:8000/api"))
    ap.add_argument("--device-key", default=None)
    ap.add_argument("--email", default=None)
    ap.add_argument("--password", default=None)
    ap.add_argument("--hours", type=float, default=2.0)
    ap.add_argument("--probe-interval", type=float, default=5.0)
    ap.add_argument("--sample-interval", type=float, default=30.0)
    ap.add_argument("--camera-id", default="MEASURE-CAM")
    args = ap.parse_args(argv)
    args.device_key = common.env_or(args.device_key, "SITESAFE_DEVICE_KEY")
    args.email = common.env_or(args.email, "SITESAFE_EMAIL")
    args.password = common.env_or(args.password, "SITESAFE_PASSWORD")
    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = common.RESULTS_DIR / f"soak_{time.strftime('%Y%m%dT%H%M%S')}.csv"
    result = asyncio.run(run(args, csv_path))
    path = common.save_result("soak", result)
    e2e = result["end_to_end_ms"]
    print(f"{e2e.get('n', 0)} probes, {result['probes_missed']} missed, p95 {e2e.get('p95') or 0:.0f} ms, "
          f"forced reconnect {result['forced_reconnect_s'] or 0:.1f}s, {result['error_count']} errors")
    print(f"saved {path} and {csv_path}")
    return 0 if not result["probes_missed"] else 1


if __name__ == "__main__":
    sys.exit(main())
