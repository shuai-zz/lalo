from __future__ import annotations

import math
import unittest

from lalo_core.body import CANONICAL_PARTS, mesh_part
from lalo_core.meshing import Mesh, mesh_occupancy
from lalo_core.validation import validate_mesh


class MeshValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cube = mesh_occupancy([[[1]]])

    def test_accepts_cube_and_all_canonical_parts(self) -> None:
        cube_result = validate_mesh(self.cube)

        self.assertTrue(cube_result.valid)
        self.assertEqual(cube_result.issues, ())
        self.assertEqual(cube_result.vertex_count, 8)
        self.assertEqual(cube_result.triangle_count, 12)
        self.assertEqual(cube_result.edge_count, 18)
        self.assertEqual(cube_result.component_count, 1)
        self.assertEqual(cube_result.signed_volume, 1.0)
        self.assertTrue(all(validate_mesh(mesh_part(part)).valid for part in CANONICAL_PARTS))

    def test_rejects_open_mesh(self) -> None:
        result = validate_mesh(
            Mesh(vertices=self.cube.vertices, faces=self.cube.faces[:-2])
        )

        self.assertIn("non_manifold_edges", _codes(result))

    def test_rejects_degenerate_and_duplicate_triangles(self) -> None:
        result = validate_mesh(
            Mesh(
                vertices=self.cube.vertices,
                faces=self.cube.faces + (self.cube.faces[0], (0, 0, 1)),
            )
        )

        self.assertIn("duplicate_triangle", _codes(result))
        self.assertIn("degenerate_triangle", _codes(result))

    def test_rejects_reversed_winding(self) -> None:
        reversed_mesh = Mesh(
            vertices=self.cube.vertices,
            faces=tuple((a, c, b) for a, b, c in self.cube.faces),
        )

        self.assertIn("non_positive_volume", _codes(validate_mesh(reversed_mesh)))

    def test_rejects_disconnected_solids(self) -> None:
        result = validate_mesh(mesh_occupancy([[[1, 0, 1]]]))

        self.assertIn("disconnected_mesh", _codes(result))
        self.assertEqual(result.component_count, 2)

    def test_rejects_invalid_indices(self) -> None:
        result = validate_mesh(
            Mesh(vertices=self.cube.vertices, faces=self.cube.faces + ((0, 1, 100),))
        )

        self.assertIn("invalid_index", _codes(result))

    def test_rejects_non_finite_vertices(self) -> None:
        vertices = self.cube.vertices + ((math.inf, 0, 0),)
        result = validate_mesh(Mesh(vertices=vertices, faces=self.cube.faces))

        self.assertIn("invalid_vertex", _codes(result))
        self.assertIsNone(result.signed_volume)

    def test_reports_empty_mesh(self) -> None:
        result = validate_mesh(Mesh(vertices=(), faces=()))

        self.assertEqual(_codes(result), {"empty_vertices", "empty_faces"})
        self.assertFalse(result.valid)


def _codes(result: object) -> set[str]:
    return {issue.code for issue in result.issues}  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
