from __future__ import annotations

import io
import unittest

from PIL import Image, ImageDraw

from lalo import (
    CANONICAL_PARTS,
    CharacterSheet,
    DesignPartCrops,
    DesignRaster,
    DesignView,
    DesignViewName,
    crop_design_parts,
)


class DesignCropTests(unittest.TestCase):
    def test_crops_every_part_in_stable_view_major_order(self) -> None:
        result = crop_design_parts(_sheet())

        self.assertIsInstance(result, DesignPartCrops)
        self.assertEqual(len(result.crops), 4 * len(CANONICAL_PARTS))
        self.assertEqual(
            [(crop.view, crop.part_name) for crop in result.crops[:2]],
            [
                (DesignViewName.FRONT, "head"),
                (DesignViewName.FRONT, "torso"),
            ],
        )
        self.assertTrue(
            all(crop.image.media_type == "image/png" for crop in result.crops)
        )

    def test_disconnected_label_does_not_change_character_bounds(self) -> None:
        sheet = _sheet(with_label=True)

        result = crop_design_parts(sheet)

        front = result.crops[: len(CANONICAL_PARTS)]
        self.assertTrue(all(crop.source_box[1] >= 20 for crop in front))

    def test_back_and_right_views_reverse_the_projected_axis(self) -> None:
        result = crop_design_parts(_sheet())
        by_key = {(crop.view, crop.part_name): crop for crop in result.crops}

        front_left = by_key[(DesignViewName.FRONT, "left_upper_arm")].source_box
        front_right = by_key[(DesignViewName.FRONT, "right_upper_arm")].source_box
        back_left = by_key[(DesignViewName.BACK, "left_upper_arm")].source_box
        back_right = by_key[(DesignViewName.BACK, "right_upper_arm")].source_box
        self.assertGreater(front_left[0], front_right[0])
        self.assertLess(back_left[0], back_right[0])

    def test_rejects_blank_or_mismatched_views(self) -> None:
        blank = _raster(Image.new("RGB", (80, 160), "white"))
        with self.assertRaisesRegex(ValueError, "no foreground"):
            crop_design_parts(
                CharacterSheet(
                    tuple(DesignView(name, blank) for name in DesignViewName)
                )
            )
        raster = _raster(Image.new("RGB", (80, 160), "white"))
        mismatched = DesignRaster(raster.data, "image/png", 81, 160)
        with self.assertRaisesRegex(ValueError, "decoded dimensions"):
            crop_design_parts(
                CharacterSheet(
                    tuple(DesignView(name, mismatched) for name in DesignViewName)
                )
            )


def _sheet(*, with_label: bool = False) -> CharacterSheet:
    views = []
    for name in DesignViewName:
        image = Image.new("RGB", (80, 160), "white")
        draw = ImageDraw.Draw(image)
        width = 40 if name in (DesignViewName.FRONT, DesignViewName.BACK) else 20
        left = (image.width - width) // 2
        draw.rectangle((left, 20, left + width - 1, 147), fill="red")
        if with_label:
            draw.rectangle((5, 4, 20, 9), fill="black")
        views.append(DesignView(name, _raster(image)))
    return CharacterSheet(tuple(views))


def _raster(image: Image.Image) -> DesignRaster:
    encoded = io.BytesIO()
    image.save(encoded, format="PNG")
    return DesignRaster(encoded.getvalue(), "image/png", image.width, image.height)


if __name__ == "__main__":
    unittest.main()
