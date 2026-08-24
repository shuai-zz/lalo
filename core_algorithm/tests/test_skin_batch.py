from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from lalo_core.skin_batch import evaluate_skin_sheets


class SkinBatchTests(unittest.TestCase):
    def test_generates_stable_manifest_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            _write_sheet(sources / "zeta.png", accent="#b02020")
            _write_sheet(sources / "alpha.png", accent="#2030b0")

            manifest_path = evaluate_skin_sheets(sources, root / "evaluation", scale=2)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["scale"], 2)
            self.assertEqual(
                [sample["name"] for sample in manifest["samples"]],
                ["alpha", "zeta"],
            )
            for sample in manifest["samples"]:
                self.assertTrue((manifest_path.parent / sample["skin"]).is_file())
                self.assertTrue((manifest_path.parent / sample["review_sheet"]).is_file())
                self.assertTrue((manifest_path.parent / sample["glb"]).is_file())

    def test_rejects_invalid_input_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root / "empty"
            empty.mkdir()
            output = root / "evaluation"

            with self.assertRaisesRegex(ValueError, "at least one"):
                evaluate_skin_sheets(empty, output)
            self.assertFalse(output.exists())

            _write_sheet(empty / "sample.png", accent="#b02020")
            output.mkdir()
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                evaluate_skin_sheets(empty, output)

    def test_failed_sample_does_not_publish_partial_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            _write_sheet(sources / "good.png", accent="#b02020")
            Image.new("RGB", (100, 100), "white").save(sources / "invalid.png")
            output = root / "evaluation"

            with self.assertRaisesRegex(ValueError, "two or four"):
                evaluate_skin_sheets(sources, output)
            self.assertFalse(output.exists())


def _write_sheet(path: Path, *, accent: str) -> None:
    image = Image.new("RGB", (360, 200), "white")
    draw = ImageDraw.Draw(image)
    for origin, back in ((30, False), (220, True)):
        draw.rectangle((origin + 20, 10, origin + 59, 49), fill="#181818")
        if not back:
            draw.rectangle((origin + 25, 25, origin + 54, 49), fill="#e7a474")
        draw.rectangle((origin, 50, origin + 79, 109), fill=accent)
        draw.rectangle((origin + 20, 110, origin + 59, 169), fill="#03434b")
    image.save(path)


if __name__ == "__main__":
    unittest.main()
