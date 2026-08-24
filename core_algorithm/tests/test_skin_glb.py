from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from lalo_core.skin_glb import write_textured_skin_glb


class TexturedSkinGlbTests(unittest.TestCase):
    def test_writes_six_part_self_contained_textured_glb(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skin = root / "skin.png"
            _write_skin(skin)

            path = write_textured_skin_glb(skin, root / "preview.glb")
            document, binary = _read_glb(path)

            self.assertEqual(document["asset"]["version"], "2.0")
            self.assertEqual(
                [node["name"] for node in document["nodes"]],
                ["head", "torso", "right_arm", "left_arm", "right_leg", "left_leg"],
            )
            self.assertEqual(len(document["meshes"]), 6)
            self.assertEqual(document["images"][0]["mimeType"], "image/png")
            self.assertEqual(document["samplers"][0]["magFilter"], 9728)
            image_view = document["bufferViews"][document["images"][0]["bufferView"]]
            image = binary[
                image_view["byteOffset"] : image_view["byteOffset"]
                + image_view["byteLength"]
            ]
            self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_bounds_describe_standard_thirty_two_unit_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skin = root / "skin.png"
            _write_skin(skin)
            document, _ = _read_glb(
                write_textured_skin_glb(skin, root / "preview.glb")
            )

            position_accessors = [
                mesh["primitives"][0]["attributes"]["POSITION"]
                for mesh in document["meshes"]
            ]
            minimum_y = min(document["accessors"][index]["min"][1] for index in position_accessors)
            maximum_y = max(document["accessors"][index]["max"][1] for index in position_accessors)
            self.assertEqual((minimum_y, maximum_y), (0.0, 32.0))

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skin = root / "skin.png"
            _write_skin(skin)

            first = write_textured_skin_glb(skin, root / "first.glb")
            second = write_textured_skin_glb(skin, root / "second.glb")
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_rejects_invalid_skin_and_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / "invalid.png"
            Image.new("RGB", (32, 64), "red").save(invalid)
            with self.assertRaisesRegex(ValueError, "64x64"):
                write_textured_skin_glb(invalid, root / "invalid.glb")

            skin = root / "skin.png"
            _write_skin(skin)
            existing = root / "existing.glb"
            existing.write_bytes(b"keep")
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                write_textured_skin_glb(skin, existing)
            self.assertEqual(existing.read_bytes(), b"keep")


def _write_skin(path: Path) -> None:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for y in range(64):
        for x in range(64):
            image.putpixel((x, y), (x * 4, y * 4, (x + y) * 2, 255))
    image.save(path)


def _read_glb(path: Path) -> tuple[dict, bytes]:
    payload = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", payload, 0)
    if (magic, version, length) != (b"glTF", 2, len(payload)):
        raise AssertionError("invalid GLB header")
    json_length, json_type = struct.unpack_from("<I4s", payload, 12)
    if json_type != b"JSON":
        raise AssertionError("missing JSON chunk")
    json_start = 20
    document = json.loads(payload[json_start : json_start + json_length])
    binary_header = json_start + json_length
    binary_length, binary_type = struct.unpack_from("<I4s", payload, binary_header)
    if binary_type != b"BIN\x00":
        raise AssertionError("missing binary chunk")
    binary_start = binary_header + 8
    return document, payload[binary_start : binary_start + binary_length]


if __name__ == "__main__":
    unittest.main()
