#!/usr/bin/env python3
"""Unpack a Parquet copy of a YOLO dataset into image and label folders.

Some mirrors of D-Fire (for example the Hugging Face copy
``badsaarow/d-fire``) store each split as Parquet files with one row per
image: the encoded image, its YOLO label text and the original file name.
This writes ``<out>/<split>/images/<filename>`` and
``<out>/<split>/labels/<stem>.txt``, the layout ``prepare_fire_dataset.py``
reads, and prints per-split counts so the copy can be checked against the
dataset's published figures before anything is trained on it.

    python fire/unpack_parquet_dataset.py --parquet fire/datasets/dfire_hf \\
        --out fire/datasets/D-Fire --classes smoke,fire

Only ``image``, ``label`` and ``filename`` columns are read; nothing in the
files is executed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def split_of(path: Path) -> str:
    """``train-00000-of-00009.parquet`` -> ``train``."""
    return path.name.split("-", 1)[0]


def image_bytes(value) -> bytes:
    # The Hugging Face ``Image`` feature is stored as {"bytes": ..., "path": ...}.
    if isinstance(value, dict):
        value = value.get("bytes")
    if not isinstance(value, (bytes, bytearray)):
        raise ValueError("row has no encoded image")
    return bytes(value)


def unpack(parquet_dir: Path, out: Path, classes: list[str]) -> dict:
    import pyarrow.parquet as pq

    stats: dict[str, Counter] = {}
    for path in sorted(parquet_dir.glob("*.parquet")):
        split = split_of(path)
        counts = stats.setdefault(split, Counter())
        images = out / split / "images"
        labels = out / split / "labels"
        images.mkdir(parents=True, exist_ok=True)
        labels.mkdir(parents=True, exist_ok=True)
        table = pq.read_table(path, columns=["image", "label", "filename"])
        for row in table.to_pylist():
            name = Path(row["filename"] or "").name
            if not SAFE_NAME.match(name):
                counts["skipped_bad_name"] += 1
                continue
            (images / name).write_bytes(image_bytes(row["image"]))
            text = (row["label"] or "").strip()
            (labels / f"{Path(name).stem}.txt").write_text(text + ("\n" if text else ""))
            counts["images"] += 1
            boxes = [line.split()[0] for line in text.splitlines() if line.strip()]
            if not boxes:
                counts["empty"] += 1
            for cid in boxes:
                idx = int(cid) if cid.isdigit() else -1
                counts[classes[idx] if 0 <= idx < len(classes) else f"class_{cid}"] += 1
    return {split: dict(c) for split, c in stats.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parquet", type=Path, required=True, help="Folder with <split>-*.parquet files")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--classes", required=True, help="Class names in id order, e.g. smoke,fire")
    args = ap.parse_args(argv)
    stats = unpack(args.parquet, args.out, args.classes.split(","))
    total = {k: sum(s.get(k, 0) for s in stats.values()) for k in {k for s in stats.values() for k in s}}
    report = {"splits": stats, "total": total}
    (args.out / "unpack_counts.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
