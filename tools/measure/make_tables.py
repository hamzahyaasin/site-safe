#!/usr/bin/env python3
"""Turn measurement results into Chapter 5 tables (Markdown).

Uses the most recent result of each kind in ``--results`` (latency,
recovery, fps_<device>, soak) and writes ``--out``. Every table states its
sample size, environment, settings and the proposed target, with PASS or
FAIL, so a number never appears without its context. Kinds with no result
are listed as not yet measured.

    python tools/measure/make_tables.py --out docs/evidence/CHAPTER5_MEASUREMENTS.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def latest(results: Path) -> dict[str, dict]:
    by_kind: dict[str, dict] = {}
    for path in sorted(results.glob("*.json")):
        data = json.loads(path.read_text())
        kind = path.stem.rsplit("_", 1)[0]
        data["_file"] = path.name
        if kind not in by_kind or data["recorded_at"] > by_kind[kind]["recorded_at"]:
            by_kind[kind] = data
    return by_kind


def all_runs(results: Path, kind: str) -> list[dict]:
    runs = []
    for path in sorted(results.glob(f"{kind}_*.json")):
        data = json.loads(path.read_text())
        data["_file"] = path.name
        runs.append(data)
    return sorted(runs, key=lambda d: d["recorded_at"])


def f(value, digits=1, unit=""):
    if value is None:
        return "—"
    return f"{value:.{digits}f}{unit}"


def verdict(ok: bool) -> str:
    return "**PASS**" if ok else "**FAIL**"


def env_line(d: dict) -> str:
    e = d.get("environment", {})
    cpu = e.get("cpu") or e.get("processor") or e.get("machine")
    dirty = " (uncommitted changes)" if e.get("git_dirty") else ""
    return f"{cpu}, {e.get('memory_gb', '?')} GB RAM, {e.get('system', '')}; commit `{e.get('git_commit', '?')}`{dirty}; recorded {d['recorded_at'][:16].replace('T', ' ')} UTC"


def latency_section(d: dict) -> list[str]:
    e2e, api = d["end_to_end_ms"], d["api_ms"]
    ok = e2e.get("n", 0) > 0 and d["missed_on_socket"] == 0 and (e2e.get("p95") or 1e9) <= 2000
    s = d["settings"]
    return [
        "### Event-to-dashboard latency (NFR-01)",
        "",
        f"Camera events posted every {s['interval_s']} s with a simulator token; time measured from sending the event to the dashboard socket delivering it. {env_line(d)}.",
        "",
        "| Measure | n | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) |",
        "|---|---:|---:|---:|---:|---:|",
        f"| API response | {api.get('n', 0)} | {f(api.get('p50'))} | {f(api.get('p95'))} | {f(api.get('p99'))} | {f(api.get('max'))} |",
        f"| End to end (event → dashboard) | {e2e.get('n', 0)} | {f(e2e.get('p50'))} | {f(e2e.get('p95'))} | {f(e2e.get('p99'))} | {f(e2e.get('max'))} |",
        "",
        f"Sent {d['sent']}, delivered {d['delivered_on_socket']}, missed {d['missed_on_socket']}. Target: {d['target']}. Result: {verdict(ok)}.",
        "",
        "The dashboard can receive an event slightly before the camera receives its HTTP response, because the server broadcasts when the alert is committed, before it finishes the response.",
        "",
    ]


def recovery_section(runs: list[dict]) -> list[str]:
    """Every recovery run, oldest first, so a failure and its fix both stay visible."""
    d = runs[-1]
    s = d["settings"]
    lines = [
        "### Outage recovery (NFR-02)",
        "",
        f"The camera outbox queued events while the API was unreachable, simulated with a proxy switched off. Midway through each outage the sender process was restarted. {env_line(d)}.",
        "",
        "| Run (UTC) | Events | Outage (s) | Retry ceiling (s) | Queued at restore | Recovery (s) | Stored once | Lost | Duplicated | Result |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in runs:
        rs = r["settings"]
        lines.append(
            f"| {r['recorded_at'][:16].replace('T', ' ')} | {rs['events']} | {f(rs['outage_s'], 0)} | {f(rs['max_backoff_s'], 0)} | "
            f"{r['queued_when_restored']} | {f(r['recovery_s'])} | {r['stored_once']} | {r['lost']} | {r['duplicated']} | {verdict(r['passed'])} |"
        )
    lines += [
        "",
        f"Recovery can take up to one retry ceiling after the API returns. Target: {d['target']}.",
        "",
    ]
    return lines


def fps_section(runs: list[dict]) -> list[str]:
    lines = [
        "### Inference throughput with all detectors (NFR-04)",
        "",
        "Detection and decoding only (no capture or display), so camera FPS is at most these figures.",
        "",
        "| Device | Resolution | Frames | FPS | Frame p50 (ms) | Frame p95 (ms) | Fire model | Result (≥ 10 FPS) |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for d in runs:
        s, fm = d["settings"], d["frame_ms"]
        lines.append(
            f"| {s['device']} | {s['resolution']} | {s['frames_measured']} | {f(d['fps'])} | {f(fm.get('p50'))} | {f(fm.get('p95'))} | "
            f"{'yes' if s['fire_model_present'] else 'not trained yet'} | {verdict((d['fps'] or 0) >= 10)} |"
        )
    lines += ["", "Per stage (each runs on its own schedule):", "", "| Device | Stage | Every n frames | n | p50 (ms) | p95 (ms) |", "|---|---|---:|---:|---:|---:|"]
    every = {"ppe": 1, "coco": "coco_qr", "qr": "coco_qr", "pose": "pose", "fire": "fire"}
    for d in runs:
        for stage, st in d["stage_ms"].items():
            key = every[stage]
            n_every = 1 if key == 1 else d["settings"]["intervals"][key]
            lines.append(f"| {d['settings']['device']} | {stage} | {n_every} | {st['n']} | {f(st['p50'])} | {f(st['p95'])} |")
    lines += ["", f"Source: {runs[0]['settings']['source']}. {env_line(runs[0])}.", ""]
    return lines


SOAK_HOURS = 2.0


def soak_section(d: dict) -> list[str]:
    e2e = d["end_to_end_ms"]
    full = d["settings"]["hours"] >= SOAK_HOURS
    ok = full and d["probes_missed"] == 0 and d.get("unexpected_socket_drops", 0) == 0 and d["forced_reconnect_s"] is not None
    lines = [
        "### Soak test (NFR-05)",
        "",
        f"{f(d['settings']['hours'], 1)} h with the stack running and a probe every {d['settings']['probe_interval_s']} s; processes monitored: {', '.join(d['settings']['processes_found']) or 'none found'}. {env_line(d)}.",
        "",
        "| Probes | Missed | Latency p50 (ms) | p95 (ms) | Unexpected socket drops | Forced reconnect (s) | Errors |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {e2e.get('n', 0)} | {d['probes_missed']} | {f(e2e.get('p50'))} | {f(e2e.get('p95'))} | {d.get('unexpected_socket_drops', '—')} | {f(d['forced_reconnect_s'])} | {d['error_count']} |",
        "",
        "| Process | Memory start (MB) | End (MB) | Max (MB) | Change (MB) |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, m in d["memory"].items():
        if m:
            lines.append(f"| {label} | {f(m['first_mb'])} | {f(m['last_mb'])} | {f(m['max_mb'])} | {f(m['change_mb'])} |")
    result = verdict(ok) if full else (
        f"**validation run only** ({f(d['settings']['hours'] * 60, 0)} min); the {SOAK_HOURS:g} h soak has not been run yet"
    )
    lines += ["", f"Target: {d['target']}. Result: {result}.", ""]
    return lines


def render(by_kind: dict[str, dict], recovery_runs: list[dict] | None = None) -> str:
    lines = [
        "# Chapter 5 measurements",
        "",
        "Generated by `tools/measure/make_tables.py` from raw results in `tools/measure/results/`. Targets are the proposed acceptance targets in `docs/CLAUDE_PHASED_IMPLEMENTATION_PLAN.md`, not university requirements.",
        "",
    ]
    missing = []
    if "latency" in by_kind:
        lines += latency_section(by_kind["latency"])
    else:
        missing.append("latency")
    recovery_runs = recovery_runs or ([by_kind["recovery"]] if "recovery" in by_kind else [])
    if recovery_runs:
        lines += recovery_section(recovery_runs)
    else:
        missing.append("recovery")
    fps_runs = [d for k, d in sorted(by_kind.items()) if k.startswith("fps_")]
    if fps_runs:
        lines += fps_section(fps_runs)
    else:
        missing.append("fps")
    if "soak" in by_kind:
        lines += soak_section(by_kind["soak"])
    else:
        missing.append("soak")
    if missing:
        lines += ["### Not yet measured", "", ", ".join(missing) + ".", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=common.RESULTS_DIR)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    text = render(latest(args.results), all_runs(args.results, "recovery"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
