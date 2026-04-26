#!/usr/bin/env python3
"""
Verify PPE YOLO dataset layout: counts, label/image pairing, random preview with boxes.
Run from anywhere: python verify_dataset.py (uses ai-module/ as root).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import cv2
import yaml

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def module_root() -> Path:
    return Path(__file__).resolve().parent


def dataset_root() -> Path:
    return module_root() / "ppe_dataset"


def list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            out.append(p)
    return out


def list_labels(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".txt")


def load_class_names(data_yaml: Path) -> list[str]:
    with data_yaml.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    names = cfg.get("names") or []
    if isinstance(names, dict):
        names = [names[i] for i in sorted(names)]
    return [str(x) for x in names]


def yolo_line_to_box(line: str, w: int, h: int) -> tuple[int, int, int, int, int] | None:
    parts = line.strip().split()
    if len(parts) < 5:
        return None
    cls_id = int(parts[0])
    xc, yc, bw, bh = map(float, parts[1:5])
    x1 = int((xc - bw / 2) * w)
    y1 = int((yc - bh / 2) * h)
    x2 = int((xc + bw / 2) * w)
    y2 = int((yc + bh / 2) * h)
    x1, x2 = max(0, x1), min(w - 1, x2)
    y1, y2 = max(0, y1), min(h - 1, y2)
    return x1, y1, x2, y2, cls_id


def draw_labels_on_image(image_path: Path, label_path: Path, names: list[str]) -> Path:
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    h, w = img.shape[:2]
    if label_path.is_file():
        for line in label_path.read_text(encoding="utf-8").splitlines():
            box = yolo_line_to_box(line, w, h)
            if box is None:
                continue
            x1, y1, x2, y2, cls_id = box
            color = (0, 200, 0)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            label = names[cls_id] if 0 <= cls_id < len(names) else f"id={cls_id}"
            cv2.putText(
                img,
                label,
                (x1, max(y1 - 4, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )
    out_path = module_root() / "verify_preview.jpg"
    cv2.imwrite(str(out_path), img)
    return out_path


def analyze_split(split: str, images_dir: Path, labels_dir: Path) -> dict:
    images = list_images(images_dir)
    labels = list_labels(labels_dir)
    stems_img = {p.stem for p in images}
    stems_lbl = {p.stem for p in labels}
    missing_label = sorted(stems_img - stems_lbl)
    missing_image = sorted(stems_lbl - stems_img)
    return {
        "split": split,
        "image_count": len(images),
        "label_count": len(labels),
        "missing_label_for_image": missing_label,
        "missing_image_for_label": missing_image,
        "images": images,
        "labels": labels,
    }


def main() -> None:
    root = dataset_root()
    data_yaml = root / "data.yaml"
    if not data_yaml.is_file():
        print(f"ERROR: Missing {data_yaml}", file=sys.stderr)
        sys.exit(1)

    names = load_class_names(data_yaml)
    splits = [
        ("train", root / "train" / "images", root / "train" / "labels"),
        ("valid", root / "valid" / "images", root / "valid" / "labels"),
        ("test", root / "test" / "images", root / "test" / "labels"),
    ]

    reports: list[dict] = []
    all_image_paths: list[Path] = []
    for split, img_dir, lbl_dir in splits:
        r = analyze_split(split, img_dir, lbl_dir)
        reports.append(r)
        all_image_paths.extend(r["images"])

    print("=" * 72)
    print("SITE-SAFE PPE DATASET VERIFICATION")
    print("=" * 72)
    print(f"Dataset root: {root}")
    print(f"Classes ({len(names)}): {names}")
    print()

    total_images = 0
    total_labels = 0
    issues = 0
    for r in reports:
        total_images += r["image_count"]
        total_labels += r["label_count"]
        ok = not r["missing_label_for_image"] and not r["missing_image_for_label"]
        match_note = "OK" if r["image_count"] == r["label_count"] and ok else "CHECK"
        if r["image_count"] != r["label_count"] or not ok:
            issues += 1
        print(f"[{r['split']}] images={r['image_count']} labels={r['label_count']}  ({match_note})")
        if r["missing_label_for_image"]:
            miss = r["missing_label_for_image"][:10]
            extra = len(r["missing_label_for_image"]) - len(miss)
            print(f"  Images without label file ({len(r['missing_label_for_image'])}): {miss}" + (f" … (+{extra} more)" if extra > 0 else ""))
        if r["missing_image_for_label"]:
            miss = r["missing_image_for_label"][:10]
            extra = len(r["missing_image_for_label"]) - len(miss)
            print(f"  Labels without image ({len(r['missing_image_for_label'])}): {miss}" + (f" … (+{extra} more)" if extra > 0 else ""))
        print()

    print("-" * 72)
    print(f"TOTAL images:  {total_images}")
    print(f"TOTAL labels:  {total_labels}")
    print(f"Splits with pairing/count issues: {issues}")
    print("-" * 72)

    if not all_image_paths:
        print("No images found — place images under train/valid/test .../images/ and re-run.")
        return

    sample = random.choice(all_image_paths)
    label_path = sample.parent.parent / "labels" / f"{sample.stem}.txt"
    try:
        out_path = draw_labels_on_image(sample, label_path, names)
        print(f"Random sample image: {sample}")
        print(f"Label file:          {label_path} ({'found' if label_path.is_file() else 'MISSING'})")
        print(f"Preview written to:  {out_path}")
        print("(Open verify_preview.jpg to visually confirm boxes match objects.)")
    except Exception as exc:
        print(f"Preview failed: {exc}", file=sys.stderr)

    print("=" * 72)
    print("SUMMARY: ", end="")
    if total_images == 0:
        print("No images detected.")
    elif issues == 0 and total_images == total_labels:
        print("Counts match and every split has 1:1 image/label stems.")
    else:
        print("Review warnings above (mismatched counts or missing pairs).")
    print("=" * 72)


if __name__ == "__main__":
    main()
