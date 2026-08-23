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
        head = _surface_for(plan, "head", "front")
        torso = _surface_for(plan, "torso", "front")
        thigh = _surface_for(plan, "left_thigh", "front")

        self.assertIn(3, {value for row in head.materials for value in row})
        self.assertTrue(
            any(
                material == 2 and head.relief[row][column] > 0
                for row, values in enumerate(head.materials)
                for column, material in enumerate(values)
            )
        )
        self.assertTrue(any(value > 0 for row in head.relief for value in row))
        self.assertIn(2, {value for row in torso.materials for value in row})
        self.assertTrue(all(value == 1 for row in thigh.materials for value in row))

    def test_spider_man_eyes_are_tapered_mirrored_voxel_masks(self) -> None:
        head = _surface_for(spider_man_plan(), "head", "front")
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

    def test_spider_man_chest_has_symmetric_eight_legged_spider_emblem(self) -> None:
        torso = _surface_for(spider_man_plan(), "torso", "front")
        width = len(torso.materials[0])
        raised_black = {
            (row, column)
            for row, values in enumerate(torso.materials)
            for column, material in enumerate(values)
            if material == 2 and torso.relief[row][column] > 0
        }
        left = {(row, column) for row, column in raised_black if column < width // 2}
        right = {(row, column) for row, column in raised_black if column >= width // 2}

        self.assertGreater(len(raised_black), 50)
        self.assertGreaterEqual(len({row for row, _ in raised_black}), 16)
        self.assertEqual(right, {(row, width - 1 - column) for row, column in left})

    def test_spider_man_has_red_webbed_boots_below_blue_legs(self) -> None:
        shin = _surface_for(spider_man_plan(), "left_shin", "front")
        foot = _surface_for(spider_man_plan(), "left_foot", "front")

        self.assertTrue(all(material == 1 for material in shin.materials[0]))
        self.assertIn(0, shin.materials[-1])
        self.assertTrue(any(value < 0 for row in shin.relief for value in row))
        self.assertGreater(
            sum(material == 0 for row in foot.materials for material in row),
            sum(material == 2 for row in foot.materials for material in row),
        )

    def test_spider_man_identity_details_wrap_around_visible_faces(self) -> None:
        plan = spider_man_plan()
        head_faces = {surface.face.value for surface in _part(plan, "head").surfaces}
        torso_faces = {surface.face.value for surface in _part(plan, "torso").surfaces}
        back = _surface_for(plan, "torso", "back")

        self.assertEqual(head_faces, {"front", "back", "left", "right", "top"})
        self.assertEqual(torso_faces, {"front", "back", "left", "right"})
        self.assertTrue(
            any(
                material == 0 and back.relief[row][column] > 0
                for row, values in enumerate(back.materials)
                for column, material in enumerate(values)
            )
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
                    for surface in appearance.surfaces:
                        self.assertEqual(
                            (len(surface.relief), len(surface.relief[0])),
                            face_detail_shape(part, surface.face),
                        )
                    cleaned = tuple(
                        clean_relief_for_fdm(surface).surface
                        for surface in appearance.surfaces
                    )
                    clipped = clip_protected_relief(
                        cleaned, canonical_protection_masks(part)
                    ).surfaces
                    mesh = mesh_detailed_part(compile_part_relief(part, clipped))
                    self.assertTrue(validate_mesh(mesh).valid)


def _part(plan: CharacterPlan, name: str):
    return next(part for part in plan.parts if part.part_name == name)


def _surface_for(plan: CharacterPlan, part_name: str, face: str):
    return next(
        surface
        for surface in _part(plan, part_name).surfaces
        if surface.face.value == face
    )


if __name__ == "__main__":
    unittest.main()
