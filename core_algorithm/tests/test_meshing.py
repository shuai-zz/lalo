from __future__ import annotations

import unittest
from collections import Counter

from lalo_core.meshing import Mesh, mesh_occupancy


class MeshOccupancyTests(unittest.TestCase):
    def test_single_voxel_is_a_closed_unit_cube(self) -> None:
        mesh = mesh_occupancy([[[1]]])

        self.assertEqual(len(mesh.vertices), 8)
        self.assertEqual(len(mesh.faces), 12)
        self.assertEqual(_edge_incidence(mesh), {2})
        self.assertAlmostEqual(_signed_volume(mesh), 1.0)

    def test_adjacent_voxels_do_not_emit_the_shared_face(self) -> None:
        mesh = mesh_occupancy([[[1, 1]]])

        self.assertEqual(len(mesh.faces), 20)
        self.assertEqual(_edge_incidence(mesh), {2})
        self.assertAlmostEqual(_signed_volume(mesh), 2.0)

    def test_disconnected_voxels_remain_closed_components(self) -> None:
        mesh = mesh_occupancy([[[1, 0, 1]]])

        self.assertEqual(len(mesh.faces), 24)
        self.assertEqual(_edge_incidence(mesh), {2})
        self.assertAlmostEqual(_signed_volume(mesh), 2.0)

    def test_output_is_deterministic(self) -> None:
        occupancy = [[[1, 1], [0, 1]], [[0, 1], [0, 0]]]

        self.assertEqual(mesh_occupancy(occupancy), mesh_occupancy(occupancy))

    def test_rejects_empty_grid_and_empty_occupancy(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            mesh_occupancy([])
        with self.assertRaisesRegex(ValueError, "at least one occupied"):
            mesh_occupancy([[[0]]])

    def test_rejects_non_3d_ragged_and_non_binary_inputs(self) -> None:
        with self.assertRaisesRegex(TypeError, "three-dimensional"):
            mesh_occupancy([[1]])
        with self.assertRaisesRegex(ValueError, "rectangular"):
            mesh_occupancy([[[1], [1, 0]]])
        with self.assertRaisesRegex(TypeError, "bool, 0, or 1"):
            mesh_occupancy([[[2]]])


def _edge_incidence(mesh: Mesh) -> set[int]:
    edges: Counter[tuple[int, int]] = Counter()
    for a, b, c in mesh.faces:
        edges.update(
            (
                tuple(sorted((a, b))),
                tuple(sorted((b, c))),
                tuple(sorted((c, a))),
            )
        )
    return set(edges.values())


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
