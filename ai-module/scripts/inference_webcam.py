#!/usr/bin/env python3
"""
Webcam inference: YOLO + OpenCV, JSON per frame (violations by regex on class names).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


def ai_module_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_weights() -> Path:
    return ai_module_root() / "runs" / "train" / "ppe_yolov10n" / "weights" / "best.pt"


def detections_from_result(result) -> list[dict]:
    names = result.names
    boxes = result.boxes
    out: list[dict] = []
    if boxes is None or len(boxes) == 0:
        return out

    xyxy = boxes.xyxy.cpu().tolist()
    confs = boxes.conf.cpu().tolist()
    clss = boxes.cls.cpu().int().tolist()
    for i, cid in enumerate(clss):
        name = str(names[int(cid)])
        out.append(
            {
                "class": name,
                "class_id": int(cid),
                "confidence": round(float(confs[i]), 4),
                "xyxy": [round(float(x), 2) for x in xyxy[i]],
            }
        )
    return out


def filter_violations(detections: list[dict], pattern: re.Pattern | None) -> list[dict]:
    if pattern is None:
        return []
    return [d for d in detections if pattern.search(d["class"])]


def counts_by_class(detections: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in detections:
        c = d["class"]
        counts[c] = counts.get(c, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="YOLO webcam inference + JSON violation summary.")
    p.add_argument(
        "--weights",
        type=Path,
        default=default_weights(),
        help="Path to trained weights.",
    )
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument(
        "--violation-pattern",
        type=str,
        default=r"no[-_]?|missing|without|unsafe|violation|non[-_]?compliance",
    )
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--device", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.chdir(ai_module_root())

    weights = args.weights.resolve()
    if not weights.is_file():
        print(f"Weights not found: {weights}", file=sys.stderr)
        sys.exit(1)

    violation_re: re.Pattern | None
    if args.violation_pattern.strip():
        violation_re = re.compile(args.violation_pattern, re.IGNORECASE)
    else:
        violation_re = None

    model = YOLO(str(weights))
    predict_kw: dict = dict(stream=False, verbose=False, conf=args.conf, imgsz=args.imgsz)
    if args.device is not None:
        predict_kw["device"] = args.device

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Could not open camera index {args.camera}", file=sys.stderr)
        sys.exit(1)

    frame_index = 0
    print("Streaming… Press 'q' to quit.", file=sys.stderr)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            t0 = time.perf_counter()
            results = model.predict(frame, **predict_kw)
            infer_ms = round((time.perf_counter() - t0) * 1000, 2)

            result = results[0]
            detections = detections_from_result(result)
            violations = filter_violations(detections, violation_re)

            summary = {
                "frame": frame_index,
                "inference_ms": infer_ms,
                "has_violations": len(violations) > 0,
                "violation_count": len(violations),
                "violations": violations,
                "detection_count": len(detections),
                "counts_by_class": counts_by_class(detections),
            }
            print(json.dumps(summary), flush=True)

            annotated = result.plot()
            cv2.imshow("Site-Safe PPE (q to quit)", annotated)
            frame_index += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
