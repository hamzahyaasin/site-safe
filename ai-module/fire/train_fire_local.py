#!/usr/bin/env python3
"""Train and evaluate the fire/smoke detector on this machine.

The local counterpart of ``train_fire_smoke_colab.ipynb``, with the same
recipe (YOLO11-small, 640 px, AdamW, lr 0.001, seed 42). It writes an
export folder like the PPE model's ``sitesafe_v5_export``:

* ``run_manifest.json``: settings, environment, dataset counts, timing;
* ``held_out_test_metrics.json``: one evaluation on the test split, which
  played no part in training or model selection;
* ``fire_smoke.pt`` and its SHA-256, plus Ultralytics' ``args.yaml`` and
  ``results.csv``.

``--hours`` caps training time (Ultralytics' ``time`` setting, which also
fits the learning-rate schedule to that budget), so an overnight run ends
on time; validation-based early stopping still applies. ``--install``
copies the weights to ``models/fire_smoke.pt``, where inference.py
looks for them.

    python fire/train_fire_local.py --data fire/datasets/fire_v1/data.yaml --hours 9 --install
    python fire/train_fire_local.py --data ... --fraction 0.05 --epochs 1 --name timing   # time an epoch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AI = HERE.parent
sys.path.insert(0, str(AI))

SEED = 42


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics_dict(metrics, counts: dict) -> dict:
    names = metrics.names
    box = metrics.box
    return {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": "test",
        "overall": {"precision": float(box.mp), "recall": float(box.mr), "map50": float(box.map50), "map50_95": float(box.map)},
        "per_class": {
            names[int(c)]: {"precision": float(p), "recall": float(r), "map50": float(m50), "map50_95": float(m)}
            for c, p, r, m50, m in zip(box.ap_class_index, box.p, box.r, box.ap50, box.ap)
        },
        "test_counts": counts,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="data.yaml written by prepare_fire_dataset.py")
    ap.add_argument("--model", default="yolo11s.pt", help="Starting weights (default yolo11s.pt, COCO-pretrained)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--hours", type=float, default=None, help="Stop training after this many hours")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--fraction", type=float, default=1.0, help="Share of training images to use (for timing runs)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--name", default="fire_smoke_v1")
    ap.add_argument("--export-dir", type=Path, default=None, help="Default: models/<name>_export")
    ap.add_argument("--install", action="store_true", help="Copy the weights to models/fire_smoke.pt")
    ap.add_argument("--skip-test", action="store_true", help="Do not evaluate on the test split (timing runs)")
    args = ap.parse_args(argv)

    import random

    import numpy as np
    import torch
    import ultralytics
    from ultralytics import YOLO

    from inference import pick_device

    device = pick_device(args.device)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    dataset_dir = args.data.resolve().parent
    manifest_path = dataset_dir / "manifest.json"
    dataset = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    export = (args.export_dir or AI / "models" / f"{args.name}_export").resolve()
    export.mkdir(parents=True, exist_ok=True)

    train_args = dict(
        data=str(args.data.resolve()), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        patience=args.patience, optimizer="AdamW", lr0=0.001, seed=SEED, deterministic=False,
        device=device, workers=args.workers, fraction=args.fraction,
        project=str(AI / "runs" / "fire"), name=args.name, exist_ok=False, plots=True,
    )
    if args.hours:
        train_args["time"] = args.hours
    run = {
        "status": "training",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_source": args.model,
        "train_args": train_args,
        "environment": {
            "python": platform.python_version(),
            "ultralytics": ultralytics.__version__,
            "torch": torch.__version__,
            "device": device,
            "machine": f"{platform.system()} {platform.machine()}",
        },
        "dataset": {"source": dataset.get("source"), "counts": dataset.get("counts"),
                    "skipped_images": len(dataset.get("skipped_images", []))},
        "notes": "deterministic=False: some MPS kernels have no deterministic version; the seed is still fixed.",
    }
    (export / "run_manifest.json").write_text(json.dumps(run, indent=2))

    t0 = time.monotonic()
    model = YOLO(args.model)
    model.train(**train_args)
    run_dir = Path(model.trainer.save_dir)
    best = run_dir / "weights" / "best.pt"
    run.update(status="trained", training_seconds=round(time.monotonic() - t0), run_dir=str(run_dir),
               epochs_completed=int(getattr(model.trainer, "epoch", -1)) + 1, best_fitness=float(model.trainer.best_fitness or 0))
    for name in ("args.yaml", "results.csv"):
        if (run_dir / name).exists():
            shutil.copy2(run_dir / name, export / name)

    if not args.skip_test:
        metrics = YOLO(str(best)).val(data=str(args.data.resolve()), split="test", imgsz=args.imgsz, batch=args.batch,
                                      device=device, project=str(AI / "runs" / "fire"), name=f"{args.name}_held_out", plots=True)
        results = metrics_dict(metrics, (dataset.get("counts") or {}).get("test", {}))
        (export / "held_out_test_metrics.json").write_text(json.dumps(results, indent=2))
        run["status"] = "training_and_held_out_test_completed"
        print(json.dumps(results["overall"], indent=2))

    shutil.copy2(best, export / "fire_smoke.pt")
    run["weights_sha256"] = sha256(export / "fire_smoke.pt")
    run["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    if args.install:
        shutil.copy2(best, AI / "models" / "fire_smoke.pt")
        run["installed_to"] = "models/fire_smoke.pt"
    (export / "run_manifest.json").write_text(json.dumps(run, indent=2))
    print(f"exported to {export}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
