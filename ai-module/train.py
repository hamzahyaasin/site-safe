#!/usr/bin/env python3
"""
Train Ultralytics YOLOv10n on ppe_dataset/data.yaml (CPU-friendly defaults).
"""

from __future__ import annotations

import os
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)

    data_yaml = root / "ppe_dataset" / "data.yaml"
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Missing dataset config: {data_yaml}")

    model = YOLO("yolov10n.pt")
    model.train(
        data=str(data_yaml),
        epochs=50,
        imgsz=640,
        batch=8,
        workers=2,
        project="runs/train",
        name="exp",
        exist_ok=True,
    )

    print("TRAINING COMPLETE. Model saved to runs/train/exp/weights/best.pt")


if __name__ == "__main__":
    main()
