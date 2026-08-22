import unittest

from lalo.fixtures import spider_man_plan
from lalo.planner import (
    CharacterPlanner,
    ImageInput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
)


class FakePlanner:
    capabilities = PlannerCapabilities(True, True, True, True)

    def plan(self, request: PlanRequest) -> PlanResult:
        return PlanResult(
            plan=spider_man_plan(),
            effective_seed=request.seed,
            provider="fixture",
            model="spider",
            model_version="1",
        )


class PlannerContractTests(unittest.TestCase):
    def test_request_accepts_text_and_supported_in_memory_image(self) -> None:
        image = ImageInput(data=b"not-decoded-by-the-contract", media_type="image/png")

        request = PlanRequest(prompt="把我变成方块英雄", image=image, seed=42)

        self.assertEqual(request.image, image)
        self.assertEqual(request.seed, 42)

    def test_image_rejects_empty_data_and_unsupported_media_type(self) -> None:
        with self.assertRaises(ValueError):
            ImageInput(data=b"", media_type="image/png")
        with self.assertRaises(ValueError):
            ImageInput(data=b"image", media_type="image/gif")

    def test_request_rejects_empty_prompt_and_non_integer_seed(self) -> None:
        with self.assertRaises(ValueError):
            PlanRequest(prompt="  ")
        with self.assertRaises(TypeError):
            PlanRequest(prompt="hero", seed=True)

    def test_result_requires_reproducibility_identifiers(self) -> None:
        with self.assertRaises(ValueError):
            PlanResult(
                plan=spider_man_plan(),
                effective_seed=7,
                provider="fixture",
                model="spider",
                model_version="",
            )

    def test_capabilities_require_explicit_booleans(self) -> None:
        with self.assertRaises(TypeError):
            PlannerCapabilities(True, True, True, "yes")

    def test_structural_planner_implements_runtime_protocol(self) -> None:
        planner = FakePlanner()

        self.assertIsInstance(planner, CharacterPlanner)
        self.assertEqual(planner.plan(PlanRequest("Spider-Man", seed=9)).effective_seed, 9)


if __name__ == "__main__":
    unittest.main()
