from __future__ import annotations

import unittest

from lalo.meshing import Mesh, mesh_occupancy
from lalo.voxel import solid_cuboid


class SolidCuboidTests(unittest.TestCase):
    def test_builds_expected_zyx_shape_and_occupancy(self) -> None:
        grid = solid_cuboid(2, 3, 4)

        self.assertIsInstance(grid, tuple)
        self.assertEqual(len(grid), 4)
        self.assertEqual(len(grid[0]), 3)
        self.assertEqual(len(grid[0][0]), 2)
        self.assertEqual(
            sum(cell for layer in grid for row in layer for cell in row), 24
        )

    def test_result_is_immutable(self) -> None:
        grid = solid_cuboid(1, 1, 1)

        with self.assertRaises(TypeError):
            grid[0][0][0] = False  # type: ignore[index]

    def test_integrates_with_mesher_at_expected_volume(self) -> None:
        mesh = mesh_occupancy(solid_cuboid(2, 3, 4))

        self.assertAlmostEqual(_signed_volume(mesh), 24.0)

    def test_rejects_non_positive_dimensions(self) -> None:
        for dimensions in ((0, 1, 1), (1, -1, 1), (1, 1, 0)):
            with self.subTest(dimensions=dimensions):
                with self.assertRaisesRegex(ValueError, "greater than zero"):
                    solid_cuboid(*dimensions)

    def test_rejects_boolean_and_non_integer_dimensions(self) -> None:
        for dimensions in ((True, 1, 1), (1, 1.5, 1), (1, 1, "2")):
            with self.subTest(dimensions=dimensions):
                with self.assertRaisesRegex(TypeError, "must be an integer"):
                    solid_cuboid(*dimensions)  # type: ignore[arg-type]


def _signed_volume(mesh: Mesh) -> float:
    volume_times_six = 0
    for a_index, b_index, c_index in mesh.faces:
        ax, ay, az = mesh.vertices[a_index]
        bx, by, bz = mesh.vertices[b_index]
        cx, cy, cz = mesh.vertices[c_index]
        volume_times_six += (
            ax * (by * cz - bz * cy)
            + ay * (bz * cx - bx * cz)
            + az * (bx * cy - by * cx)
        )
    return volume_times_six / 6


if __name__ == "__main__":
    unittest.main()
