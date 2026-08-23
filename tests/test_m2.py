import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lalo.fixtures import iron_man_plan, spider_man_plan
from lalo.m2 import generate_m2_artifacts
from lalo.plan_json import character_plan_from_json, character_plan_to_json
from lalo.planner import (
    ImageInput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
)
from lalo.planning import SingleSubjectError


class FixturePlanner:
    capabilities = PlannerCapabilities(True, True, True, True)

    def __init__(self, *, subject_count: int | None = None) -> None:
        self.subject_count = subject_count
        self.calls = 0

    def plan(
        self, request: PlanRequest, *, correction: str | None = None
    ) -> PlanResult:
        self.calls += 1
        plan = iron_man_plan() if "iron" in request.prompt.lower() else spider_man_plan()
        return PlanResult(
            plan=plan,
            effective_seed=request.seed,
            provider="fixture",
            model="golden-planner",
            model_version="1",
            subject_count=self.subject_count,
        )


class M2ArtifactTests(unittest.TestCase):
    def test_chinese_prompt_generates_complete_artifact_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            artifacts = generate_m2_artifacts(
                PlanRequest("生成一个蜘蛛侠方块人", seed=42),
                FixturePlanner(),
                output,
                generator_version="test-generator",
            )

            self.assertEqual(len(artifacts.m1.stl_paths), 14)
            self.assertTrue(artifacts.m1.preview_path.is_file())
            self.assertTrue(artifacts.provider_plan_path.is_file())
            self.assertTrue(artifacts.planning_metadata_path.is_file())
            self.assertEqual(
                character_plan_from_json(artifacts.provider_plan_path.read_bytes()),
                spider_man_plan(),
            )
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "stl",
                    "character_plan.json",
                    "provider_character_plan.json",
                    "material_grid.json.gz",
                    "manifest.json",
                    "preview.glb",
                    "validation_report.json",
                    "planning_metadata.json",
                    "result.zip",
                },
            )

    def test_english_image_request_records_safe_reproducibility_metadata(self) -> None:
        prompt = "Iron Man; use blue clothing even if the photo differs"
        image = ImageInput(b"private-photo", "image/jpeg")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            artifacts = generate_m2_artifacts(
                PlanRequest(prompt, image, seed=7),
                FixturePlanner(subject_count=1),
                output,
                generator_version="test-generator",
            )
            metadata_text = artifacts.planning_metadata_path.read_text("utf-8")
            metadata = json.loads(metadata_text)
            provider_plan = character_plan_to_json(iron_man_plan()).encode("utf-8")

            self.assertNotIn(prompt, metadata_text)
            self.assertNotIn("private-photo", metadata_text)
            self.assertEqual(metadata["planning"]["effective_seed"], 7)
            self.assertEqual(metadata["planning"]["provider"], "fixture")
            self.assertEqual(metadata["generator_version"], "test-generator")
            self.assertEqual(
                metadata["character_plan"]["file"],
                "provider_character_plan.json",
            )
            self.assertEqual(
                metadata["character_plan"]["sha256"],
                hashlib.sha256(provider_plan).hexdigest(),
            )
            self.assertEqual(
                metadata["character_plan"]["byte_size"], len(provider_plan)
            )
            self.assertEqual(artifacts.provider_plan_path.read_bytes(), provider_plan)

    def test_non_empty_output_is_rejected_before_planning(self) -> None:
        planner = FixturePlanner()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            output.mkdir()
            (output / "owned.txt").write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                generate_m2_artifacts(PlanRequest("hero"), planner, output)

            self.assertEqual(planner.calls, 0)
            self.assertEqual((output / "owned.txt").read_text("utf-8"), "keep")

    def test_subject_failure_leaves_no_output(self) -> None:
        request = PlanRequest("hero", ImageInput(b"photo", "image/png"))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"

            with self.assertRaises(SingleSubjectError):
                generate_m2_artifacts(
                    request, FixturePlanner(subject_count=2), output
                )

            self.assertFalse(output.exists())

    def test_complete_output_is_bitwise_deterministic(self) -> None:
        request = PlanRequest("Spider-Man", seed=99)
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            generate_m2_artifacts(
                request,
                FixturePlanner(),
                first,
                generator_version="test-generator",
            )
            generate_m2_artifacts(
                request,
                FixturePlanner(),
                second,
                generator_version="test-generator",
            )

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


if __name__ == "__main__":
    unittest.main()
