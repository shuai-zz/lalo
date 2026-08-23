from __future__ import annotations

import io
import unittest

from PIL import Image, ImageDraw

from lalo import (
    CharacterSheet,
    DesignRaster,
    DesignView,
    DesignViewName,
    compile_head_visual_hull,
    crop_design_parts,
)
from lalo.relief import mesh_detailed_part
from lalo.validation import validate_mesh


class HeadVisualHullTests(unittest.TestCase):
    def test_builds_a_bounded_stepped_head_with_profile_depth(self) -> None:
        hull = compile_head_visual_hull(crop_design_parts(_profile_sheet()))

        self.assertEqual(
            (len(hull.occupancy), len(hull.occupancy[0]), len(hull.occupancy[0][0])),
            (40, 40, 40),
        )
        self.assertTrue(
            all(value for layer in hull.occupancy[:5] for row in layer for value in row)
        )
        self.assertFalse(hull.occupancy[35][5][5])
        self.assertTrue(hull.occupancy[20][20][20])
        occupied = sum(
            value for layer in hull.occupancy for row in layer for value in row
        )
        self.assertLess(occupied, 40**3)

    def test_mesh_is_one_watertight_component_and_deterministic(self) -> None:
        crops = crop_design_parts(_profile_sheet())

        first = compile_head_visual_hull(crops)
        second = compile_head_visual_hull(crops)
        validation = validate_mesh(mesh_detailed_part(first))

        self.assertEqual(first, second)
        self.assertTrue(validation.valid)
        self.assertEqual(validation.component_count, 1)


def _profile_sheet() -> CharacterSheet:
    views = []
    for name in DesignViewName:
        image = Image.new("RGB", (80, 160), "white")
        draw = ImageDraw.Draw(image)
        if name in (DesignViewName.FRONT, DesignViewName.BACK):
            draw.rectangle((20, 52, 59, 147), fill="#C08060")
            draw.rectangle((30, 36, 49, 51), fill="#402820")
            draw.rectangle((34, 20, 45, 35), fill="#402820")
        elif name == DesignViewName.LEFT:
            draw.rectangle((30, 52, 49, 147), fill="#C08060")
            draw.rectangle((32, 36, 49, 51), fill="#402820")
            draw.rectangle((35, 20, 49, 35), fill="#402820")
        else:
            draw.rectangle((30, 52, 49, 147), fill="#C08060")
            draw.rectangle((30, 36, 47, 51), fill="#402820")
            draw.rectangle((30, 20, 44, 35), fill="#402820")
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
