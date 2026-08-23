from __future__ import annotations

import io
import unittest

from PIL import Image, ImageDraw

from lalo import (
    CANONICAL_PARTS,
    CharacterRegion,
    CharacterSheet,
    DesignRaster,
    DesignView,
    DesignViewName,
    FeatureImportance,
    IdentityFeature,
    IdentitySpec,
    PaletteEntry,
    SurfaceFace,
    character_plan_to_json,
    crop_design_parts,
    sample_design_materials,
)
from lalo.relief import face_detail_shape


class DesignMaterialTests(unittest.TestCase):
    def test_samples_four_faces_for_every_part_with_zero_relief(self) -> None:
        plan = sample_design_materials(_identity(), crop_design_parts(_sheet()))

        self.assertEqual(len(plan.parts), len(CANONICAL_PARTS))
        for appearance, part in zip(plan.parts, CANONICAL_PARTS):
            self.assertEqual(
                tuple(surface.face for surface in appearance.surfaces),
                (
                    SurfaceFace.FRONT,
                    SurfaceFace.BACK,
                    SurfaceFace.LEFT,
                    SurfaceFace.RIGHT,
                ),
            )
            for surface in appearance.surfaces:
                self.assertEqual(
                    (len(surface.materials), len(surface.materials[0])),
                    face_detail_shape(part, surface.face),
                )
                self.assertTrue(
                    all(value == 0 for row in surface.relief for value in row)
                )

    def test_background_does_not_become_a_material(self) -> None:
        plan = sample_design_materials(_identity(), crop_design_parts(_sheet()))

        referenced = {
            value
            for part in plan.parts
            for surface in part.surfaces
            for row in surface.materials
            for value in row
        }
        self.assertEqual(referenced, {0, 1})
        head = plan.parts[0]
        self.assertEqual(
            {value for row in head.surfaces[0].materials for value in row}, {0}
        )
        feet = [part for part in plan.parts if part.part_name.endswith("foot")]
        self.assertTrue(
            all(
                {value for row in part.surfaces[0].materials for value in row} == {1}
                for part in feet
            )
        )

    def test_sampling_is_deterministic(self) -> None:
        crops = crop_design_parts(_sheet())

        first = sample_design_materials(_identity(), crops)
        second = sample_design_materials(_identity(), crops)

        self.assertEqual(character_plan_to_json(first), character_plan_to_json(second))


def _identity() -> IdentitySpec:
    return IdentitySpec(
        "1.0",
        "two color hero",
        "red upper body and blue lower body",
        (
            PaletteEntry(0, "red", "#D02020"),
            PaletteEntry(1, "blue", "#2040D0"),
            PaletteEntry(2, "background", "#FFFFFF"),
        ),
        (
            IdentityFeature(
                "color split",
                CharacterRegion.TORSO,
                "red above and blue below",
                FeatureImportance.PRIMARY,
            ),
        ),
    )


def _sheet() -> CharacterSheet:
    views = []
    for name in DesignViewName:
        image = Image.new("RGB", (80, 160), "white")
        draw = ImageDraw.Draw(image)
        width = 40 if name in (DesignViewName.FRONT, DesignViewName.BACK) else 20
        left = (image.width - width) // 2
        head_inset = width // 4
        draw.rectangle(
            (left + head_inset, 20, left + width - head_inset - 1, 39),
            fill="#D02020",
        )
        draw.rectangle((left, 40, left + width - 1, 99), fill="#D02020")
        draw.rectangle((left, 100, left + width - 1, 147), fill="#2040D0")
        draw.rectangle((5, 4, 20, 9), fill="black")
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")
        views.append(
            DesignView(
                name,
                DesignRaster(
                    encoded.getvalue(), "image/png", image.width, image.height
                ),
            )
        )
    return CharacterSheet(tuple(views))


if __name__ == "__main__":
    unittest.main()
