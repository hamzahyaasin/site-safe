#!/usr/bin/env python3
"""Score the camera pipeline's alerts on an annotated video clip (FR-04/05/06/10).

The clip is run through the real pipeline (``ai-module/inference.py``)
headless, with every tracker timed by the video's own timestamps
(``--video-clock``), so persistence and episode timeouts behave as they
would live however fast the file is processed. Every event the camera
would send is recorded (``--events-out``) and nothing is delivered: the
API address points at a closed port and the outbox lives in a temporary
folder.

Annotations are a CSV with one row per true episode (see
``clip_annotations_template.csv``)::

    event,start_s,end_s,badge,person,notes
    no-helmet,3.0,41.5,,Hamza,walks in without helmet
    no-vest,3.0,41.5,SSW1:abc123,Hamza,
    FALL,62.0,70.0,,Ali,staged fall on mattress

``event`` is a PPE class (no-helmet, no-vest, no-gloves, no-boots,
no-goggles) or an alert type (FALL, INACTIVITY, VEHICLE_PROXIMITY, FIRE,
SMOKE). An alert counts for an episode when it has the same event and
fires between ``start_s`` and ``end_s + --grace``. Each episode takes at
most one alert; further alerts inside a matched episode are duplicates,
and alerts outside every episode are false alerts.

    python tools/measure/evaluate_clip.py --video clip.mp4 --annotations clip.csv
    python tools/measure/evaluate_clip.py --events events.jsonl --annotations clip.csv   # score a saved run

Extra pipeline options go after ``--``, for example ``-- --inactivity-timeout 30``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

AI = common.REPO / "ai-module"
ACTIVITY_EVENTS = {"SIGHTING", "IDLE_START", "IDLE_END"}


def load_annotations(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            event = (row.get("event") or "").strip()
            if not event or event.startswith("#"):
                continue
            start, end = float(row["start_s"]), float(row["end_s"])
            if end < start:
                raise ValueError(f"line {i}: end_s {end} is before start_s {start}")
            rows.append({
                "event": event,
                "start": start,
                "end": end,
                "badge": (row.get("badge") or "").strip() or None,
                "person": (row.get("person") or "").strip(),
            })
    return rows


def load_events(path: Path) -> list[dict]:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [e for e in events if e.get("event") not in ACTIVITY_EVENTS]


def score(alerts: list[dict], annotations: list[dict], grace: float = 5.0) -> dict:
    """Match alerts to annotated episodes; see the module docstring for the rules."""
    alerts = sorted(alerts, key=lambda a: a["t"])
    used: set[int] = set()
    matches = []
    for ann in sorted(annotations, key=lambda a: a["start"]):
        window = [
            i for i, a in enumerate(alerts)
            if i not in used and a["event"] == ann["event"] and ann["start"] <= a["t"] <= ann["end"] + grace
        ]
        # Prefer the wearer's own badge, then the earliest alert.
        same_badge = [i for i in window if ann["badge"] and alerts[i].get("badge") == ann["badge"]]
        pick = (same_badge or window or [None])[0]
        if pick is not None:
            used.add(pick)
        matches.append((ann, alerts[pick] if pick is not None else None))

    duplicates, false_alerts = [], []
    for i, a in enumerate(alerts):
        if i in used:
            continue
        inside = any(
            ann["event"] == a["event"] and ann["start"] <= a["t"] <= ann["end"] + grace and hit is not None
            for ann, hit in matches
        )
        (duplicates if inside else false_alerts).append(a)

    def summary(event=None):
        ms = [(ann, hit) for ann, hit in matches if event is None or ann["event"] == event]
        hits = [(ann, hit) for ann, hit in ms if hit is not None]
        fa = [a for a in false_alerts if event is None or a["event"] == event]
        dup = [a for a in duplicates if event is None or a["event"] == event]
        delays = [hit["t"] - ann["start"] for ann, hit in hits]
        badged = [(ann, hit) for ann, hit in hits if ann["badge"]]
        return {
            "episodes": len(ms),
            "detected": len(hits),
            "missed": len(ms) - len(hits),
            "false_alerts": len(fa),
            "duplicates": len(dup),
            "recall": len(hits) / len(ms) if ms else None,
            "precision": len(hits) / (len(hits) + len(fa)) if hits or fa else None,
            "delay_s_median": statistics.median(delays) if delays else None,
            "delay_s_max": max(delays) if delays else None,
            "identity": {
                "episodes_with_badge": len(badged),
                "correct": sum(1 for ann, hit in badged if hit.get("badge") == ann["badge"]),
                "wrong": sum(1 for ann, hit in badged if hit.get("badge") not in (None, ann["badge"])),
                "unidentified": sum(1 for ann, hit in badged if hit.get("badge") is None),
            },
        }

    kinds = sorted({a["event"] for a in annotations} | {a["event"] for a in alerts})
    return {
        "overall": summary(),
        "by_event": {k: summary(k) for k in kinds},
        "missed": [ann for ann, hit in matches if hit is None],
        "false_alerts": false_alerts,
        "duplicates": duplicates,
    }


def run_pipeline(video: Path, events_out: Path, extra: list[str]) -> int:
    env = dict(os.environ)
    with tempfile.TemporaryDirectory() as outbox:
        env.update(
            SITESAFE_OUTBOX_DIR=outbox,
            SITESAFE_API_BASE="http://127.0.0.1:9/api",  # nothing listens: events stay local
            SITESAFE_DEVICE_KEY="",
        )
        python = AI / ".venv" / "bin" / "python"
        cmd = [str(python if python.exists() else sys.executable), "-u", "inference.py",
               "--source", str(video), "--camera-id", "EVAL", "--video-clock", "--no-display", "--no-live",
               "--events-out", str(events_out), *extra]
        return subprocess.run(cmd, cwd=AI, env=env).returncode


def print_report(result: dict) -> None:
    def pct(v):
        return "—" if v is None else f"{v:.0%}"

    print(f"{'event':<18}{'episodes':>9}{'detected':>9}{'missed':>7}{'false':>7}{'dupl.':>7}{'recall':>8}{'prec.':>7}{'delay':>8}")
    for name, s in [*result["by_event"].items(), ("ALL", result["overall"])]:
        delay = "—" if s["delay_s_median"] is None else f"{s['delay_s_median']:.1f}s"
        print(f"{name:<18}{s['episodes']:>9}{s['detected']:>9}{s['missed']:>7}{s['false_alerts']:>7}"
              f"{s['duplicates']:>7}{pct(s['recall']):>8}{pct(s['precision']):>7}{delay:>8}")
    ident = result["overall"]["identity"]
    if ident["episodes_with_badge"]:
        print(f"identity on badged episodes: {ident['correct']} correct, {ident['wrong']} wrong, "
              f"{ident['unidentified']} unidentified of {ident['episodes_with_badge']}")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[: argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", type=Path, help="Run the pipeline on this clip")
    src.add_argument("--events", type=Path, help="Score a saved events file instead of running the pipeline")
    ap.add_argument("--annotations", type=Path, required=True)
    ap.add_argument("--grace", type=float, default=5.0, help="Seconds after an episode's end an alert still counts (default 5)")
    ap.add_argument("--no-save", action="store_true", help="Print only; do not write a result file")
    args = ap.parse_args(argv)

    annotations = load_annotations(args.annotations)
    if args.video:
        common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        events_path = common.RESULTS_DIR / f"clip_events_{args.video.stem}.jsonl"
        events_path.unlink(missing_ok=True)
        code = run_pipeline(args.video.resolve(), events_path, extra)
        if code:
            print(f"pipeline exited with {code}", file=sys.stderr)
            return code
    else:
        events_path = args.events
    result = score(load_events(events_path), annotations, args.grace)
    print_report(result)
    if not args.no_save:
        path = common.save_result("clip_eval", {
            "settings": {
                "video": str(args.video) if args.video else None,
                "annotations": str(args.annotations),
                "events": str(events_path),
                "grace_s": args.grace,
                "pipeline_options": extra,
            },
            **result,
        })
        print(f"saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
