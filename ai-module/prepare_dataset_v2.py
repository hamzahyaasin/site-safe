#!/usr/bin/env python3
"""Prepare a leakage-safe, reviewable YOLO dataset-v2 split plan.

This command is deliberately non-destructive: it reads ``ppe_dataset`` and
writes manifests and a proposed split plan.  It never moves, copies, or edits
an image or label.  Conflicting annotations must be adjudicated before a v2
dataset is materialized.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import random
import re
from functools import lru_cache
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageOps
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

import audit_dataset


TEMPORAL_SOURCE = re.compile(
    r"^(?P<session>(?:video|vid|clip|sequence|seq|camera|cam|cctv)[-_]?[a-z0-9-]*?)[-_](?:frame[-_]?)?\d+$",
    re.IGNORECASE,
)
OUTPUT_FILES = (
    "manifest.csv",
    "groups.csv",
    "conflict_review.csv",
    "conflict_review.html",
    "split_plan.json",
)


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def infer_session_id(source_id: str) -> str:
    """Infer only high-confidence temporal families from exported filenames."""
    match = TEMPORAL_SOURCE.match(source_id)
    return match.group("session").rstrip("-_").casefold() if match else ""


def _bits_to_hex(bits: Iterable[bool]) -> str:
    value = 0
    count = 0
    for bit in bits:
        value = (value << 1) | int(bit)
        count += 1
    return f"{value:0{(count + 3) // 4}x}"


def _pixel_values(image: Image.Image) -> list[int]:
    flattened = getattr(image, "get_flattened_data", None)
    return list(flattened() if flattened else image.getdata())


def image_fingerprint(path: Path) -> dict[str, Any]:
    """Return compact fingerprints suitable for conservative duplicate review."""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("L")
        width, height = image.size
        average = round(sum(_pixel_values(image.resize((8, 8)))) / 64)

        def hashes(candidate: Image.Image) -> tuple[str, str]:
            dhash_image = candidate.resize((9, 8))
            pixels = _pixel_values(dhash_image)
            differences = (
                pixels[row * 9 + column] > pixels[row * 9 + column + 1]
                for row in range(8)
                for column in range(8)
            )
            ahash_pixels = _pixel_values(candidate.resize((8, 8)))
            ahash_average = sum(ahash_pixels) / len(ahash_pixels)
            return (
                _bits_to_hex(differences),
                _bits_to_hex(value >= ahash_average for value in ahash_pixels),
            )

        dhash, ahash = hashes(image)
        mirrored_dhash, mirrored_ahash = hashes(ImageOps.mirror(image))
    return {
        "width": width,
        "height": height,
        "dhash": dhash,
        "ahash": ahash,
        "mirrored_dhash": mirrored_dhash,
        "mirrored_ahash": mirrored_ahash,
        "mean_luma": average,
    }


def _visual_keys(record: dict[str, Any]) -> set[str]:
    """Keys intentionally require two hashes and similar mean luminance."""
    luma_bucket = int(record["mean_luma"]) // 4
    return {
        f"{record['dhash']}:{record['ahash']}:{luma_bucket}",
        f"{record['mirrored_dhash']}:{record['mirrored_ahash']}:{luma_bucket}",
    }


@lru_cache(maxsize=2048)
def _comparison_pixels(path_text: str, mirrored: bool = False) -> tuple[int, ...]:
    with Image.open(path_text) as opened:
        image = ImageOps.exif_transpose(opened).convert("L").resize((32, 32))
        if mirrored:
            image = ImageOps.mirror(image)
        return tuple(_pixel_values(image))


def visual_mse(left: Path, right: Path) -> float:
    """Return the best normalized low-resolution MSE, including a mirror check."""
    left_pixels = _comparison_pixels(str(left))
    right_pixels = _comparison_pixels(str(right))
    right_mirrored = _comparison_pixels(str(right), True)
    scale = len(left_pixels) * (255 ** 2)
    direct = sum((a - b) ** 2 for a, b in zip(left_pixels, right_pixels)) / scale
    mirrored = sum((a - b) ** 2 for a, b in zip(left_pixels, right_mirrored)) / scale
    return min(direct, mirrored)


def collect_records(root: Path) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    root = root.resolve()
    audit = audit_dataset.audit_dataset(root)
    if audit["blockers"]["annotation_or_pairing_errors"]:
        raise ValueError(
            "Cannot plan a split while annotation/pairing errors remain; "
            "run audit_dataset.py for details."
        )

    names = audit["class_names"]
    records: list[dict[str, Any]] = []
    for split in audit_dataset.SPLITS:
        images_dir = root / split / "images"
        labels_dir = root / split / "labels"
        for image_path in sorted(
            path for path in images_dir.iterdir()
            if path.is_file() and path.suffix.lower() in audit_dataset.IMAGE_EXTENSIONS
        ):
            label_path = labels_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                continue
            label = audit_dataset.parse_label_file(label_path, len(names))
            fingerprint = image_fingerprint(image_path)
            source_id = audit_dataset.canonical_source_id(image_path)
            records.append({
                "record_id": len(records),
                "current_split": split,
                "image": image_path,
                "label": label_path,
                "source_id": source_id,
                "session_id": infer_session_id(source_id),
                "image_sha256": audit_dataset.sha256_file(image_path),
                "label_signature": label["signature"],
                "background": label["background"],
                "class_counts": {
                    names[class_id]: count for class_id, count in label["counts"].items()
                },
                **fingerprint,
            })
    return names, records, audit


def connect_records(
    records: list[dict[str, Any]],
    visual_mse_threshold: float = 0.0015,
) -> tuple[list[dict[str, Any]], list[list[int]]]:
    dsu = DisjointSet(len(records))
    indexes: dict[tuple[str, str], int] = {}

    def connect(key_type: str, key: str, index: int) -> None:
        if not key:
            return
        compound = (key_type, key)
        previous = indexes.setdefault(compound, index)
        dsu.union(previous, index)

    for index, record in enumerate(records):
        connect("source", record["source_id"], index)
        connect("session", record["session_id"], index)
        connect("exact", record["image_sha256"], index)

    visual_indexes: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        candidates = {
            previous
            for visual_key in _visual_keys(record)
            for previous in visual_indexes[visual_key]
        }
        for previous in candidates:
            if records[previous]["image_sha256"] == record["image_sha256"]:
                continue
            if visual_mse(records[previous]["image"], record["image"]) <= visual_mse_threshold:
                dsu.union(previous, index)
        for visual_key in _visual_keys(record):
            visual_indexes[visual_key].append(index)

    members_by_root: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        members_by_root[dsu.find(index)].append(index)

    groups: list[dict[str, Any]] = []
    member_lists = sorted(members_by_root.values(), key=lambda values: min(values))
    for members in member_lists:
        stable_parts = sorted(records[index]["image_sha256"] for index in members)
        group_id = "grp_" + hashlib.sha256("\n".join(stable_parts).encode()).hexdigest()[:16]
        class_counts: Counter[str] = Counter()
        for index in members:
            class_counts.update(records[index]["class_counts"])
            records[index]["group_id"] = group_id
        groups.append({
            "group_id": group_id,
            "members": members,
            "image_count": len(members),
            "background_count": sum(int(records[index]["background"]) for index in members),
            "class_counts": dict(sorted(class_counts.items())),
            "current_splits": sorted({records[index]["current_split"] for index in members}),
            "source_ids": sorted({records[index]["source_id"] for index in members}),
            "session_ids": sorted({records[index]["session_id"] for index in members if records[index]["session_id"]}),
            "unique_exact_images": len({records[index]["image_sha256"] for index in members}),
        })
    return groups, member_lists


def find_exact_conflicts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_hash: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        by_hash[record["image_sha256"]].append(index)

    conflicts = []
    for image_hash, members in sorted(by_hash.items()):
        signatures = {records[index]["label_signature"] for index in members}
        if len(signatures) < 2:
            continue
        conflicts.append({
            "conflict_id": "conflict_" + image_hash[:16],
            "image_sha256": image_hash,
            "members": members,
            "label_signatures": sorted(signatures),
        })
    return conflicts


def propose_split(
    groups: list[dict[str, Any]],
    class_names: list[str],
    ratios: dict[str, float],
    seed: int,
    max_eval_group_fraction: float = 0.5,
) -> dict[str, Any]:
    split_names = tuple(ratios)
    total_images = sum(group["image_count"] for group in groups)
    total_classes: Counter[str] = Counter()
    for group in groups:
        total_classes.update(group["class_counts"])
    image_targets = {split: total_images * ratios[split] for split in split_names}
    class_targets = {
        split: {name: total_classes[name] * ratios[split] for name in class_names}
        for split in split_names
    }

    metrics = ["images", "backgrounds", *class_names]
    group_count = len(groups)
    split_count = len(split_names)
    assignment_count = group_count * split_count
    metric_rows = [(split, metric) for split in split_names for metric in metrics]
    variable_count = assignment_count + len(metric_rows) * 2

    objective = [0.0] * variable_count
    rng = random.Random(seed)
    for index in range(assignment_count):
        objective[index] = rng.random() * 1e-9
    metric_totals = {
        "images": total_images,
        "backgrounds": sum(group["background_count"] for group in groups),
        **total_classes,
    }
    for row_index, (_, metric) in enumerate(metric_rows):
        total = metric_totals[metric]
        weight = (5.0 if metric == "images" else 1.0) / max(total, 1)
        objective[assignment_count + row_index * 2] = weight
        objective[assignment_count + row_index * 2 + 1] = weight

    constraint_count = group_count + len(metric_rows)
    matrix = lil_matrix((constraint_count, variable_count), dtype=float)
    lower_constraints = [0.0] * constraint_count
    upper_constraints = [0.0] * constraint_count
    for group_index in range(group_count):
        for split_index in range(split_count):
            matrix[group_index, group_index * split_count + split_index] = 1.0
        lower_constraints[group_index] = 1.0
        upper_constraints[group_index] = 1.0

    def metric_value(group: dict[str, Any], metric: str) -> int:
        if metric == "images":
            return group["image_count"]
        if metric == "backgrounds":
            return group["background_count"]
        return group["class_counts"].get(metric, 0)

    for row_index, (split, metric) in enumerate(metric_rows):
        constraint_index = group_count + row_index
        split_index = split_names.index(split)
        for group_index, group in enumerate(groups):
            matrix[constraint_index, group_index * split_count + split_index] = metric_value(group, metric)
        positive_deviation = assignment_count + row_index * 2
        negative_deviation = positive_deviation + 1
        matrix[constraint_index, positive_deviation] = -1.0
        matrix[constraint_index, negative_deviation] = 1.0
        target = metric_totals[metric] * ratios[split]
        lower_constraints[constraint_index] = target
        upper_constraints[constraint_index] = target

    lower_bounds = [0.0] * variable_count
    upper_bounds = [float("inf")] * variable_count
    for group_index, group in enumerate(groups):
        for split_index, split in enumerate(split_names):
            variable = group_index * split_count + split_index
            upper_bounds[variable] = 1.0
            if (
                split != "train"
                and group["image_count"] > max(1.0, image_targets[split] * max_eval_group_fraction)
            ):
                upper_bounds[variable] = 0.0

    integrality = [1] * assignment_count + [0] * (variable_count - assignment_count)
    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(matrix.tocsr(), lower_constraints, upper_constraints),
        options={"time_limit": 30.0, "mip_rel_gap": 0.001},
    )
    if result.x is None:
        raise RuntimeError(f"Split optimization failed: {result.message}")

    assignments = {}
    assigned_images = {split: 0 for split in split_names}
    assigned_classes = {split: Counter() for split in split_names}
    assigned_backgrounds = {split: 0 for split in split_names}
    for group_index, group in enumerate(groups):
        split_index = max(
            range(split_count),
            key=lambda candidate: result.x[group_index * split_count + candidate],
        )
        split = split_names[split_index]
        assignments[group["group_id"]] = split
        assigned_images[split] += group["image_count"]
        assigned_backgrounds[split] += group["background_count"]
        assigned_classes[split].update(group["class_counts"])

    distributions = {}
    for split in split_names:
        distributions[split] = {
            "images": assigned_images[split],
            "target_images": round(image_targets[split], 2),
            "image_ratio": round(assigned_images[split] / max(total_images, 1), 6),
            "groups": sum(value == split for value in assignments.values()),
            "backgrounds": assigned_backgrounds[split],
            "class_counts": {name: assigned_classes[split][name] for name in class_names},
        }
    return {
        "seed": seed,
        "max_eval_group_fraction": max_eval_group_fraction,
        "optimizer": {
            "name": "scipy.optimize.milp",
            "feasible_solution": True,
            "optimality_proven": bool(result.success),
            "status": int(result.status),
            "message": result.message,
            "objective": float(result.fun),
        },
        "requested_ratios": ratios,
        "assignments": assignments,
        "distributions": distributions,
    }


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_annotation_preview(
    image_path: Path,
    label_path: Path,
    class_names: list[str],
    destination: Path,
) -> None:
    with Image.open(image_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    line_width = max(2, round(min(width, height) / 200))
    for row in label_path.read_text(encoding="utf-8").splitlines():
        fields = row.split()
        if len(fields) < 5:
            continue
        try:
            class_id = int(fields[0])
            coordinates = [float(value) for value in fields[1:]]
        except ValueError:
            continue
        if len(coordinates) == 4:
            center_x, center_y, box_width, box_height = coordinates
            points = [
                ((center_x - box_width / 2) * width, (center_y - box_height / 2) * height),
                ((center_x + box_width / 2) * width, (center_y + box_height / 2) * height),
            ]
            draw.rectangle(points, outline="#ff3b30", width=line_width)
            anchor = points[0]
        elif len(coordinates) >= 6 and len(coordinates) % 2 == 0:
            points = [
                (coordinates[index] * width, coordinates[index + 1] * height)
                for index in range(0, len(coordinates), 2)
            ]
            draw.line([*points, points[0]], fill="#ff3b30", width=line_width)
            anchor = points[0]
        else:
            continue
        name = class_names[class_id] if 0 <= class_id < len(class_names) else str(class_id)
        draw.text(anchor, name, fill="white", stroke_width=2, stroke_fill="black")
    image.thumbnail((600, 600))
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "JPEG", quality=88)


def write_outputs(
    output: Path,
    root: Path,
    names: list[str],
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    proposal: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    root = root.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    group_assignments = proposal["assignments"]
    conflict_by_member = {
        member: conflict["conflict_id"]
        for conflict in conflicts
        for member in conflict["members"]
    }
    review_path = output / "conflict_review.csv"
    existing_reviews: dict[tuple[str, str], tuple[str, str]] = {}
    if review_path.exists():
        with review_path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                key = (row.get("conflict_id", ""), row.get("record_id", ""))
                existing_reviews[key] = (
                    row.get("reviewer_decision", ""),
                    row.get("reviewer_notes", ""),
                )

    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "record_id", "group_id", "proposed_split", "current_split", "image", "label",
            "source_id", "session_id", "image_sha256", "label_signature", "background",
            "width", "height", "dhash", "ahash", "mirrored_dhash", "mirrored_ahash",
            "mean_luma", "conflict_id", *[f"class:{name}" for name in names],
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {
                key: record.get(key, "")
                for key in fields
                if not key.startswith("class:")
            }
            row.update({
                "proposed_split": group_assignments[record["group_id"]],
                "image": _relative(record["image"], root),
                "label": _relative(record["label"], root),
                "conflict_id": conflict_by_member.get(record["record_id"], ""),
            })
            row.update({f"class:{name}": record["class_counts"].get(name, 0) for name in names})
            writer.writerow(row)

    with (output / "groups.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "group_id", "proposed_split", "image_count", "background_count",
            "unique_exact_images", "current_splits", "source_ids", "session_ids",
            *[f"class:{name}" for name in names],
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for group in groups:
            row = {
                "group_id": group["group_id"],
                "proposed_split": group_assignments[group["group_id"]],
                "image_count": group["image_count"],
                "background_count": group["background_count"],
                "unique_exact_images": group["unique_exact_images"],
                "current_splits": "|".join(group["current_splits"]),
                "source_ids": "|".join(group["source_ids"]),
                "session_ids": "|".join(group["session_ids"]),
            }
            row.update({f"class:{name}": group["class_counts"].get(name, 0) for name in names})
            writer.writerow(row)

    with review_path.open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "conflict_id", "status", "record_id", "current_split", "image", "label",
            "label_signature", "class_counts", "reviewer_decision", "reviewer_notes",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for conflict in conflicts:
            for member in conflict["members"]:
                record = records[member]
                prior_decision, prior_notes = existing_reviews.get(
                    (conflict["conflict_id"], str(member)),
                    ("", ""),
                )
                writer.writerow({
                    "conflict_id": conflict["conflict_id"],
                    "status": "unresolved",
                    "record_id": member,
                    "current_split": record["current_split"],
                    "image": _relative(record["image"], root),
                    "label": _relative(record["label"], root),
                    "label_signature": record["label_signature"],
                    "class_counts": json.dumps(record["class_counts"], sort_keys=True),
                    "reviewer_decision": prior_decision,
                    "reviewer_notes": prior_notes,
                })

    html_rows = []
    preview_dir = output / "conflict_previews"
    for conflict in conflicts:
        cards = []
        for member in conflict["members"]:
            record = records[member]
            preview_path = preview_dir / f"{conflict['conflict_id']}_{member}.jpg"
            write_annotation_preview(record["image"], record["label"], names, preview_path)
            image_link = os.path.relpath(preview_path, output).replace(os.sep, "/")
            label_text = record["label"].read_text(encoding="utf-8").strip() or "(background)"
            cards.append(
                '<figure><img loading="lazy" src="{}" alt="{}"><figcaption>'
                '<strong>{}</strong><br><code>{}</code><pre>{}</pre></figcaption></figure>'.format(
                    html.escape(image_link, quote=True),
                    html.escape(conflict["conflict_id"], quote=True),
                    html.escape(record["current_split"]),
                    html.escape(_relative(record["image"], root)),
                    html.escape(label_text),
                )
            )
        html_rows.append(
            f'<section><h2>{html.escape(conflict["conflict_id"])}</h2>'
            f'<div class="cards">{"".join(cards)}</div></section>'
        )
    (output / "conflict_review.html").write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>Site-Safe label conflicts</title>"
        "<style>body{font:14px system-ui;max-width:1400px;margin:2rem auto;padding:0 1rem}"
        "section{border-top:1px solid #ccc;margin-top:2rem}.cards{display:flex;gap:1rem;flex-wrap:wrap}"
        "figure{margin:0;width:300px}img{width:300px;height:300px;object-fit:contain;background:#111}"
        "pre{white-space:pre-wrap;font-size:11px;max-height:180px;overflow:auto}</style>"
        f"<h1>Unresolved exact-image label conflicts ({len(conflicts)})</h1>"
        "<p>Compare each identical image's annotations. Record the canonical decision in "
        "<code>conflict_review.csv</code>; do not train on unresolved conflicts.</p>"
        + "".join(html_rows),
        encoding="utf-8",
    )

    multi_hash_visual_groups = sum(
        group["unique_exact_images"] > 1 and group["image_count"] > 1 for group in groups
    )
    cross_split_groups = sum(len(group["current_splits"]) > 1 for group in groups)
    plan = {
        "schema_version": 1,
        "dataset_root": str(root),
        "class_names": names,
        "record_count": len(records),
        "group_count": len(groups),
        "unresolved_exact_conflicts": len(conflicts),
        "connected_groups_currently_crossing_splits": cross_split_groups,
        "multi_hash_source_or_visual_groups": multi_hash_visual_groups,
        "ready_to_materialize": len(conflicts) == 0 and audit["strict_pass"],
        "readiness_notes": [
            "Resolve every row in conflict_review.csv before materialization.",
            "Add explicit site/camera/session/timestamp metadata; filename inference is provisional.",
            "Recover pre-augmentation source assets and split them before augmentation.",
            "Reserve an untouched target-camera/site/time test set before model selection.",
        ],
        **proposal,
    }
    (output / "split_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


def parse_ratios(value: str) -> dict[str, float]:
    parts = [float(part) for part in value.split(",")]
    if len(parts) != 3 or any(part <= 0 for part in parts):
        raise argparse.ArgumentTypeError("ratios must be three positive values: train,valid,test")
    total = sum(parts)
    return {
        "train": parts[0] / total,
        "valid": parts[1] / total,
        "test": parts[2] / total,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=audit_dataset.module_root() / "ppe_dataset")
    parser.add_argument("--output", type=Path, default=audit_dataset.module_root() / "dataset_v2_plan")
    parser.add_argument("--ratios", type=parse_ratios, default=parse_ratios("0.70,0.15,0.15"))
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument(
        "--visual-mse",
        type=float,
        default=0.0015,
        help="Maximum normalized 32x32 MSE for conservative visual grouping.",
    )
    parser.add_argument(
        "--max-eval-group-fraction",
        type=float,
        default=0.5,
        help="Prevent one connected group from exceeding this share of valid/test.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0.0 <= args.visual_mse <= 1.0:
        raise SystemExit("--visual-mse must be between 0 and 1")
    if not 0.0 < args.max_eval_group_fraction <= 1.0:
        raise SystemExit("--max-eval-group-fraction must be greater than 0 and at most 1")
    names, records, audit = collect_records(args.dataset)
    groups, _ = connect_records(records, args.visual_mse)
    conflicts = find_exact_conflicts(records)
    proposal = propose_split(
        groups,
        names,
        args.ratios,
        args.seed,
        args.max_eval_group_fraction,
    )
    write_outputs(args.output.resolve(), args.dataset.resolve(), names, records, groups, conflicts, proposal, audit)
    print("SITE-SAFE DATASET V2 PREPARATION")
    print(f"Records: {len(records)}")
    print(f"Leakage-safe groups: {len(groups)}")
    print(f"Unresolved exact-image label conflicts: {len(conflicts)}")
    for split, distribution in proposal["distributions"].items():
        print(
            f"[{split}] images={distribution['images']} "
            f"ratio={distribution['image_ratio']:.3f} groups={distribution['groups']}"
        )
    print(f"Artifacts: {args.output.resolve()}")
    print("No dataset files were changed.")
    return 2 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
