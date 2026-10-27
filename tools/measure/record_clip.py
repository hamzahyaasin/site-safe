#!/usr/bin/env python3
"""Record an evaluation clip from a camera (for evaluate_clip.py).

Writes the camera's raw frames, without any overlay, to an MP4 as they
arrive. The frame rate written into the file is measured during the
countdown, so the clip plays back at real speed, which matters because
evaluate_clip.py times every tracker by the video's own clock. ``<clip>.json``
records when, how long, the resolution, the source and both frame rates. A countdown and a red "REC" marker are drawn on
the preview window only. Press Q to stop early.

    python tools/measure/record_clip.py --out clips/webcam_one_person.mp4 --seconds 60
    python tools/measure/record_clip.py --source rtsp://192.168.1.20/stream --out clips/gate.mp4

Write the true episodes for the clip next to it (copy
clip_annotations_template.csv), then score the pipeline with
evaluate_clip.py --video <clip> --annotations <csv>.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def parse_source(raw: str) -> int | str:
    try:
        return int(raw)
    except ValueError:
        return raw


def metadata(
    source, out: Path, frames: int, seconds: float, size: tuple[int, int], started: datetime, file_fps: float
) -> dict:
    achieved = frames / seconds if seconds > 0 else None
    return {
        "clip": out.name,
        "source": str(source),
        "started_at_utc": started.isoformat(),
        "frames": frames,
        "duration_s": round(seconds, 2),
        "fps_achieved": round(achieved, 2) if achieved else None,
        "fps_in_file": round(file_fps, 2),
        # Playback runs at fps_in_file; a large gap means clip time drifts from real time.
        "timing_error_pct": round(abs(file_fps - achieved) / achieved * 100, 1) if achieved else None,
        "width": size[0],
        "height": size[1],
        "machine": f"{platform.system()} {platform.machine()}",
        "note": "Raw camera frames, no overlays. Annotate true episodes in a CSV for evaluate_clip.py.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="0", help="Camera index (default 0) or stream URL")
    ap.add_argument("--out", type=Path, required=True, help="Output .mp4 path")
    ap.add_argument("--seconds", type=float, default=60.0, help="Recording length (default 60)")
    ap.add_argument("--countdown", type=int, default=5, help="Seconds of preview before recording starts (default 5)")
    args = ap.parse_args(argv)
    if args.seconds <= 0:
        ap.error("--seconds must be greater than zero")
    if args.out.suffix.lower() != ".mp4":
        ap.error("--out must end in .mp4")

    import cv2

    source = parse_source(args.source)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"could not open camera {source} (on macOS, allow camera access for this terminal app)", file=sys.stderr)
        return 1
    ok, frame = cap.read()
    if not ok:
        print("camera opened but returned no frame", file=sys.stderr)
        return 1
    h, w = frame.shape[:2]
    window = "Site-Safe clip recorder (Q to stop)"

    countdown_end = time.monotonic() + max(args.countdown, 2)
    counted, t_count = 0, time.monotonic()
    while time.monotonic() < countdown_end:
        ok, frame = cap.read()
        if not ok:
            continue
        counted += 1
        preview = frame.copy()
        left = int(countdown_end - time.monotonic()) + 1
        cv2.putText(preview, f"Recording in {left}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        cv2.imshow(window, preview)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return 0
    file_fps = counted / (time.monotonic() - t_count)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(args.out), cv2.VideoWriter_fourcc(*"mp4v"), file_fps, (w, h))
    frames = 0
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    while time.monotonic() - t0 < args.seconds:
        ok, frame = cap.read()
        if not ok:
            continue
        writer.write(frame)
        frames += 1
        preview = frame.copy()
        cv2.circle(preview, (30, 30), 10, (0, 0, 255), -1)
        cv2.putText(preview, f"REC {time.monotonic() - t0:4.1f}s", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imshow(window, preview)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    seconds = time.monotonic() - t0
    writer.release()
    cap.release()
    cv2.destroyAllWindows()
    if not frames:
        print("no frames recorded", file=sys.stderr)
        args.out.unlink(missing_ok=True)
        return 1

    meta = metadata(source, args.out, frames, seconds, (w, h), started, file_fps)
    args.out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    if meta["timing_error_pct"] and meta["timing_error_pct"] > 10:
        print(f"warning: the camera ran at {meta['fps_achieved']} FPS but the file plays at {file_fps:.1f}; "
              "clip timings will be off by more than 10%", file=sys.stderr)
    print(f"saved {args.out} ({frames} frames, {seconds:.1f} s, {meta['fps_achieved']} FPS, {w}x{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
