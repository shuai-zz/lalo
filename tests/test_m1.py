from __future__ import annotations

import gzip
import hashlib
import json
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
from lalo.fixtures import iron_man_plan, spider_man_plan
from lalo.m1 import generate_m1_artifacts
from lalo.relief import compile_part_relief, face_detail_shape


class M1ArtifactTests(unittest.TestCase):
    def test_both_golden_plans_generate_complete_valid_artifacts(self) -> None:
        for builder in (spider_man_plan, iron_man_plan):
            with (
                self.subTest(builder=builder.__name__),
                tempfile.TemporaryDirectory() as directory,
            ):
                output = Path(directory) / "result"
                artifacts = generate_m1_artifacts(builder(), output)
                files = {
                    path.relative_to(output).as_posix()
                    for path in output.rglob("*")
                    if path.is_file()
                }

                self.assertEqual(len(artifacts.stl_paths), 14)
                self.assertEqual(len(files), 19)
                report = json.loads(
                    artifacts.validation_report_path.read_text(encoding="utf-8")
                )
                self.assertEqual(report["status"], "passed")
                self.assertTrue(all(part["valid"] for part in report["parts"]))

    def test_manifest_hashes_and_relief_bounds_match_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            artifacts = generate_m1_artifacts(spider_man_plan(), output)
            manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["height_mm"], 96.0)
            self.assertEqual(manifest["detail_pitch_mm"], 0.6)
            head = next(part for part in manifest["parts"] if part["name"] == "head")
            self.assertLess(head["local_bounds_mm"][0][1], 0.0)
            data = (output / head["file"]).read_bytes()
            self.assertEqual(head["sha256"], hashlib.sha256(data).hexdigest())

    def test_material_grid_and_glb_preserve_all_four_colors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = generate_m1_artifacts(
                iron_man_plan(), Path(directory) / "result"
            )
            material_grid = json.loads(
                gzip.decompress(artifacts.material_grid_path.read_bytes())
            )
            self.assertEqual(len(material_grid["palette"]), 4)

            document = _glb_json(artifacts.preview_path.read_bytes())
            self.assertEqual(len(document["materials"]), 4)
            self.assertTrue(
                any(mesh["name"] == "head_materials" for mesh in document["meshes"])
            )
            head_accessor = document["accessors"][
                document["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
            ]
            self.assertLess(head_accessor["min"][1], 0.0)

    def test_protected_relief_is_clipped_and_reported(self) -> None:
        head = CANONICAL_PARTS[0]
        rows, columns = face_detail_shape(head, SurfaceFace.BOTTOM)
        surface = SurfaceMap(
            SurfaceFace.BOTTOM,
            tuple(tuple(1 for _ in range(columns)) for _ in range(rows)),
            tuple(tuple(0 for _ in range(columns)) for _ in range(rows)),
        )
        plan = CharacterPlan(
            "1.0",
            "protected test",
            (PaletteEntry(0, "gray", "#777777"),),
            (PartAppearance("head", (surface,)),),
        )
        with tempfile.TemporaryDirectory() as directory:
            artifacts = generate_m1_artifacts(plan, Path(directory) / "result")
            report = json.loads(
                artifacts.validation_report_path.read_text(encoding="utf-8")
            )
            head_report = next(
                part for part in report["parts"] if part["name"] == "head"
            )
            self.assertGreater(head_report["clipped_protected_pixels"], 0)
            processed = json.loads(
                artifacts.character_plan_path.read_text(encoding="utf-8")
            )
            head_surface = processed["parts"][0]["surfaces"][0]
            self.assertTrue(
                all(level == 0 for row in head_surface["relief"] for level in row)
            )

    def test_complete_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "first", root / "second"
            generate_m1_artifacts(spider_man_plan(), first)
            generate_m1_artifacts(spider_man_plan(), second)

            self.assertEqual(_files(first), _files(second))

    def test_accepts_a_bounded_custom_base_shape(self) -> None:
        head = CANONICAL_PARTS[0]
        shape = compile_part_relief(head, ())
        occupancy = [[list(row) for row in layer] for layer in shape.occupancy]
        occupancy[41][2][2] = False
        custom = type(shape)(
            tuple(
                tuple(tuple(value for value in row) for row in layer)
                for layer in occupancy
            ),
            shape.origin_detail_xyz,
        )
        with tempfile.TemporaryDirectory() as directory:
            artifacts = generate_m1_artifacts(
                CharacterPlan(
                    "1.0",
                    "custom head",
                    (PaletteEntry(0, "gray", "#777777"),),
                    (),
                ),
                Path(directory) / "result",
                part_shapes={"head": custom},
            )
            report = json.loads(artifacts.validation_report_path.read_text())
            head_report = next(
                part for part in report["parts"] if part["name"] == "head"
            )
            self.assertEqual(head_report["signed_volume_detail_cells"], 40**3 - 1)


def _files(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _glb_json(data: bytes) -> dict[str, object]:
    json_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON":
        raise AssertionError("missing GLB JSON chunk")
    return json.loads(data[20 : 20 + json_length].decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
