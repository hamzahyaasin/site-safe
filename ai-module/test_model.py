#!/usr/bin/env python3
"""
Validate trained YOLO weights on the test split (mAP) and save annotated predictions.
"""

from __future__ import annotations

import os
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)

    weights = root / "runs" / "train" / "exp" / "weights" / "best.pt"
    data_yaml = root / "ppe_dataset" / "data.yaml"
    test_images = root / "ppe_dataset" / "test" / "images"
    out_dir = root / "test_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not weights.is_file():
        raise FileNotFoundError(
            f"Weights not found: {weights}\nTrain first: python train.py"
        )
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Missing dataset config: {data_yaml}")

    model = YOLO(str(weights))

    # mAP on labeled test split (requires test/labels alongside test/images)
    metrics = model.val(
        data=str(data_yaml),
        split="test",
        imgsz=640,
        batch=8,
        workers=2,
        plots=False,
    )

    box = metrics.box
    print("-" * 72)
    print("TEST SPLIT METRICS (Ultralytics val)")
    print(f"  mAP50-95: {float(box.map):.4f}")
    print(f"  mAP50:    {float(box.map50):.4f}")
    maps = getattr(box, "maps", None)
    if maps is not None:
        try:
            per_class = [round(float(x), 4) for x in maps.tolist()]
        except Exception:
            per_class = list(maps)
        print(f"  mAP per class: {per_class}")
    print("-" * 72)

    if not test_images.is_dir():
        print(f"Warning: missing test images folder: {test_images}")
        return

    # Save annotated predictions for every test image
    model.predict(
        source=str(test_images),
        imgsz=640,
        conf=0.25,
        save=True,
        project=str(out_dir),
        name="annotated",
        exist_ok=True,
        verbose=False,
    )
    print(f"Annotated images saved under: {out_dir / 'annotated'}")


if __name__ == "__main__":
    main()
