from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lalo import generate_m1_artifacts, validate_artifact_directory
from lalo.fixtures import spider_man_plan


class ArtifactDirectoryValidationTests(unittest.TestCase):
    def test_missing_directory_returns_a_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = validate_artifact_directory(Path(directory) / "missing")

        self.assertEqual(result.errors, ("missing_artifact_directory",))

    def test_accepts_a_fresh_complete_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            generate_m1_artifacts(spider_man_plan(), output)

            result = validate_artifact_directory(output)

            self.assertTrue(result.valid, result.errors)

    def test_detects_stl_tampering_and_stale_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            generate_m1_artifacts(spider_man_plan(), output)
            head = output / "stl" / "head.stl"
            head.write_bytes(head.read_bytes() + b"tampered")

            result = validate_artifact_directory(output)

            self.assertFalse(result.valid)
            self.assertIn("size_mismatch:head", result.errors)
            self.assertIn("hash_mismatch:head", result.errors)
            self.assertIn("invalid_result_zip", result.errors)

    def test_rejects_an_unsafe_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            generate_m1_artifacts(spider_man_plan(), output)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["parts"][0]["file"] = "../head.stl"
            manifest_path.write_text(json.dumps(manifest))

            result = validate_artifact_directory(output)

            self.assertFalse(result.valid)
            self.assertIn("invalid_manifest_part:head", result.errors)


if __name__ == "__main__":
    unittest.main()
