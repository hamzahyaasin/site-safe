#!/usr/bin/env python3
"""
Train Ultralytics YOLOv10n on a PPE dataset (YOLO format).

Dataset: <ai-module>/ppe_dataset/data.yaml
Training outputs: <ai-module>/runs/train/<name>/
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ultralytics import YOLO


def ai_module_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_data_yaml() -> Path:
    return ai_module_root() / "ppe_dataset" / "data.yaml"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLOv10n on PPE dataset (Ultralytics).")
    p.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to data.yaml (default: ppe_dataset/data.yaml inside ai-module).",
    )
    p.add_argument("--weights", type=str, default="yolov10n.pt", help="Initial weights / model name.")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument(
        "--project",
        type=str,
        default="runs/train",
        help="Project dir relative to ai-module (Ultralytics: project/name/).",
    )
    p.add_argument("--name", type=str, default="ppe_yolov10n", help="Run name.")
    p.add_argument("--device", type=str, default=None, help="e.g. 0, cpu, mps — default: auto.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = ai_module_root()
    os.chdir(root)

    data_path = (args.data or default_data_yaml()).resolve()
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset config not found: {data_path}")

    model = YOLO(args.weights)
    train_kw = dict(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
    )
    if args.device is not None:
        train_kw["device"] = args.device

    model.train(**train_kw)


if __name__ == "__main__":
    main()
