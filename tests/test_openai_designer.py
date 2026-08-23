from __future__ import annotations

import base64
import io
import json
import unittest

from PIL import Image

from lalo import DesignRequest, ImageInput, InvalidDesignerOutput
from lalo.openai_designer import OpenAIDesigner, openai_identity_schema


class RecordingTransport:
    def __init__(self, identity: dict[str, object], image: dict[str, object]) -> None:
        self.identity = identity
        self.image = image
        self.response_payloads: list[dict[str, object]] = []
        self.image_calls: list[tuple[dict[str, object], bytes | None, str | None]] = []

    def create_response(self, payload: dict[str, object]) -> dict[str, object]:
        self.response_payloads.append(payload)
        return self.identity

    def generate_image(
        self,
        payload: dict[str, object],
        image: bytes | None = None,
        image_media_type: str | None = None,
    ) -> dict[str, object]:
        self.image_calls.append((payload, image, image_media_type))
        return self.image


class OpenAIDesignerTests(unittest.TestCase):
    def test_text_request_extracts_identity_and_splits_four_views(self) -> None:
        transport = RecordingTransport(_identity_response(), _image_response())
        designer = OpenAIDesigner("gpt-5.4", "gpt-image-2", transport)

        result = designer.design(DesignRequest("一个戴眼镜的方块小人", seed=9))

        identity_payload = transport.response_payloads[0]
        self.assertIs(identity_payload["store"], False)
        self.assertEqual(identity_payload["text"]["format"]["type"], "json_schema")
        image_payload, source, media_type = transport.image_calls[0]
        self.assertIsNone(source)
        self.assertIsNone(media_type)
        self.assertEqual(image_payload["model"], "gpt-image-2")
        self.assertIn("FRONT, BACK, LEFT, RIGHT", image_payload["prompt"])
        self.assertEqual(
            [v.name.value for v in result.sheet.views],
            ["front", "back", "left", "right"],
        )
        self.assertEqual(
            {(v.image.width, v.image.height) for v in result.sheet.views}, {(16, 32)}
        )
        self.assertEqual(result.effective_seed, 9)
        self.assertFalse(designer.capabilities.supports_seed)

    def test_photo_stays_in_memory_for_both_provider_calls(self) -> None:
        transport = RecordingTransport(
            _identity_response(subject_count=1), _image_response()
        )
        designer = OpenAIDesigner("vision", "image", transport, zero_retention=True)
        photo = b"private-photo"

        result = designer.design(
            DesignRequest("保留我的眼镜", ImageInput(photo, "image/jpeg"))
        )

        content = transport.response_payloads[0]["input"][0]["content"]
        self.assertTrue(content[1]["image_url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(transport.image_calls[0][1:], (photo, "image/jpeg"))
        self.assertEqual(result.subject_count, 1)
        self.assertTrue(designer.capabilities.supports_zero_retention)

    def test_invalid_identity_or_sheet_is_correctable_output(self) -> None:
        invalid = RecordingTransport(
            {"model": "vision", "output": []}, _image_response()
        )
        with self.assertRaisesRegex(InvalidDesignerOutput, "output_text"):
            OpenAIDesigner("vision", "image", invalid).design(DesignRequest("hero"))

        invalid_image = RecordingTransport(_identity_response(), {"data": []})
        with self.assertRaisesRegex(InvalidDesignerOutput, "exactly one"):
            OpenAIDesigner("vision", "image", invalid_image).design(
                DesignRequest("hero")
            )

    def test_identity_schema_is_strict(self) -> None:
        schema = openai_identity_schema()
        self.assertIs(schema["additionalProperties"], False)
        identity = schema["properties"]["identity"]
        self.assertIs(identity["additionalProperties"], False)
        self.assertIs(
            identity["properties"]["features"]["items"]["additionalProperties"], False
        )


def _identity_response(*, subject_count: int | None = None) -> dict[str, object]:
    envelope = {
        "subject_count": subject_count,
        "identity": {
            "schema_version": "1.0",
            "name": "glasses hero",
            "summary": "mustard hoodie, dark hair, round glasses",
            "palette": [
                {"id": 0, "name": "mustard", "srgb": "#C7922B"},
                {"id": 1, "name": "teal", "srgb": "#237C7A"},
            ],
            "features": [
                {
                    "name": "round glasses",
                    "region": "head",
                    "description": "large round dark-rim glasses",
                    "importance": "primary",
                }
            ],
        },
    }
    return {
        "model": "gpt-5.4-2026-08-01",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(envelope)}],
            }
        ],
    }


def _image_response() -> dict[str, object]:
    image = Image.new("RGB", (64, 32), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return {
        "model": "gpt-image-2-2026-04-21",
        "data": [{"b64_json": base64.b64encode(output.getvalue()).decode("ascii")}],
    }


if __name__ == "__main__":
    unittest.main()
