from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from lalo import PaletteEntry, SurfaceFace, character_plan_from_skin_atlas


PALETTE = (
    PaletteEntry(0, "red", "#FF0000"),
    PaletteEntry(1, "blue", "#0000FF"),
    PaletteEntry(2, "black", "#000000"),
)


class SkinAtlasTests(unittest.TestCase):
    def test_hd_skin_maps_faces_and_splits_limbs(self) -> None:
        skin = Image.new("RGBA", (320, 320), "red")
        draw = ImageDraw.Draw(skin)
        draw.rectangle((180, 260, 199, 284), fill="red")
        draw.rectangle((180, 285, 199, 309), fill="blue")
        draw.rectangle((180, 310, 199, 319), fill="black")

        plan = character_plan_from_skin_atlas(
            skin, name="sample", palette=PALETTE
        )

        self.assertEqual(
            set(_surface(plan, "head", SurfaceFace.FRONT).materials[0]), {0}
        )
        self.assertEqual(
            set(_surface(plan, "left_upper_arm", SurfaceFace.FRONT).materials[0]),
            {0},
        )
        self.assertEqual(
            set(_surface(plan, "left_forearm", SurfaceFace.FRONT).materials[0]),
            {1},
        )
        self.assertEqual(
            set(_surface(plan, "left_hand", SurfaceFace.FRONT).materials[0]), {2}
        )

    def test_base_skin_quantizes_to_nearest_lab_palette_color(self) -> None:
        skin = Image.new("RGB", (64, 64), (245, 20, 20))

        plan = character_plan_from_skin_atlas(
            skin, name="sample", palette=PALETTE
        )

        self.assertEqual(
            _surface(plan, "torso", SurfaceFace.FRONT).materials[0][0], 0
        )

    def test_optional_mask_maps_exact_grayscale_codes_to_relief(self) -> None:
        skin = Image.new("RGB", (64, 64), "red")
        mask = Image.new("L", (64, 64), 128)
        mask.putpixel((20, 20), 64)

        plan = character_plan_from_skin_atlas(
            skin, name="sample", palette=PALETTE, relief_mask=mask
        )

        torso = _surface(plan, "torso", SurfaceFace.FRONT)
        self.assertEqual(torso.relief[0][0], -1)
        self.assertEqual(torso.relief[0][5], 0)

    def test_rejects_invalid_atlas_and_mask_inputs(self) -> None:
        skin = Image.new("RGB", (128, 64), "red")
        with self.assertRaisesRegex(ValueError, "square"):
            character_plan_from_skin_atlas(skin, name="sample", palette=PALETTE)

        skin = Image.new("RGB", (64, 64), "red")
        with self.assertRaisesRegex(ValueError, "dimensions"):
            character_plan_from_skin_atlas(
                skin,
                name="sample",
                palette=PALETTE,
                relief_mask=Image.new("L", (128, 128), 128),
            )

        mask = Image.new("L", (64, 64), 128)
        mask.putpixel((20, 20), 100)
        with self.assertRaisesRegex(ValueError, "mask pixels"):
            character_plan_from_skin_atlas(
                skin, name="sample", palette=PALETTE, relief_mask=mask
            )


def _surface(plan, part_name, face):
    part = next(part for part in plan.parts if part.part_name == part_name)
    return next(surface for surface in part.surfaces if surface.face == face)


if __name__ == "__main__":
    unittest.main()
