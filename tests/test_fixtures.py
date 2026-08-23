from __future__ import annotations

import unittest

from lalo.appearance import CharacterPlan
from lalo.body import CANONICAL_PARTS
from lalo.fixtures import iron_man_plan, spider_man_plan
from lalo.printability import clean_relief_for_fdm
from lalo.protection import canonical_protection_masks, clip_protected_relief
from lalo.relief import compile_part_relief, face_detail_shape, mesh_detailed_part
from lalo.validation import validate_mesh


class CharacterFixtureTests(unittest.TestCase):
    def test_both_fixtures_are_deterministic_four_color_complete_plans(self) -> None:
        for builder in (spider_man_plan, iron_man_plan):
            with self.subTest(builder=builder.__name__):
                plan = builder()
                self.assertIsInstance(plan, CharacterPlan)
                self.assertEqual(len(plan.palette), 4)
                self.assertEqual(len(plan.parts), 14)
                self.assertEqual(plan, builder())

    def test_spider_man_contains_eyes_web_and_blue_suit_regions(self) -> None:
        plan = spider_man_plan()
        head = _part(plan, "head").surfaces[0]
        torso = _part(plan, "torso").surfaces[0]
        thigh = _part(plan, "left_thigh").surfaces[0]

        self.assertIn(3, {value for row in head.materials for value in row})
        self.assertTrue(any(value < 0 for row in head.relief for value in row))
        self.assertTrue(any(value > 0 for row in head.relief for value in row))
        self.assertIn(2, {value for row in torso.materials for value in row})
        self.assertTrue(all(value == 1 for row in thigh.materials for value in row))

    def test_spider_man_eyes_are_tapered_mirrored_voxel_masks(self) -> None:
        head = _part(spider_man_plan(), "head").surfaces[0]
        width = len(head.materials[0])
        left = {
            (row, column)
            for row, values in enumerate(head.materials)
            for column, material in enumerate(values)
            if material == 3 and column < width // 2
        }
        right = {
            (row, column)
            for row, values in enumerate(head.materials)
            for column, material in enumerate(values)
            if material == 3 and column >= width // 2
        }
        row_widths = {
            sum((row, column) in left for column in range(width // 2))
            for row in {row for row, _ in left}
        }

        self.assertGreaterEqual(len(row_widths), 4)
        self.assertEqual(min(row_widths), 2)
        self.assertEqual(
            right,
            {(row, width - 1 - column) for row, column in left},
        )
        self.assertTrue(
            all(head.relief[row][column] > 0 for row, column in left | right)
        )

        white = left | right
        expected_outline = {
            (row + row_offset, column + column_offset)
            for row, column in white
            for row_offset in range(-2, 3)
            for column_offset in range(-2, 3)
            if 0 <= row + row_offset < len(head.materials)
            and 0 <= column + column_offset < width
        } - white
        self.assertTrue(
            all(head.materials[row][column] == 2 for row, column in expected_outline)
        )

    def test_iron_man_contains_gold_faceplate_cyan_eyes_and_reactor(self) -> None:
        plan = iron_man_plan()
        head = _part(plan, "head").surfaces[0]
        torso = _part(plan, "torso").surfaces[0]

        self.assertIn(1, {value for row in head.materials for value in row})
        self.assertTrue(
            any(
                material == 3 and head.relief[row][column] > 0
                for row, values in enumerate(head.materials)
                for column, material in enumerate(values)
            )
        )
        self.assertTrue(
            any(
                material == 3 and torso.relief[row][column] > 0
                for row, values in enumerate(torso.materials)
                for column, material in enumerate(values)
            )
        )

    def test_all_maps_match_parts_and_compile_to_valid_meshes(self) -> None:
        specs = {part.name: part for part in CANONICAL_PARTS}
        for plan in (spider_man_plan(), iron_man_plan()):
            for appearance in plan.parts:
                with self.subTest(plan=plan.name, part=appearance.part_name):
                    part = specs[appearance.part_name]
                    surface = appearance.surfaces[0]
                    self.assertEqual(
                        (len(surface.relief), len(surface.relief[0])),
                        face_detail_shape(part, surface.face),
                    )
                    cleaned = clean_relief_for_fdm(surface).surface
                    clipped = clip_protected_relief(
                        (cleaned,), canonical_protection_masks(part)
                    ).surfaces
                    mesh = mesh_detailed_part(compile_part_relief(part, clipped))
                    self.assertTrue(validate_mesh(mesh).valid)


def _part(plan: CharacterPlan, name: str):
    return next(part for part in plan.parts if part.part_name == name)


if __name__ == "__main__":
    unittest.main()
