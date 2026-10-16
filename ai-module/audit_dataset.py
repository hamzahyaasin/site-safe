#!/usr/bin/env python3
"""Audit a YOLO dataset for split leakage and annotation integrity.

The audit is read-only.  By default it prints findings and exits successfully
so it can be used on a dataset that is still being repaired.  ``--strict``
returns a non-zero status when training/evaluation blockers are present.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import yaml


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SPLITS = ("train", "valid", "test")
ROBOFLOW_SUFFIX = re.compile(r"\.rf\.[0-9a-f]{16,}$", re.IGNORECASE)
ENCODED_EXTENSION = re.compile(
    r"_(?:jpg|jpeg|png|bmp|webp|tif|tiff)$",
    re.IGNORECASE,
)


def module_root() -> Path:
    return Path(__file__).resolve().parent


def canonical_source_id(path: Path) -> str:
    """Best available pre-export identity for a Roboflow-style filename.

    A durable dataset should carry an explicit source/video/session id.  Until
    then, stripping the export hash and encoded extension catches augmented or
    duplicated copies of the same named source asset.
    """
    stem = ROBOFLOW_SUFFIX.sub("", path.stem)
    stem = ENCODED_EXTENSION.sub("", stem)
    return stem.casefold()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_class_names(data_yaml: Path) -> list[str]:
    config = yaml.safe_load(data_yaml.read_text(encoding="utf-8")) or {}
    names = config.get("names", [])
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names, key=lambda value: int(value))]
    names = [str(name) for name in names]
    declared = config.get("nc")
    if declared is not None and int(declared) != len(names):
        raise ValueError(f"data.yaml declares nc={declared} but defines {len(names)} names")
    if not names:
        raise ValueError("data.yaml does not define any class names")
    return names


def parse_label_file(path: Path, class_count: int) -> dict[str, Any]:
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors: list[str] = []
    counts: Counter[int] = Counter()
    formats: Counter[str] = Counter()

    for line_number, row in enumerate(rows, start=1):
        fields = row.split()
        try:
            class_id = int(fields[0])
            coordinates = [float(value) for value in fields[1:]]
        except (IndexError, ValueError):
            errors.append(f"{path}:{line_number}: cannot parse")
            continue

        is_box = len(coordinates) == 4
        is_polygon = len(coordinates) >= 6 and len(coordinates) % 2 == 0
        if class_id not in range(class_count):
            errors.append(f"{path}:{line_number}: class id {class_id} is out of range")
            continue
        if not (is_box or is_polygon):
            errors.append(f"{path}:{line_number}: expected 4 box coordinates or polygon pairs")
            continue
        if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in coordinates):
            errors.append(f"{path}:{line_number}: coordinate outside [0, 1] or non-finite")
            continue
        if is_box and (coordinates[2] <= 0.0 or coordinates[3] <= 0.0):
            errors.append(f"{path}:{line_number}: box width and height must be positive")
            continue

        counts[class_id] += 1
        formats["box" if is_box else "polygon"] += 1

    normalized = "\n".join(sorted(rows)).encode("utf-8")
    return {
        "background": not rows,
        "counts": counts,
        "errors": errors,
        "formats": formats,
        "signature": hashlib.sha256(normalized).hexdigest(),
    }


def _public_record(record: dict[str, Any], root: Path) -> dict[str, str]:
    return {
        "split": record["split"],
        "image": record["image"].relative_to(root).as_posix(),
        "label": record["label"].relative_to(root).as_posix(),
        "source_id": record["source_id"],
    }


def audit_dataset(root: Path) -> dict[str, Any]:
    root = root.resolve()
    names = load_class_names(root / "data.yaml")
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    split_reports: dict[str, Any] = {}
    all_errors: list[str] = []

    for split in SPLITS:
        images_dir = root / split / "images"
        labels_dir = root / split / "labels"
        images = sorted(
            path for path in images_dir.glob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        labels = sorted(labels_dir.glob("*.txt"))
        images_by_stem = {path.stem: path for path in images}
        labels_by_stem = {path.stem: path for path in labels}
        missing_labels = sorted(set(images_by_stem) - set(labels_by_stem))
        orphan_labels = sorted(set(labels_by_stem) - set(images_by_stem))
        all_errors.extend(f"{split}: image without label: {stem}" for stem in missing_labels)
        all_errors.extend(f"{split}: label without image: {stem}" for stem in orphan_labels)

        class_counts: Counter[int] = Counter()
        format_counts: Counter[str] = Counter()
        background_images = 0
        invalid_rows = 0

        for stem in sorted(set(images_by_stem) & set(labels_by_stem)):
            image_path = images_by_stem[stem]
            label_path = labels_by_stem[stem]
            label = parse_label_file(label_path, len(names))
            all_errors.extend(label["errors"])
            invalid_rows += len(label["errors"])
            background_images += int(label["background"])
            class_counts.update(label["counts"])
            format_counts.update(label["formats"])
            record = {
                "split": split,
                "image": image_path,
                "label": label_path,
                "image_hash": sha256_file(image_path),
                "label_signature": label["signature"],
                "source_id": canonical_source_id(image_path),
            }
            by_hash[record["image_hash"]].append(record)
            by_source[record["source_id"]].append(record)

        split_reports[split] = {
            "images": len(images),
            "labels": len(labels),
            "background_images": background_images,
            "invalid_rows": invalid_rows,
            "missing_labels": len(missing_labels),
            "orphan_labels": len(orphan_labels),
            "annotation_formats": dict(format_counts),
            "class_counts": {name: class_counts[index] for index, name in enumerate(names)},
        }

    exact_duplicate_groups = [records for records in by_hash.values() if len(records) > 1]
    cross_split_exact = [
        records for records in exact_duplicate_groups
        if len({record["split"] for record in records}) > 1
    ]
    conflicting_exact = [
        records for records in exact_duplicate_groups
        if len({record["label_signature"] for record in records}) > 1
    ]
    cross_split_sources = [
        records for records in by_source.values()
        if len({record["split"] for record in records}) > 1
    ]

    blockers = {
        "annotation_or_pairing_errors": len(all_errors),
        "cross_split_source_groups": len(cross_split_sources),
        "cross_split_exact_duplicate_groups": len(cross_split_exact),
        "conflicting_exact_duplicate_groups": len(conflicting_exact),
    }
    return {
        "dataset_root": str(root),
        "class_names": names,
        "splits": split_reports,
        "blockers": blockers,
        "examples": {
            "errors": all_errors[:10],
            "cross_split_sources": [
                [_public_record(record, root) for record in records[:5]]
                for records in cross_split_sources[:10]
            ],
            "cross_split_exact_duplicates": [
                [_public_record(record, root) for record in records]
                for records in cross_split_exact[:10]
            ],
            "conflicting_exact_duplicates": [
                [_public_record(record, root) for record in records]
                for records in conflicting_exact[:10]
            ],
        },
        "strict_pass": not any(blockers.values()),
    }


def print_report(report: dict[str, Any]) -> None:
    print("SITE-SAFE DATASET QUALITY AUDIT")
    print(f"Dataset: {report['dataset_root']}")
    print(f"Classes: {len(report['class_names'])}")
    for split in SPLITS:
        item = report["splits"][split]
        print(
            f"[{split}] images={item['images']} labels={item['labels']} "
            f"backgrounds={item['background_images']} invalid_rows={item['invalid_rows']}"
        )
    print("Blockers:")
    for name, count in report["blockers"].items():
        print(f"  {name}: {count}")
    print(f"Strict result: {'PASS' if report['strict_pass'] else 'FAIL'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=module_root() / "ppe_dataset",
        help="Dataset root containing data.yaml and train/valid/test directories.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 when blockers are found.")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_dataset(args.dataset)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 1 if args.strict and not report["strict_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
