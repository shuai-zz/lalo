from __future__ import annotations

import unittest

from lalo.appearance import SurfaceFace, SurfaceMap
from lalo.body import PartSpec
from lalo.relief import compile_part_relief, mesh_detailed_part
from lalo.validation import validate_mesh


class ReliefCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.part = PartSpec("test", (1, 1, 1), (0, 0, 0))

    def test_raised_and_engraved_front_pixels_change_volume(self) -> None:
        raised = mesh_detailed_part(
            compile_part_relief(
                self.part, (_surface(SurfaceFace.FRONT, center_level=1),)
            )
        )
        engraved = mesh_detailed_part(
            compile_part_relief(
                self.part, (_surface(SurfaceFace.FRONT, center_level=-1),)
            )
        )

        self.assertEqual(_volume(raised), 126.0)
        self.assertEqual(_volume(engraved), 124.0)
        self.assertTrue(validate_mesh(raised).valid)
        self.assertTrue(validate_mesh(engraved).valid)

    def test_positive_and_negative_faces_extend_correct_bounds(self) -> None:
        expectations = {
            SurfaceFace.FRONT: ((0, -1, 0), (5, 5, 5)),
            SurfaceFace.BACK: ((0, 0, 0), (5, 6, 5)),
            SurfaceFace.LEFT: ((0, 0, 0), (6, 5, 5)),
            SurfaceFace.RIGHT: ((-1, 0, 0), (5, 5, 5)),
            SurfaceFace.TOP: ((0, 0, 0), (5, 5, 6)),
            SurfaceFace.BOTTOM: ((0, 0, -1), (5, 5, 5)),
        }
        for face, expected_bounds in expectations.items():
            with self.subTest(face=face):
                mesh = mesh_detailed_part(
                    compile_part_relief(
                        self.part, (_surface(face, center_level=1),)
                    )
                )
                self.assertEqual(_bounds(mesh), expected_bounds)

    def test_level_two_extends_two_detail_cells(self) -> None:
        mesh = mesh_detailed_part(
            compile_part_relief(
                self.part, (_surface(SurfaceFace.TOP, center_level=2),)
            )
        )

        self.assertEqual(_bounds(mesh)[1][2], 7)
        self.assertEqual(_volume(mesh), 127.0)

    def test_no_surfaces_preserves_base_bounds_and_volume(self) -> None:
        mesh = mesh_detailed_part(compile_part_relief(self.part, ()))

        self.assertEqual(_bounds(mesh), ((0, 0, 0), (5, 5, 5)))
        self.assertEqual(_volume(mesh), 125.0)

    def test_rejects_wrong_face_dimensions_and_duplicate_faces(self) -> None:
        wrong = SurfaceMap(SurfaceFace.FRONT, ((0,),), ((0,),))
        with self.assertRaisesRegex(ValueError, "must be 5x5"):
            compile_part_relief(self.part, (wrong,))
        surface = _surface(SurfaceFace.FRONT)
        with self.assertRaisesRegex(ValueError, "duplicate surface"):
            compile_part_relief(self.part, (surface, surface))

    def test_output_is_deterministic(self) -> None:
        surfaces = (_surface(SurfaceFace.FRONT, center_level=1),)

        self.assertEqual(
            compile_part_relief(self.part, surfaces),
            compile_part_relief(self.part, surfaces),
        )


def _surface(face: SurfaceFace, center_level: int = 0) -> SurfaceMap:
    if face in (SurfaceFace.FRONT, SurfaceFace.BACK, SurfaceFace.LEFT, SurfaceFace.RIGHT):
        height, width = 5, 5
    else:
        height, width = 5, 5
    relief = tuple(
        tuple(center_level if (row, column) == (2, 2) else 0 for column in range(width))
        for row in range(height)
    )
    materials = tuple(tuple(0 for _ in range(width)) for _ in range(height))
    return SurfaceMap(face, relief, materials)


def _bounds(mesh: object) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    vertices = mesh.vertices  # type: ignore[attr-defined]
    return (
        tuple(min(vertex[axis] for vertex in vertices) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in vertices) for axis in range(3)),
    )


def _volume(mesh: object) -> float:
    result = validate_mesh(mesh)  # type: ignore[arg-type]
    if result.signed_volume is None:
        raise AssertionError("mesh has no volume")
    return result.signed_volume


if __name__ == "__main__":
    unittest.main()
