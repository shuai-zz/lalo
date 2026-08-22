from __future__ import annotations

import io
import math
import struct
import tempfile
import unittest
from pathlib import Path

from lalo.meshing import Mesh, mesh_occupancy
from lalo.stl import binary_stl_bytes, write_binary_stl

_TRIANGLE = struct.Struct("<12fH")


class BinaryStlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cube = mesh_occupancy([[[1]]])

    def test_exports_cube_with_scaled_coordinates_and_unit_normals(self) -> None:
        data = binary_stl_bytes(self.cube, scale_mm=2.5)

        self.assertEqual(len(data), 84 + 12 * 50)
        self.assertEqual(struct.unpack_from("<I", data, 80)[0], 12)

        coordinates: list[float] = []
        for index in range(12):
            triangle = _TRIANGLE.unpack_from(data, 84 + index * 50)
            normal = triangle[0:3]
            vertices = tuple(
                tuple(triangle[start : start + 3]) for start in (3, 6, 9)
            )
            coordinates.extend(triangle[3:12])
            self.assertAlmostEqual(math.sqrt(sum(value**2 for value in normal)), 1.0)
            self.assertEqual(normal, _normal(*vertices))

        self.assertEqual(min(coordinates), 0.0)
        self.assertEqual(max(coordinates), 2.5)

    def test_export_is_deterministic(self) -> None:
        self.assertEqual(binary_stl_bytes(self.cube), binary_stl_bytes(self.cube))

    def test_writes_to_binary_stream_and_path(self) -> None:
        expected = binary_stl_bytes(self.cube)
        stream = io.BytesIO()
        write_binary_stl(self.cube, stream)
        self.assertEqual(stream.getvalue(), expected)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cube.stl"
            write_binary_stl(self.cube, path)
            self.assertEqual(path.read_bytes(), expected)

    def test_rejects_invalid_scale(self) -> None:
        for value in (0, -1, math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "scale_mm"):
                    binary_stl_bytes(self.cube, scale_mm=value)
        with self.assertRaisesRegex(TypeError, "scale_mm"):
            binary_stl_bytes(self.cube, scale_mm=True)

    def test_rejects_missing_vertices_and_degenerate_faces(self) -> None:
        missing = Mesh(vertices=((0, 0, 0),), faces=((0, 1, 0),))
        with self.assertRaisesRegex(ValueError, "missing vertex"):
            binary_stl_bytes(missing)

        degenerate = Mesh(
            vertices=((0, 0, 0), (1, 0, 0), (2, 0, 0)),
            faces=((0, 1, 2),),
        )
        with self.assertRaisesRegex(ValueError, "degenerate"):
            binary_stl_bytes(degenerate)

    def test_rejects_text_stream(self) -> None:
        with self.assertRaisesRegex(TypeError, "binary data"):
            write_binary_stl(self.cube, io.StringIO())


def _normal(
    a: tuple[float, ...], b: tuple[float, ...], c: tuple[float, ...]
) -> tuple[float, float, float]:
    ab = tuple(b[index] - a[index] for index in range(3))
    ac = tuple(c[index] - a[index] for index in range(3))
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    length = math.sqrt(sum(value**2 for value in cross))
    return tuple(value / length for value in cross)


if __name__ == "__main__":
    unittest.main()
