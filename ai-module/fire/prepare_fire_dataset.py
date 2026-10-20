#!/usr/bin/env python3
"""Validate a YOLO-format fire/smoke dataset and write a training config.

Accepts the common layout ``<root>/<split>/images`` + ``<root>/<split>/labels``
(for example the public D-Fire dataset, whose classes are 0=smoke, 1=fire).
Labels are remapped to Site-Safe's class order (0=fire, 1=smoke) into a new
labels directory. A validation split is carved from train when the source
has none; it is chosen deterministically, and image files sharing a name
prefix (frames from the same video) stay in one split.

Writes ``<out>/images/<split>`` (symlinks to the source images, or copies
with ``--copy``) beside ``<out>/labels/<split>``, because Ultralytics finds
each label by swapping ``/images/`` for ``/labels/`` in the image path. Also
writes ``data.yaml``, ``train.txt``/``val.txt``/``test.txt`` lists and
``manifest.json`` with per-split counts, so a training run is reproducible.
Images without fire or smoke are kept as negatives; they matter for false
alarms.

    python fire/prepare_fire_dataset.py --source ~/datasets/D-Fire \
        --source-classes smoke,fire --out fire/dataset_v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

TARGET = ("fire", "smoke")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def group_key(stem: str) -> str:
    """Name prefix shared by frames of one clip, e.g. 'WEB10495_frame_012' -> 'WEB10495'."""
    return re.split(r"[_\-\s](?:frame|f|img)?\d+$", stem, maxsplit=1)[0] or stem


def in_val(group: str, fraction: float) -> bool:
    h = int(hashlib.sha256(group.encode()).hexdigest()[:8], 16)
    return (h % 10_000) / 10_000 < fraction


def remap_label(text: str, mapping: dict[int, int]) -> tuple[list[str], list[str]]:
    """Return (remapped lines, problems). Unknown classes are dropped and reported."""
    out, problems = [], []
    for n, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            problems.append(f"line {n}: expected 5 values, got {len(parts)}")
            continue
        try:
            cls = int(parts[0])
            coords = [float(v) for v in parts[1:]]
        except ValueError:
            problems.append(f"line {n}: not numeric")
            continue
        if cls not in mapping:
            problems.append(f"line {n}: class {cls} not in --source-classes")
            continue
        if not all(0.0 <= v <= 1.0 for v in coords) or coords[2] <= 0 or coords[3] <= 0:
            problems.append(f"line {n}: box outside 0-1 or empty")
            continue
        out.append(" ".join([str(mapping[cls]), *parts[1:]]))
    return out, problems


def find_splits(source: Path) -> dict[str, Path]:
    splits = {}
    for name, aliases in {"train": ("train",), "val": ("val", "valid", "validation"), "test": ("test",)}.items():
        for a in aliases:
            if (source / a / "images").is_dir():
                splits[name] = source / a
                break
    return splits


def prepare(source: Path, out: Path, source_classes: list[str], val_fraction: float = 0.1, copy: bool = False) -> dict:
    mapping = {}
    for i, name in enumerate(source_classes):
        name = name.strip().lower()
        if name not in TARGET:
            raise ValueError(f"source class {name!r} must be one of {TARGET}")
        mapping[i] = TARGET.index(name)
    splits = find_splits(source)
    if "train" not in splits:
        raise ValueError(f"no train/images directory under {source}")

    labels_out = out / "labels"
    lists: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    counts = {s: Counter() for s in lists}
    problems: list[str] = []
    skipped: list[str] = []
    for split, folder in splits.items():
        for image in sorted((folder / "images").iterdir()):
            if image.suffix.lower() not in IMAGE_EXT:
                continue
            label = folder / "labels" / f"{image.stem}.txt"
            lines, issues = remap_label(label.read_text() if label.exists() else "", mapping)
            if issues:
                # A broken label is not evidence of "no fire": leave the image
                # out rather than training on a wrong or empty label.
                problems += [f"{split}/{image.name}: {p}" for p in issues]
                skipped.append(f"{split}/{image.name}")
                continue
            target = split
            if split == "train" and "val" not in splits and in_val(group_key(image.stem), val_fraction):
                target = "val"
            # Ultralytics looks for labels beside the images by replacing
            # /images/ with /labels/; keep that structure under out/.
            label_dir = labels_out / target
            image_dir = out / "images" / target
            label_dir.mkdir(parents=True, exist_ok=True)
            image_dir.mkdir(parents=True, exist_ok=True)
            (label_dir / f"{image.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
            linked = image_dir / image.name
            if linked.is_symlink() or linked.exists():
                linked.unlink()
            if copy:
                shutil.copy2(image, linked)
            else:
                linked.symlink_to(image.resolve())
            lists[target].append(str(linked.absolute()))
            counts[target]["images"] += 1
            counts[target]["negatives"] += not lines
            for line in lines:
                counts[target][TARGET[int(line.split()[0])]] += 1

    out.mkdir(parents=True, exist_ok=True)
    for split, items in lists.items():
        (out / f"{split}.txt").write_text("\n".join(items) + ("\n" if items else ""))
    data_yaml = out / "data.yaml"
    data_yaml.write_text(
        "# Generated by prepare_fire_dataset.py\n"
        f"path: {out.resolve()}\n"
        "train: train.txt\nval: val.txt\n"
        + ("test: test.txt\n" if lists["test"] else "")
        + "names:\n  0: fire\n  1: smoke\n"
    )
    manifest = {
        "source": str(source.resolve()),
        "source_classes": source_classes,
        "val_fraction": val_fraction if "val" not in splits else None,
        "counts": {s: dict(c) for s, c in counts.items()},
        "problems": problems[:200],
        "problem_count": len(problems),
        "skipped_images": skipped,
        "images": "copied" if copy else "symlinked to source",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--source-classes", required=True, help="Source class names in id order, e.g. smoke,fire")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--val-fraction", type=float, default=0.1)
    ap.add_argument("--copy", action="store_true", help="Copy images instead of symlinking them")
    args = ap.parse_args(argv)
    m = prepare(args.source, args.out, args.source_classes.split(","), args.val_fraction, args.copy)
    for split, c in m["counts"].items():
        print(f"{split:5s} {c}")
    if m["problem_count"]:
        print(
            f"{len(m['skipped_images'])} images skipped for {m['problem_count']} label problems (see manifest.json)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
