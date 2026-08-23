from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SurfaceFace,
    SurfaceMap,
)
from lalo.body import CANONICAL_PARTS
from lalo.glb import write_canonical_glb


class CanonicalGlbTests(unittest.TestCase):
    def test_writes_glb_two_framing_with_json_and_binary_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = write_canonical_glb(directory).read_bytes()
            document, binary = _parse_glb(data)

            self.assertEqual(struct.unpack_from("<4sII", data), (b"glTF", 2, len(data)))
            self.assertEqual(document["asset"]["version"], "2.0")
            self.assertEqual(len(binary), document["buffers"][0]["byteLength"])

    def test_contains_fourteen_named_parts_under_conversion_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document, _ = _parse_glb(write_canonical_glb(directory).read_bytes())

            root = document["nodes"][0]
            expected_names = [part.name for part in CANONICAL_PARTS]
            self.assertEqual(root["children"], list(range(1, 15)))
            self.assertEqual(
                [node["name"] for node in document["nodes"][1:]], expected_names
            )
            self.assertEqual(len(document["meshes"]), 14)

    def test_head_bounds_translation_and_up_axis_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document, _ = _parse_glb(write_canonical_glb(directory).read_bytes())

            root = document["nodes"][0]
            head_node = document["nodes"][1]
            head_position_accessor = document["meshes"][0]["primitives"][0][
                "attributes"
            ]["POSITION"]
            head_accessor = document["accessors"][head_position_accessor]

            self.assertEqual(head_accessor["max"], [24.0, 24.0, 24.0])
            self.assertEqual(head_node["translation"], [-12.0, -12.0, 72.0])
            self.assertEqual(
                root["rotation"],
                [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)],
            )
            assembled_top_z = max(
                node["translation"][2]
                + document["accessors"][
                    document["meshes"][node["mesh"]]["primitives"][0]["attributes"][
                        "POSITION"
                    ]
                ]["max"][2]
                for node in document["nodes"][1:]
            )
            self.assertEqual(assembled_top_z, 96.0)

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_canonical_glb(root / "first").read_bytes()
            second = write_canonical_glb(root / "second").read_bytes()

            self.assertEqual(first, second)

    def test_rejects_invalid_height(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "height_mm"):
                write_canonical_glb(directory, height_mm=0)

    def test_renders_palette_and_groups_surface_patches_by_material(self) -> None:
        plan = _material_plan()
        with tempfile.TemporaryDirectory() as directory:
            document, _ = _parse_glb(
                write_canonical_glb(directory, plan=plan).read_bytes()
            )

            self.assertEqual([item["name"] for item in document["materials"]], ["red", "blue", "black", "white"])
            overlay = next(mesh for mesh in document["meshes"] if mesh["name"] == "head_materials")
            self.assertEqual(
                [primitive["material"] for primitive in overlay["primitives"]],
                [0, 1, 2, 3],
            )
            self.assertIn("head_materials", [node["name"] for node in document["nodes"]])

    def test_positions_raised_front_patch_outward(self) -> None:
        plan = _material_plan()
        with tempfile.TemporaryDirectory() as directory:
            document, binary = _parse_glb(
                write_canonical_glb(directory, plan=plan).read_bytes()
            )
            overlay = next(mesh for mesh in document["meshes"] if mesh["name"] == "head_materials")
            material_one = next(
                primitive for primitive in overlay["primitives"] if primitive["material"] == 1
            )
            accessor = document["accessors"][material_one["attributes"]["POSITION"]]
            view = document["bufferViews"][accessor["bufferView"]]
            first_position = struct.unpack_from("<3f", binary, view["byteOffset"])

            self.assertLess(first_position[1], -0.5)

    def test_material_output_is_deterministic(self) -> None:
        plan = _material_plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                write_canonical_glb(root / "first", plan=plan).read_bytes(),
                write_canonical_glb(root / "second", plan=plan).read_bytes(),
            )


def _parse_glb(data: bytes) -> tuple[dict[str, object], bytes]:
    magic, version, length = struct.unpack_from("<4sII", data)
    if (magic, version, length) != (b"glTF", 2, len(data)):
        raise AssertionError("invalid GLB header")
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise AssertionError("missing JSON chunk")
    json_start = 20
    json_end = json_start + json_length
    document = json.loads(data[json_start:json_end].decode("utf-8"))
    binary_length, binary_type = struct.unpack_from("<I4s", data, json_end)
    if binary_type != b"BIN\0":
        raise AssertionError("missing binary chunk")
    binary_start = json_end + 8
    return document, data[binary_start : binary_start + binary_length]


def _material_plan() -> CharacterPlan:
    size = 40
    materials = tuple(
        tuple((row * size + column) % 4 for column in range(size))
        for row in range(size)
    )
    relief = tuple(
        tuple(1 if materials[row][column] == 1 else 0 for column in range(size))
        for row in range(size)
    )
    return CharacterPlan(
        "1.0",
        "four-color head",
        (
            PaletteEntry(0, "red", "#FF0000"),
            PaletteEntry(1, "blue", "#0000FF"),
            PaletteEntry(2, "black", "#000000"),
            PaletteEntry(3, "white", "#FFFFFF"),
        ),
        (
            PartAppearance(
                "head",
                (SurfaceMap(SurfaceFace.FRONT, relief, materials),),
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
