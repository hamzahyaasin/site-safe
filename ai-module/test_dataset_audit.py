from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import audit_dataset
import verify_dataset


class DatasetAuditTests(unittest.TestCase):
    def make_dataset(self, root: Path) -> None:
        (root / "data.yaml").write_text("nc: 1\nnames: [helmet]\n", encoding="utf-8")
        for split in audit_dataset.SPLITS:
            (root / split / "images").mkdir(parents=True)
            (root / split / "labels").mkdir(parents=True)

    def add_pair(self, root: Path, split: str, name: str, image: bytes, label: str) -> None:
        (root / split / "images" / f"{name}.jpg").write_bytes(image)
        (root / split / "labels" / f"{name}.txt").write_text(label, encoding="utf-8")

    def test_canonical_source_id_removes_roboflow_export_suffix(self):
        path = Path("worker_01_jpg.rf.0123456789abcdef0123456789abcdef.jpg")
        self.assertEqual(audit_dataset.canonical_source_id(path), "worker_01")

    def test_empty_label_is_a_valid_background(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_dataset(root)
            self.add_pair(root, "train", "background", b"background", "")
            report = audit_dataset.audit_dataset(root)
            self.assertEqual(report["splits"]["train"]["background_images"], 1)
            self.assertEqual(report["blockers"]["annotation_or_pairing_errors"], 0)

    def test_exact_cross_split_duplicate_with_different_labels_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_dataset(root)
            image = b"same-image-bytes"
            self.add_pair(
                root,
                "train",
                "worker_jpg.rf.11111111111111111111111111111111",
                image,
                "0 0.5 0.5 0.2 0.2\n",
            )
            self.add_pair(
                root,
                "valid",
                "worker_jpg.rf.22222222222222222222222222222222",
                image,
                "",
            )
            report = audit_dataset.audit_dataset(root)
            self.assertEqual(report["blockers"]["cross_split_source_groups"], 1)
            self.assertEqual(report["blockers"]["cross_split_exact_duplicate_groups"], 1)
            self.assertEqual(report["blockers"]["conflicting_exact_duplicate_groups"], 1)
            self.assertFalse(report["strict_pass"])

    def test_polygon_preview_uses_polygon_bounds(self):
        box = verify_dataset.yolo_line_to_box(
            "0 0.1 0.2 0.4 0.2 0.4 0.8 0.1 0.8",
            100,
            200,
        )
        self.assertEqual(box, (10, 40, 40, 160, 0))


if __name__ == "__main__":
    unittest.main()
