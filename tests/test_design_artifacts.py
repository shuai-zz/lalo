from __future__ import annotations

import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image
from test_design import _result

from lalo import (
    CharacterSheet,
    DesignerCapabilities,
    DesignRaster,
    DesignRequest,
    DesignView,
    DesignViewName,
    write_design_artifacts,
)


class DesignArtifactTests(unittest.TestCase):
    def test_writes_complete_redacted_package_atomically(self) -> None:
        request = DesignRequest("private character description", seed=5)
        result = _png_result()
        capabilities = DesignerCapabilities(True, True, False, False)
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "design"

            write_design_artifacts(output, request, result, capabilities)

            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "identity.json",
                    "sheet.png",
                    "front.png",
                    "back.png",
                    "left.png",
                    "right.png",
                    "design-metadata.json",
                },
            )
            metadata_text = (output / "design-metadata.json").read_text()
            self.assertNotIn(request.prompt, metadata_text)
            metadata = json.loads(metadata_text)
            self.assertEqual(metadata["design"]["effective_seed"], 7)
            self.assertEqual(metadata["input"]["has_image"], False)

    def test_refuses_to_replace_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "design"
            output.mkdir()
            marker = output / "mine.txt"
            marker.write_text("keep")

            with self.assertRaises(FileExistsError):
                write_design_artifacts(
                    output,
                    DesignRequest("hero"),
                    _png_result(),
                    DesignerCapabilities(True, True, False, False),
                )

            self.assertEqual(marker.read_text(), "keep")


def _png_result():
    views = []
    colors = ("red", "blue", "green", "yellow")
    for name, color in zip(DesignViewName, colors):
        image = Image.new("RGB", (16, 32), color)
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")
        views.append(
            DesignView(
                name,
                DesignRaster(encoded.getvalue(), "image/png", 16, 32),
            )
        )
    return replace(_result(subject_count=None), sheet=CharacterSheet(tuple(views)))


if __name__ == "__main__":
    unittest.main()
