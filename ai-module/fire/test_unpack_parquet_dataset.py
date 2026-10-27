import io
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

import unpack_parquet_dataset as unpack


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buf, format="JPEG")
    return buf.getvalue()


class UnpackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        rows = {
            "image": [{"bytes": jpeg(), "path": None}] * 3 + [{"bytes": jpeg(), "path": None}],
            "label": ["1 0.5 0.5 0.2 0.2\n0 0.3 0.3 0.1 0.1", "", "0 0.5 0.5 0.4 0.4", "1 0.1 0.1 0.1 0.1"],
            "filename": ["AoF1.jpg", "AoF2.jpg", "WEB3.jpg", "../escape.jpg"],
        }
        (self.root / "pq").mkdir()
        pq.write_table(pa.table(rows), self.root / "pq" / "train-00000-of-00001.parquet")

    def test_writes_yolo_layout_and_counts(self):
        stats = unpack.unpack(self.root / "pq", self.root / "out", ["smoke", "fire"])
        self.assertEqual(stats["train"], {"images": 4, "fire": 2, "smoke": 2, "empty": 1})
        self.assertTrue((self.root / "out/train/images/AoF1.jpg").is_file())
        self.assertEqual((self.root / "out/train/labels/AoF2.txt").read_text(), "")
        self.assertEqual((self.root / "out/train/labels/WEB3.txt").read_text(), "0 0.5 0.5 0.4 0.4\n")

    def test_path_in_file_name_is_reduced_to_its_base_name(self):
        unpack.unpack(self.root / "pq", self.root / "out", ["smoke", "fire"])
        self.assertTrue((self.root / "out/train/images/escape.jpg").is_file())
        self.assertFalse((self.root / "out/train/escape.jpg").exists())
        self.assertFalse((self.root / "escape.jpg").exists())

    def test_cli_writes_count_report(self):
        unpack.main(["--parquet", str(self.root / "pq"), "--out", str(self.root / "out"), "--classes", "smoke,fire"])
        report = json.loads((self.root / "out/unpack_counts.json").read_text())
        self.assertEqual(report["total"]["images"], 4)


if __name__ == "__main__":
    unittest.main()
