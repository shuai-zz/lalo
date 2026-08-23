from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from test_design import _FakeDesigner
from test_design_artifacts import _png_result

from lalo.cli import main


class _PNGDesigner(_FakeDesigner):
    def __init__(self, *, subject_count=None):
        super().__init__(subject_count=subject_count)
        self.requests = []

    def design(self, request, *, correction=None):
        self.corrections.append(correction)
        self.requests.append(request)
        return replace(_png_result(), subject_count=self.subject_count)


class DesignCLITests(unittest.TestCase):
    def test_design_command_writes_inspectable_views(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "hero"
            stdout = StringIO()
            with (
                patch(
                    "lalo.cli._openai_designer_from_environment",
                    return_value=_PNGDesigner(subject_count=None),
                ),
                redirect_stdout(stdout),
            ):
                status = main(
                    [
                        "design",
                        "--prompt",
                        "一个方块英雄",
                        "--seed",
                        "12",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(status, 0)
            self.assertTrue((output / "identity.json").is_file())
            self.assertTrue((output / "sheet.png").is_file())
            self.assertEqual(stdout.getvalue().strip(), str(output))

    def test_provider_failure_is_redacted(self) -> None:
        stderr = StringIO()
        with (
            tempfile.TemporaryDirectory() as parent,
            patch(
                "lalo.cli._openai_designer_from_environment",
                side_effect=ValueError("secret API response body"),
            ),
            redirect_stderr(stderr),
        ):
            status = main(
                ["design", "--prompt", "private prompt", "--output", f"{parent}/out"]
            )

        self.assertEqual(status, 1)
        self.assertNotIn("secret", stderr.getvalue())
        self.assertNotIn("private prompt", stderr.getvalue())
        self.assertIn("ValueError", stderr.getvalue())

    def test_optional_image_is_passed_in_memory(self) -> None:
        designer = _PNGDesigner(subject_count=1)
        with tempfile.TemporaryDirectory() as parent:
            image = Path(parent) / "person.png"
            image.write_bytes(b"private-image")
            with (
                patch(
                    "lalo.cli._openai_designer_from_environment", return_value=designer
                ),
                redirect_stdout(StringIO()),
            ):
                status = main(
                    [
                        "design",
                        "--prompt",
                        "保留眼镜",
                        "--image",
                        str(image),
                        "--output",
                        f"{parent}/out",
                    ]
                )

        self.assertEqual(status, 0)
        self.assertEqual(designer.requests[0].image.data, b"private-image")
        self.assertEqual(designer.requests[0].image.media_type, "image/png")


if __name__ == "__main__":
    unittest.main()
