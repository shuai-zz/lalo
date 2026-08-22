import json
import tempfile
import unittest
from pathlib import Path

from lalo.fixtures import spider_man_plan
from lalo.planner import (
    ImageInput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
)
from lalo.privacy import (
    planning_metadata,
    planning_metadata_json,
    transient_image_file,
)


def _result() -> PlanResult:
    return PlanResult(
        plan=spider_man_plan(),
        effective_seed=42,
        provider="openai",
        model="configured-model",
        model_version="resolved-model-version",
        subject_count=1,
    )


class PrivacyTests(unittest.TestCase):
    def test_transient_image_copy_is_removed_after_success(self) -> None:
        image = ImageInput(b"private-image-bytes", "image/png")
        request = PlanRequest("make me a figure", image)
        with tempfile.TemporaryDirectory() as parent:
            with transient_image_file(request, parent_directory=parent) as path:
                self.assertIsNotNone(path)
                assert path is not None
                self.assertEqual(path.read_bytes(), image.data)
                temporary_directory = path.parent
            self.assertFalse(path.exists())
            self.assertFalse(temporary_directory.exists())
            self.assertEqual(tuple(Path(parent).iterdir()), ())
        self.assertEqual(image.data, b"private-image-bytes")

    def test_transient_image_copy_is_removed_after_exception(self) -> None:
        request = PlanRequest("hero", ImageInput(b"private", "image/jpeg"))
        with tempfile.TemporaryDirectory() as parent:
            with self.assertRaisesRegex(RuntimeError, "provider failed"):
                with transient_image_file(request, parent_directory=parent) as path:
                    self.assertTrue(path and path.exists())
                    raise RuntimeError("provider failed")
            self.assertEqual(tuple(Path(parent).iterdir()), ())

    def test_text_only_request_does_not_create_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            with transient_image_file(
                PlanRequest("hero"), parent_directory=parent
            ) as path:
                self.assertIsNone(path)
            self.assertEqual(tuple(Path(parent).iterdir()), ())

    def test_metadata_is_reproducible_and_contains_no_private_values(self) -> None:
        prompt = "把照片里的我做成红色夹克方块人"
        image_bytes = b"secret-photo-content"
        request = PlanRequest(prompt, ImageInput(image_bytes, "image/webp"), seed=42)
        capabilities = PlannerCapabilities(True, True, False, True)

        encoded = planning_metadata_json(
            request, _result(), capabilities, generator_version="0.0.0"
        )
        document = json.loads(encoded)

        self.assertEqual(
            encoded,
            planning_metadata_json(
                request, _result(), capabilities, generator_version="0.0.0"
            ),
        )
        self.assertNotIn(prompt, encoded)
        self.assertNotIn(image_bytes.decode("ascii"), encoded)
        self.assertNotIn("Bearer", encoded)
        self.assertEqual(len(document["prompt_sha256"]), 64)
        self.assertEqual(document["planning"]["effective_seed"], 42)
        self.assertIs(document["planning"]["provider_supports_seed"], False)
        self.assertEqual(document["input"]["image_media_type"], "image/webp")
        self.assertEqual(document["character_plan"]["schema_version"], "1.0")
        self.assertEqual(document["generator_version"], "0.0.0")

    def test_metadata_changes_with_prompt_plan_or_generator_version(self) -> None:
        capabilities = PlannerCapabilities(True, True, True, True)
        first = planning_metadata(
            PlanRequest("Spider-Man"),
            _result(),
            capabilities,
            generator_version="1",
        )
        second = planning_metadata(
            PlanRequest("Iron Man"),
            _result(),
            capabilities,
            generator_version="2",
        )

        self.assertNotEqual(first["prompt_sha256"], second["prompt_sha256"])
        self.assertNotEqual(first["generator_version"], second["generator_version"])


if __name__ == "__main__":
    unittest.main()
