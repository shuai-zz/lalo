from __future__ import annotations

import struct
import tempfile
import unittest
import hashlib
import json
from pathlib import Path

from lalo_core.body import CANONICAL_PARTS
from lalo_core.generate import write_canonical_manifest, write_canonical_stls

_TRIANGLE = struct.Struct("<12fH")


class CanonicalStlSetTests(unittest.TestCase):
    def test_writes_all_parts_in_canonical_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_canonical_stls(Path(directory) / "stl")

            self.assertEqual(
                tuple(path.name for path in paths),
                tuple(f"{part.name}.stl" for part in CANONICAL_PARTS),
            )
            self.assertTrue(all(path.is_file() for path in paths))
            self.assertTrue(all(_triangle_count(path) > 0 for path in paths))

    def test_scales_head_to_default_twenty_four_millimeter_cube(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_canonical_stls(directory)
            head_path = next(path for path in paths if path.name == "head.stl")

            self.assertEqual(_bounds(head_path), ((0.0, 0.0, 0.0), (24.0, 24.0, 24.0)))

    def test_custom_height_scales_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_canonical_stls(directory, height_mm=160)
            head_path = next(path for path in paths if path.name == "head.stl")

            self.assertEqual(_bounds(head_path)[1], (40.0, 40.0, 40.0))

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_canonical_stls(root / "first")
            second = write_canonical_stls(root / "second")

            self.assertEqual(
                tuple(path.read_bytes() for path in first),
                tuple(path.read_bytes() for path in second),
            )

    def test_rejects_non_empty_directory_without_modifying_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "must be empty"):
                write_canonical_stls(directory)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertEqual(tuple(Path(directory).iterdir()), (marker,))

    def test_rejects_invalid_height(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for height in (0, -1, float("inf"), float("nan")):
                with self.subTest(height=height):
                    with self.assertRaisesRegex(ValueError, "height_mm"):
                        write_canonical_stls(Path(directory) / "out", height_mm=height)


class CanonicalManifestTests(unittest.TestCase):
    def test_describes_all_parts_scale_and_coordinate_system(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            write_canonical_stls(directory)
            manifest_path = write_canonical_manifest(directory)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["schema_version"], "1.0")
            self.assertEqual(manifest["height_mm"], 96.0)
            self.assertEqual(manifest["master_voxel_mm"], 3.0)
            self.assertEqual(manifest["coordinate_system"]["up_axis"], "+Z")
            self.assertEqual(len(manifest["parts"]), 14)

            head = manifest["parts"][0]
            self.assertEqual(head["name"], "head")
            self.assertEqual(head["size_mm"], [24.0, 24.0, 24.0])
            self.assertEqual(head["assembly_translation_mm"], [-12.0, -12.0, 72.0])
            self.assertEqual(head["assembly_rotation_xyzw"], [0.0, 0.0, 0.0, 1.0])

            left_thigh = next(
                part for part in manifest["parts"] if part["name"] == "left_thigh"
            )
            right_thigh = next(
                part for part in manifest["parts"] if part["name"] == "right_thigh"
            )
            self.assertEqual(left_thigh["assembly_translation_mm"][0], 0.4)
            self.assertEqual(right_thigh["assembly_translation_mm"][0], -12.4)

    def test_records_matching_file_sizes_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            write_canonical_stls(directory)
            manifest = json.loads(
                write_canonical_manifest(directory).read_text(encoding="utf-8")
            )

            for part in manifest["parts"]:
                data = (Path(directory) / part["file"]).read_bytes()
                self.assertEqual(part["byte_size"], len(data))
                self.assertEqual(part["sha256"], hashlib.sha256(data).hexdigest())

    def test_manifest_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            write_canonical_stls(directory)
            path = write_canonical_manifest(directory)
            first = path.read_bytes()
            second = write_canonical_manifest(directory).read_bytes()

            self.assertEqual(first, second)

    def test_missing_stl_prevents_manifest_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            write_canonical_stls(directory)
            (Path(directory) / "head.stl").unlink()

            with self.assertRaisesRegex(FileNotFoundError, "head.stl"):
                write_canonical_manifest(directory)
            self.assertFalse((Path(directory) / "manifest.json").exists())


def _triangle_count(path: Path) -> int:
    return struct.unpack_from("<I", path.read_bytes(), 80)[0]


def _bounds(
    path: Path,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    data = path.read_bytes()
    coordinates: list[tuple[float, float, float]] = []
    for index in range(struct.unpack_from("<I", data, 80)[0]):
        triangle = _TRIANGLE.unpack_from(data, 84 + index * 50)
        coordinates.extend(
            tuple(triangle[start : start + 3]) for start in (3, 6, 9)
        )
    return (
        tuple(min(vertex[axis] for vertex in coordinates) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in coordinates) for axis in range(3)),
    )


if __name__ == "__main__":
    unittest.main()
