from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

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

            self.assertEqual(head_accessor["max"], [20.0, 20.0, 20.0])
            self.assertEqual(head_node["translation"], [-10.0, -10.0, 60.0])
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
            self.assertEqual(assembled_top_z, 80.0)

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


if __name__ == "__main__":
    unittest.main()
