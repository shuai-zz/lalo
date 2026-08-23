from __future__ import annotations

import unittest

from lalo.appearance import SurfaceFace, SurfaceMap
from lalo.printability import clean_relief_for_fdm


class ReliefPrintabilityTests(unittest.TestCase):
    def test_expands_isolated_pixel_to_two_by_two_at_default_scale(self) -> None:
        surface = _surface(((0, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)))

        result = clean_relief_for_fdm(surface)

        self.assertEqual(result.detail_pitch_mm, 0.6)
        self.assertEqual(result.expanded_pixel_count, 3)
        self.assertEqual(_nonzero_count(result.surface.relief), 4)
        self.assertEqual(result.depth_adjustment_count, 0)

    def test_preserves_negative_sign_and_copies_material(self) -> None:
        surface = SurfaceMap(
            SurfaceFace.FRONT,
            ((0, 0, 0), (0, -1, 0), (0, 0, 0)),
            ((0, 0, 0), (0, 3, 0), (0, 0, 0)),
        )

        result = clean_relief_for_fdm(surface)

        nonzero = [
            (level, result.surface.materials[row][column])
            for row, values in enumerate(result.surface.relief)
            for column, level in enumerate(values)
            if level != 0
        ]
        self.assertEqual(nonzero, [(-1, 3)] * 4)

    def test_keeps_already_printable_two_by_two_feature_unchanged(self) -> None:
        surface = _surface(((1, 1, 0), (1, 1, 0), (0, 0, 0)))

        result = clean_relief_for_fdm(surface)

        self.assertEqual(result.surface.relief, surface.relief)
        self.assertEqual(result.expanded_pixel_count, 0)

    def test_adjusts_depth_for_smaller_physical_scale(self) -> None:
        surface = _surface(tuple(tuple(1 for _ in range(4)) for _ in range(4)))

        result = clean_relief_for_fdm(surface, height_mm=32)

        self.assertEqual(result.detail_pitch_mm, 0.2)
        self.assertTrue(all(level == 2 for row in result.surface.relief for level in row))
        self.assertEqual(result.depth_adjustment_count, 16)

    def test_rejects_unrepresentable_depth_or_width(self) -> None:
        surface = _surface(((1, 0), (0, 0)))
        with self.assertRaisesRegex(ValueError, "cannot be represented"):
            clean_relief_for_fdm(surface, height_mm=20)
        with self.assertRaisesRegex(ValueError, "does not fit"):
            clean_relief_for_fdm(surface, minimum_line_width_mm=2.0)

    def test_output_is_deterministic(self) -> None:
        surface = _surface(((0, 1, 0), (0, 0, 0), (0, 0, 0)))
        self.assertEqual(clean_relief_for_fdm(surface), clean_relief_for_fdm(surface))


def _surface(relief: tuple[tuple[int, ...], ...]) -> SurfaceMap:
    materials = tuple(tuple(0 for _ in row) for row in relief)
    return SurfaceMap(SurfaceFace.FRONT, relief, materials)


def _nonzero_count(grid: tuple[tuple[int, ...], ...]) -> int:
    return sum(level != 0 for row in grid for level in row)


if __name__ == "__main__":
    unittest.main()
