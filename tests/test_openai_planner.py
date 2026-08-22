import json
import unittest

from lalo.fixtures import spider_man_plan
from lalo.openai_planner import OpenAIPlanner, openai_planner_schema
from lalo.plan_json import character_plan_to_dict
from lalo.planner import ImageInput, InvalidPlannerOutput, PlanRequest


class RecordingTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.payloads: list[dict[str, object]] = []

    def create_response(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(payload)
        return self.response


def response(*, subject_count: int | None = None) -> dict[str, object]:
    envelope = {
        "subject_count": subject_count,
        "plan": character_plan_to_dict(spider_man_plan()),
    }
    return {
        "model": "gpt-4o-2024-11-20",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps(envelope)}
                ],
            }
        ],
    }


class OpenAIPlannerTests(unittest.TestCase):
    def test_text_request_uses_strict_stateless_responses_payload(self) -> None:
        transport = RecordingTransport(response())
        planner = OpenAIPlanner("gpt-4o-2024-11-20", transport)

        result = planner.plan(PlanRequest("生成蜘蛛侠", seed=42))

        payload = transport.payloads[0]
        self.assertEqual(payload["model"], "gpt-4o-2024-11-20")
        self.assertIs(payload["store"], False)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertIs(payload["text"]["format"]["strict"], True)
        self.assertIn("MUST override", payload["instructions"])
        self.assertEqual(result.plan, spider_man_plan())
        self.assertEqual(result.effective_seed, 42)
        self.assertEqual(result.model_version, "gpt-4o-2024-11-20")

    def test_image_is_an_in_memory_data_url_and_reports_one_subject(self) -> None:
        transport = RecordingTransport(response(subject_count=1))
        planner = OpenAIPlanner("vision-model", transport, zero_retention=True)
        request = PlanRequest(
            "keep my glasses", ImageInput(b"binary-image", "image/png")
        )

        result = planner.plan(request)

        content = transport.payloads[0]["input"][0]["content"]
        self.assertEqual(content[0], {"type": "input_text", "text": request.prompt})
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))
        self.assertEqual(result.subject_count, 1)
        self.assertTrue(planner.capabilities.supports_zero_retention)
        self.assertFalse(planner.capabilities.supports_seed)

    def test_correction_feedback_is_added_without_changing_user_prompt(self) -> None:
        transport = RecordingTransport(response())
        planner = OpenAIPlanner("model", transport)
        request = PlanRequest("blue clothing")

        planner.plan(request, correction="$.parts[0] is invalid")

        payload = transport.payloads[0]
        self.assertIn("$.parts[0] is invalid", payload["instructions"])
        self.assertEqual(
            payload["input"][0]["content"][0]["text"], "blue clothing"
        )

    def test_invalid_provider_envelope_is_a_correctable_output_error(self) -> None:
        invalid_responses = (
            {"model": "model", "output": []},
            {
                "model": "model",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "{}"}],
                    }
                ],
            },
        )
        for invalid in invalid_responses:
            with self.assertRaises(InvalidPlannerOutput):
                OpenAIPlanner("model", RecordingTransport(invalid)).plan(
                    PlanRequest("hero")
                )

    def test_schema_is_strict_at_every_object_level(self) -> None:
        schema = openai_planner_schema()

        self.assertIs(schema["additionalProperties"], False)
        plan = schema["properties"]["plan"]
        self.assertIs(plan["additionalProperties"], False)
        palette_item = plan["properties"]["palette"]["items"]
        self.assertIs(palette_item["additionalProperties"], False)


if __name__ == "__main__":
    unittest.main()
