import unittest

from lalo.fixtures import spider_man_plan
from lalo.planner import (
    ImageInput,
    InvalidPlannerOutput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
)
from lalo.planning import (
    SingleSubjectError,
    UnsupportedPlannerError,
    plan_character,
)


class RecordingPlanner:
    def __init__(
        self,
        outcomes: list[PlanResult | Exception],
        capabilities: PlannerCapabilities | None = None,
    ) -> None:
        self.capabilities = capabilities or PlannerCapabilities(True, True, True, True)
        self.outcomes = outcomes
        self.calls: list[tuple[PlanRequest, str | None]] = []

    def plan(
        self, request: PlanRequest, *, correction: str | None = None
    ) -> PlanResult:
        self.calls.append((request, correction))
        outcome = self.outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def result(subject_count: int | None = None) -> PlanResult:
    return PlanResult(
        plan=spider_man_plan(),
        effective_seed=42,
        provider="fixture",
        model="planner",
        model_version="1",
        subject_count=subject_count,
    )


class PlanningOrchestrationTests(unittest.TestCase):
    def test_text_only_request_does_not_require_subject_count(self) -> None:
        planner = RecordingPlanner([result()])

        self.assertEqual(plan_character(PlanRequest("蜘蛛侠"), planner), result())

    def test_one_subject_image_succeeds(self) -> None:
        request = PlanRequest(
            "保留黑框眼镜，穿红色外套",
            ImageInput(b"image", "image/jpeg"),
            seed=42,
        )
        planner = RecordingPlanner([result(1)])

        self.assertEqual(plan_character(request, planner).subject_count, 1)
        self.assertIs(planner.calls[0][0], request)

    def test_zero_multiple_and_missing_subject_counts_are_not_retried(self) -> None:
        request = PlanRequest("make a block figure", ImageInput(b"image", "image/png"))
        for count in (None, 0, 2):
            planner = RecordingPlanner([result(count)])
            with self.assertRaises(SingleSubjectError) as raised:
                plan_character(request, planner)
            self.assertEqual(raised.exception.subject_count, count)
            self.assertEqual(len(planner.calls), 1)

    def test_invalid_output_gets_one_correction_using_same_request(self) -> None:
        request = PlanRequest("blue jacket overrides the photo", seed=9)
        planner = RecordingPlanner(
            [InvalidPlannerOutput("$.palette is missing"), result()]
        )

        plan_character(request, planner)

        self.assertEqual(len(planner.calls), 2)
        self.assertIs(planner.calls[0][0], request)
        self.assertIs(planner.calls[1][0], request)
        self.assertIsNone(planner.calls[0][1])
        self.assertEqual(planner.calls[1][1], "$.palette is missing")

    def test_second_invalid_output_and_unrelated_errors_propagate(self) -> None:
        request = PlanRequest("hero")
        planner = RecordingPlanner(
            [InvalidPlannerOutput("first"), InvalidPlannerOutput("second")]
        )
        with self.assertRaisesRegex(InvalidPlannerOutput, "second"):
            plan_character(request, planner)
        self.assertEqual(len(planner.calls), 2)

        planner = RecordingPlanner([RuntimeError("network")])
        with self.assertRaisesRegex(RuntimeError, "network"):
            plan_character(request, planner)
        self.assertEqual(len(planner.calls), 1)

    def test_required_capabilities_are_checked_before_provider_call(self) -> None:
        image_request = PlanRequest("hero", ImageInput(b"image", "image/webp"))
        cases = (
            PlannerCapabilities(False, True, True, True),
            PlannerCapabilities(True, True, True, False),
        )
        for capabilities in cases:
            planner = RecordingPlanner([result(1)], capabilities)
            with self.assertRaises(UnsupportedPlannerError):
                plan_character(image_request, planner)
            self.assertEqual(planner.calls, [])

    def test_non_native_structured_output_is_locally_validated(self) -> None:
        planner = RecordingPlanner(
            [result()], PlannerCapabilities(True, False, True, True)
        )

        self.assertEqual(plan_character(PlanRequest("hero"), planner), result())


if __name__ == "__main__":
    unittest.main()
