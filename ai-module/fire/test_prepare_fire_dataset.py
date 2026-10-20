import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import prepare_fire_dataset as prep


def make(root: Path, split: str, name: str, label: str | None):
    (root / split / "images").mkdir(parents=True, exist_ok=True)
    (root / split / "labels").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8)).save(root / split / "images" / f"{name}.jpg")
    if label is not None:
        (root / split / "labels" / f"{name}.txt").write_text(label)


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "dfire"
        self.out = Path(self.tmp.name) / "out"
        # D-Fire order: 0=smoke, 1=fire
        for i in range(40):
            make(self.src, "train", f"clip{i // 4}_frame_{i % 4}", "1 0.5 0.5 0.2 0.2\n0 0.3 0.3 0.1 0.1\n" if i % 2 else "")
        make(self.src, "test", "t1", "0 0.5 0.5 0.4 0.4\n")
        make(self.src, "test", "t2", "7 0.5 0.5 0.1 0.1\n1 1.4 0.5 0.1 0.1\n")

    def test_remaps_classes_and_writes_config(self):
        m = prep.prepare(self.src, self.out, ["smoke", "fire"])
        label = (self.out / "labels" / "test" / "t1.txt").read_text().split()
        self.assertEqual(label[0], "1")  # source smoke(0) -> target smoke(1)
        self.assertIn("names:\n  0: fire\n  1: smoke", (self.out / "data.yaml").read_text())
        self.assertEqual(m["counts"]["test"]["images"], 1)
        self.assertEqual(m["problem_count"], 2)  # unknown class 7, box outside 0-1
        self.assertEqual(m["skipped_images"], ["test/t2.jpg"])  # broken labels: excluded, not a negative
        # Each listed image has its label beside it under images/ -> labels/.
        for line in (self.out / "train.txt").read_text().split():
            self.assertTrue(Path(line.replace("/images/", "/labels/")).with_suffix(".txt").exists(), line)

    def test_val_split_keeps_clip_frames_together(self):
        prep.prepare(self.src, self.out, ["smoke", "fire"], val_fraction=0.3)
        val = {Path(p).stem for p in (self.out / "val.txt").read_text().split()}
        train = {Path(p).stem for p in (self.out / "train.txt").read_text().split()}
        self.assertTrue(val)
        self.assertFalse({prep.group_key(s) for s in val} & {prep.group_key(s) for s in train})

    def test_negatives_kept_and_counted(self):
        m = prep.prepare(self.src, self.out, ["smoke", "fire"])
        total_neg = sum(c.get("negatives", 0) for c in m["counts"].values())
        self.assertEqual(total_neg, 20)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["images"], "symlinked to source")

    def test_rejects_unknown_target_class(self):
        with self.assertRaises(ValueError):
            prep.prepare(self.src, self.out, ["smoke", "lava"])


if __name__ == "__main__":
    unittest.main()
