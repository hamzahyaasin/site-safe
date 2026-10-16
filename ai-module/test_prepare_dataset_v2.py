from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

import audit_dataset
import prepare_dataset_v2


class DatasetV2PreparationTests(unittest.TestCase):
    def make_dataset(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "data.yaml").write_text("nc: 2\nnames: [helmet, vest]\n", encoding="utf-8")
        for split in audit_dataset.SPLITS:
            (root / split / "images").mkdir(parents=True)
            (root / split / "labels").mkdir(parents=True)

    def add_pair(
        self,
        root: Path,
        split: str,
        name: str,
        pixels: list[int],
        label: str,
        mirror: bool = False,
    ) -> None:
        image = Image.new("L", (4, 2))
        image.putdata(pixels)
        if mirror:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        image.convert("RGB").save(root / split / "images" / f"{name}.png")
        (root / split / "labels" / f"{name}.txt").write_text(label, encoding="utf-8")

    def test_session_inference_is_conservative(self):
        self.assertEqual(prepare_dataset_v2.infer_session_id("video1_30"), "video1")
        self.assertEqual(prepare_dataset_v2.infer_session_id("image_30"), "")
        self.assertEqual(prepare_dataset_v2.infer_session_id("ppe_30"), "")

    def test_mirrored_visual_siblings_stay_in_one_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_dataset(root)
            pixels = [0, 20, 80, 255, 10, 50, 100, 220]
            self.add_pair(root, "train", "worker_a", pixels, "0 0.5 0.5 0.2 0.2\n")
            self.add_pair(root, "valid", "worker_b", pixels, "0 0.5 0.5 0.2 0.2\n", mirror=True)
            _, records, _ = prepare_dataset_v2.collect_records(root)
            groups, _ = prepare_dataset_v2.connect_records(records)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["current_splits"], ["train", "valid"])

    def test_outputs_flag_conflicts_and_never_modify_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "dataset"
            output = Path(directory) / "plan"
            self.make_dataset(root)
            pixels = [0, 20, 80, 255, 10, 50, 100, 220]
            name1 = "worker_jpg.rf.11111111111111111111111111111111"
            name2 = "worker_jpg.rf.22222222222222222222222222222222"
            self.add_pair(root, "train", name1, pixels, "0 0.5 0.5 0.2 0.2\n")
            self.add_pair(root, "test", name2, pixels, "1 0.5 0.5 0.2 0.2\n")
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()
            }

            names, records, audit = prepare_dataset_v2.collect_records(root)
            groups, _ = prepare_dataset_v2.connect_records(records)
            conflicts = prepare_dataset_v2.find_exact_conflicts(records)
            proposal = prepare_dataset_v2.propose_split(
                groups,
                names,
                {"train": 0.7, "valid": 0.15, "test": 0.15},
                seed=7,
            )
            prepare_dataset_v2.write_outputs(
                output, root, names, records, groups, conflicts, proposal, audit
            )

            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertEqual(len(conflicts), 1)
            plan = json.loads((output / "split_plan.json").read_text(encoding="utf-8"))
            self.assertFalse(plan["ready_to_materialize"])
            with (output / "manifest.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual({row["proposed_split"] for row in rows}, {rows[0]["proposed_split"]})
            self.assertTrue(all(row["conflict_id"] for row in rows))

            review_path = output / "conflict_review.csv"
            with review_path.open(newline="", encoding="utf-8") as stream:
                review_rows = list(csv.DictReader(stream))
            review_rows[0]["reviewer_decision"] = "canonical"
            with review_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=review_rows[0].keys())
                writer.writeheader()
                writer.writerows(review_rows)
            prepare_dataset_v2.write_outputs(
                output, root, names, records, groups, conflicts, proposal, audit
            )
            with review_path.open(newline="", encoding="utf-8") as stream:
                preserved = list(csv.DictReader(stream))
            self.assertEqual(preserved[0]["reviewer_decision"], "canonical")


if __name__ == "__main__":
    unittest.main()
