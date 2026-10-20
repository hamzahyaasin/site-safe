#!/usr/bin/env python3
"""Inference throughput with every detector enabled (NFR-04).

Runs the camera pipeline's model schedule on recorded frames, without a
window or network, and times each stage:

* PPE detector every frame
* person/vehicle detector every 3rd frame (proximity, inactivity)
* pose model every 3rd frame (falls)
* QR badge decoding every 3rd frame
* fire/smoke detector every 5th frame (only if models/fire_smoke.pt exists)

The intervals are read from inference.py, so the benchmark follows the
pipeline if they change. Frames come from a video (``--video``) or a folder
of images (``--images``), resized to ``--width``x``--height`` like a camera
stream. The first ``--warmup`` frames are excluded (model load and kernel
compilation).

    python tools/measure/fps.py --images ai-module/ppe_dataset/test/images --frames 300 --device mps
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AI = HERE.parents[1] / "ai-module"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AI))
import common  # noqa: E402


def frame_source(args):
    import cv2

    if args.video:
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            raise SystemExit(f"cannot open {args.video}")
        frames = []
        while len(frames) < args.frames + args.warmup:
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop a short clip
                continue
            frames.append(cv2.resize(frame, (args.width, args.height)))
        return frames, f"video {Path(args.video).name}"
    paths = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not paths:
        raise SystemExit(f"no images in {args.images}")
    frames = []
    for i in range(args.frames + args.warmup):
        frame = cv2.imread(str(paths[i % len(paths)]))
        frames.append(cv2.resize(frame, (args.width, args.height)))
    return frames, f"{len(paths)} images from {Path(args.images).name}"


def run(args) -> dict:
    os.chdir(AI)
    import identity
    import inference
    from ultralytics import YOLO

    device = args.device
    stages = {"ppe": [], "coco": [], "pose": [], "qr": [], "fire": []}
    models = {"ppe": YOLO(str(inference.resolve_model_path()))}
    if Path(inference.resolve_proximity_model_path()).is_file():
        models["coco"] = YOLO(str(inference.resolve_proximity_model_path()))
    if Path(inference.resolve_fall_model_path()).is_file():
        models["pose"] = YOLO(str(inference.resolve_fall_model_path()))
    fire_path = inference.resolve_fire_model_path()
    if fire_path.is_file() and not args.no_fire:
        models["fire"] = YOLO(str(fire_path))
    qr = identity.QrDecoder() if "coco" in models else None

    frames, source = frame_source(args)
    totals = []
    for i, frame in enumerate(frames):
        t_frame = time.perf_counter()

        def timed(name, fn):
            t = time.perf_counter()
            fn()
            if i >= args.warmup:
                stages[name].append((time.perf_counter() - t) * 1000)

        timed("ppe", lambda: models["ppe"].predict(frame, verbose=False, conf=inference.PPE_CONF, device=device))
        if "coco" in models and i % inference.PROXIMITY_FRAME_INTERVAL == 0:
            timed("coco", lambda: models["coco"].predict(frame, verbose=False, conf=inference.PROXIMITY_CONF, device=device))
            timed("qr", lambda: qr.decode(frame))
        if "pose" in models and i % inference.FALL_FRAME_INTERVAL == 0:
            timed("pose", lambda: models["pose"].predict(frame, verbose=False, conf=inference.FALL_CONF, device=device))
        if "fire" in models and i % inference.FIRE_FRAME_INTERVAL == 0:
            timed("fire", lambda: models["fire"].predict(frame, verbose=False, conf=0.45, device=device))
        if i >= args.warmup:
            totals.append((time.perf_counter() - t_frame) * 1000)

    elapsed_s = sum(totals) / 1000
    return {
        "settings": {
            "device": device,
            "resolution": f"{args.width}x{args.height}",
            "frames_measured": len(totals),
            "warmup_frames": args.warmup,
            "source": source,
            "intervals": {
                "coco_qr": inference.PROXIMITY_FRAME_INTERVAL,
                "pose": inference.FALL_FRAME_INTERVAL,
                "fire": inference.FIRE_FRAME_INTERVAL,
            },
            "models": {name: Path(m.ckpt_path).name if getattr(m, "ckpt_path", None) else name for name, m in models.items()},
            "fire_model_present": "fire" in models,
        },
        "frame_ms": common.summarise(totals),
        "fps": len(totals) / elapsed_s if elapsed_s else None,
        "stage_ms": {name: common.summarise(v) for name, v in stages.items() if v},
        "note": "Detection and decoding only: excludes capture, drawing and display. "
        "Sustained camera FPS is at most this figure.",
        "target": ">= 10 FPS with all detectors on the demo machine (proposed NFR-04)",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video")
    src.add_argument("--images")
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--warmup", type=int, default=15)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--device", default="cpu", help="cpu, mps (Apple GPU) or a CUDA index such as 0")
    ap.add_argument("--no-fire", action="store_true")
    args = ap.parse_args(argv)
    if args.images:
        args.images = str(Path(args.images).resolve())
    if args.video:
        args.video = str(Path(args.video).resolve())
    result = run(args)
    path = common.save_result(f"fps_{args.device}", result)
    print(f"{result['fps']:.1f} FPS on {args.device} at {args.width}x{args.height} "
          f"(frame p95 {result['frame_ms']['p95']:.0f} ms, {result['settings']['frames_measured']} frames)")
    for name, s in result["stage_ms"].items():
        print(f"  {name:5s} p50 {s['p50']:.1f} ms  p95 {s['p95']:.1f} ms  (n={s['n']})")
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
