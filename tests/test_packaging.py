from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from lalo.packaging import write_artifact_zip


class ArtifactPackagingTests(unittest.TestCase):
    def test_packages_sorted_files_without_packaging_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "stl").mkdir()
            (root / "stl" / "head.stl").write_bytes(b"head")
            (root / "manifest.json").write_text("{}")

            output = write_artifact_zip(root)

            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), ["manifest.json", "stl/head.stl"])
                self.assertNotIn("result.zip", archive.namelist())

    def test_identical_inputs_produce_identical_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.txt").write_text("same")

            first = write_artifact_zip(root).read_bytes()
            second = write_artifact_zip(root).read_bytes()

            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
