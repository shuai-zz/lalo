from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lalo.body import CANONICAL_PARTS
from lalo.m0 import generate_m0_artifacts


class M0ArtifactTests(unittest.TestCase):
    def test_generates_exact_complete_artifact_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            artifacts = generate_m0_artifacts(output)

            expected = {
                *(f"stl/{part.name}.stl" for part in CANONICAL_PARTS),
                "manifest.json",
                "preview.glb",
                "validation_report.json",
            }
            actual = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, expected)
            self.assertEqual(len(artifacts.stl_paths), 14)
            self.assertEqual(artifacts.manifest_path, output / "manifest.json")
            self.assertEqual(artifacts.preview_path, output / "preview.glb")

    def test_manifest_paths_and_hashes_match_stl_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            artifacts = generate_m0_artifacts(output)
            manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["height_mm"], 80.0)
            for entry in manifest["parts"]:
                self.assertTrue(entry["file"].startswith("stl/"))
                data = (output / entry["file"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())

    def test_validation_report_passes_all_fourteen_parts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = generate_m0_artifacts(Path(directory) / "result")
            report = json.loads(
                artifacts.validation_report_path.read_text(encoding="utf-8")
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["parts"]), 14)
            self.assertTrue(all(part["valid"] for part in report["parts"]))
            self.assertTrue(
                all(part["signed_volume_mm3"] > 0 for part in report["parts"])
            )

    def test_full_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            generate_m0_artifacts(first)
            generate_m0_artifacts(second)

            first_files = {
                path.relative_to(first): path.read_bytes()
                for path in first.rglob("*")
                if path.is_file()
            }
            second_files = {
                path.relative_to(second): path.read_bytes()
                for path in second.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first_files, second_files)

    def test_rejects_non_empty_output_without_modification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "must be empty"):
                generate_m0_artifacts(directory)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertEqual(tuple(Path(directory).iterdir()), (marker,))


if __name__ == "__main__":
    unittest.main()
