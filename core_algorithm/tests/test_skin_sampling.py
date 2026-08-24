from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from lalo_core.skin_sampling import _UV, _extend_horizontal_background, sample_skin_sheet


class SkinSamplingTests(unittest.TestCase):
    def test_extends_only_external_side_view_background(self) -> None:
        source = Image.new("RGB", (5, 1), "white")
        source.putpixel((1, 0), (200, 0, 0))
        source.putpixel((3, 0), (0, 0, 200))

        extended = _extend_horizontal_background(source, (255, 255, 255))

        self.assertEqual(extended.getpixel((0, 0)), (200, 0, 0))
        self.assertEqual(extended.getpixel((2, 0)), (255, 255, 255))
        self.assertEqual(extended.getpixel((4, 0)), (0, 0, 200))

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

    def test_protruding_chin_is_kept_out_of_torso(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            _write_source(source, protruding_chin=True)

            artifacts = sample_skin_sheet(source, root / "result")
            with Image.open(artifacts.skin) as stored_skin:
                skin = stored_skin.convert("RGB")
            torso = skin.crop(_UV["torso"]["front"])
            skin_color = (231, 164, 116)
            self.assertFalse(
                any(
                    torso.getpixel((x, y)) == skin_color
                    for y in range(torso.height)
                    for x in range(torso.width)
                )
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

    def test_four_x_skin_preserves_more_source_detail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            _write_four_view_source(source)

            artifacts = sample_skin_sheet(source, root / "result", scale=4)
            with Image.open(artifacts.skin) as skin:
                self.assertEqual(skin.size, (256, 256))
                front = tuple(value * 4 for value in _UV["torso"]["front"])
                self.assertEqual(skin.crop(front).size, (32, 48))

    def test_rejects_invalid_scale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            _write_source(source)
            for scale in (0, -1, True, 1.5):
                with self.subTest(scale=scale):
                    with self.assertRaisesRegex(ValueError, "positive integer"):
                        sample_skin_sheet(source, Path(directory) / "result", scale=scale)

    def test_four_panel_sheet_observes_distinct_side_textures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "four-view.png"
            _write_four_view_source(source)

            artifacts = sample_skin_sheet(source, root / "result")
            with Image.open(artifacts.skin) as stored_skin:
                skin = stored_skin.convert("RGBA")
            right = skin.crop(_UV["torso"]["right"])
            left = skin.crop(_UV["torso"]["left"])
            self.assertNotEqual(right.tobytes(), left.tobytes())
            self.assertGreater(right.getpixel((0, 0))[0], right.getpixel((0, 0))[2])
            self.assertGreater(left.getpixel((0, 0))[2], left.getpixel((0, 0))[0])
            right_head = skin.crop(_UV["head"]["right"])
            left_head = skin.crop(_UV["head"]["left"])
            self.assertGreater(right_head.getpixel((7, 7))[0], 100)
            self.assertLess(right_head.getpixel((0, 7))[0], 100)
            self.assertGreater(left_head.getpixel((0, 7))[0], 100)
            self.assertLess(left_head.getpixel((7, 7))[0], 100)

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
            with self.assertRaisesRegex(ValueError, "two or four"):
                sample_skin_sheet(root / "blank.png", root / "invalid")


def _write_source(path: Path, *, protruding_chin: bool = False) -> None:
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
            if protruding_chin:
                draw.rectangle((origin + 32, 50, origin + 47, 59), fill="#e7a474")
        draw.rectangle((origin + 20, 110, origin + 39, 169), fill="#03434b")
        draw.rectangle((origin + 40, 110, origin + 59, 169), fill="#03434b")
    image.save(path)


def _write_four_view_source(path: Path) -> None:
    image = Image.new("RGB", (600, 200), "white")
    draw = ImageDraw.Draw(image)
    _draw_front_or_back(draw, 20, back=False)
    _draw_side(draw, 180, color="#b02020", front_on_left=True)
    _draw_front_or_back(draw, 320, back=True)
    _draw_side(draw, 500, color="#2030b0", front_on_left=False)
    image.save(path)


def _draw_front_or_back(draw: ImageDraw.ImageDraw, origin: int, *, back: bool) -> None:
    draw.rectangle((origin + 20, 10, origin + 59, 49), fill="#181818")
    if not back:
        draw.rectangle((origin + 25, 25, origin + 54, 49), fill="#e7a474")
    draw.rectangle((origin + 20, 50, origin + 59, 109), fill="#d99b00")
    draw.rectangle((origin, 50, origin + 19, 109), fill="#d99b00")
    draw.rectangle((origin + 60, 50, origin + 79, 109), fill="#d99b00")
    draw.rectangle((origin + 20, 110, origin + 39, 169), fill="#03434b")
    draw.rectangle((origin + 40, 110, origin + 59, 169), fill="#03434b")


def _draw_side(
    draw: ImageDraw.ImageDraw, origin: int, *, color: str, front_on_left: bool
) -> None:
    draw.rectangle((origin, 10, origin + 39, 49), fill="#181818")
    face_left = origin if front_on_left else origin + 20
    draw.rectangle((face_left, 30, face_left + 19, 49), fill="#e7a474")
    draw.rectangle((origin + 10, 50, origin + 29, 109), fill=color)
    draw.rectangle((origin + 10, 110, origin + 29, 169), fill="#03434b")


if __name__ == "__main__":
    unittest.main()
