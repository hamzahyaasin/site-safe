#!/usr/bin/env python3
"""Confusion matrix of a detector on the held-out test split.

The Colab evaluation saved per-class metrics but not the matrix, so the
report's Figure 5.2 is computed here from the same weights and split. A
first pass at the validator's own threshold reproduces mAP@0.5, written
beside the matrix so it can be checked against held_out_test_metrics.json;
the matrix itself is counted at the camera pipeline's candidate threshold
(inference.PPE_CONF), so it shows the boxes the pipeline actually sees.

    .venv/bin/python scripts/held_out_confusion.py \
        --weights models/sitesafe_v5.pt --data ppe_dataset/data.yaml \
        --out models/sitesafe_v5_export/held_out_confusion_matrix.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--conf", type=float, default=0.15, help="threshold for the matrix (inference.PPE_CONF)")
    args = ap.parse_args()

    model = YOLO(str(args.weights))
    common = dict(data=str(args.data), split=args.split, imgsz=640, batch=16, device=args.device, verbose=False)
    with tempfile.TemporaryDirectory() as runs:
        reference = model.val(project=runs, name="map", plots=False, **common)
        # Ultralytics fills the matrix only when plotting; the plots go with the temporary folder.
        metrics = model.val(project=runs, name="confusion", conf=args.conf, plots=True, **common)
    cm = metrics.confusion_matrix
    names = [metrics.names[i] for i in range(len(metrics.names))]
    result = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "weights": args.weights.name,
        "weights_sha256_prefix": hashlib.sha256(args.weights.read_bytes()).hexdigest()[:12],
        "split": args.split,
        "conf": args.conf,
        "iou_thres": 0.45,
        "map50": float(reference.box.map50),
        "layout": "matrix[predicted][true]; the last row and column are background",
        "classes": names + ["background"],
        "matrix": [[int(v) for v in row] for row in cm.matrix],
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"mAP@0.5 {result['map50']:.4f}; wrote {args.out}")


if __name__ == "__main__":
    main()
