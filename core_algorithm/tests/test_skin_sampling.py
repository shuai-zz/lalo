from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from lalo_core.skin_sampling import _UV, sample_skin_sheet


class SkinSamplingTests(unittest.TestCase):
    def test_samples_two_panel_sheet_into_complete_skin_faces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            _write_source(source)

            artifacts = sample_skin_sheet(source, Path(directory) / "result")
            skin = Image.open(artifacts.skin).convert("RGBA")

            self.assertEqual(skin.size, (64, 64))
            with Image.open(artifacts.review_sheet) as review:
                self.assertEqual(review.size, (900, 620))
            for faces in _UV.values():
                for rectangle in faces.values():
                    self.assertEqual(skin.crop(rectangle).getextrema()[3], (255, 255))
            self.assertNotEqual(
                skin.crop(_UV["torso"]["front"]).tobytes(),
                skin.crop(_UV["torso"]["back"]).tobytes(),
            )

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            _write_source(source)

            first = sample_skin_sheet(source, root / "first")
            second = sample_skin_sheet(source, root / "second")

            self.assertEqual(first.skin.read_bytes(), second.skin.read_bytes())
            self.assertEqual(
                first.review_sheet.read_bytes(), second.review_sheet.read_bytes()
            )

    def test_refuses_existing_output_and_invalid_panel_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            _write_source(source)
            existing = root / "existing"
            existing.mkdir()

            with self.assertRaisesRegex(FileExistsError, "already exists"):
                sample_skin_sheet(source, existing)

            Image.new("RGB", (100, 100), "white").save(root / "blank.png")
            with self.assertRaisesRegex(ValueError, "exactly two"):
                sample_skin_sheet(root / "blank.png", root / "invalid")


def _write_source(path: Path) -> None:
    image = Image.new("RGB", (360, 200), "white")
    draw = ImageDraw.Draw(image)
    for origin, back in ((30, False), (220, True)):
        # 32 units high at five pixels per unit. All canonical parts touch.
        draw.rectangle((origin + 20, 10, origin + 59, 49), fill="#181818")
        if not back:
            draw.rectangle((origin + 25, 25, origin + 54, 49), fill="#e7a474")
            draw.rectangle((origin + 28, 30, origin + 51, 36), fill="#202020")
        draw.rectangle((origin + 20, 50, origin + 59, 109), fill="#d99b00")
        draw.rectangle((origin, 50, origin + 19, 109), fill="#d99b00")
        draw.rectangle((origin + 60, 50, origin + 79, 109), fill="#d99b00")
        if not back:
            draw.rectangle((origin + 35, 50, origin + 44, 109), fill="#f4f4f4")
        draw.rectangle((origin + 20, 110, origin + 39, 169), fill="#03434b")
        draw.rectangle((origin + 40, 110, origin + 59, 169), fill="#03434b")
    image.save(path)


if __name__ == "__main__":
    unittest.main()
