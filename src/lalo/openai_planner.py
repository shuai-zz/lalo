"""OpenAI Responses API adapter for constrained multimodal planning."""

from __future__ import annotations

import base64
import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from lalo.body import CANONICAL_PARTS
from lalo.plan_json import CharacterPlanCodecError, character_plan_from_dict
from lalo.planner import (
    InvalidPlannerOutput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
)
from lalo.relief import DETAIL_CELLS_PER_MASTER


class ResponsesTransport(Protocol):
    """Minimal replaceable transport used by the OpenAI adapter."""

    def create_response(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OpenAIHTTPTransport:
    """Small standard-library transport for ``POST /v1/responses``."""

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("OpenAI api_key must not be empty")
        if not self.base_url.startswith(("https://", "http://")):
            raise ValueError("OpenAI base_url must be an HTTP(S) URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

    def create_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/responses",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            decoded = json.load(response)
        if not isinstance(decoded, dict):
            raise ValueError("OpenAI response must be a JSON object")
        return decoded


@dataclass(frozen=True)
class OpenAIPlanner:
    """Generate locally validated CharacterPlans with the Responses API."""

    model: str
    transport: ResponsesTransport
    zero_retention: bool = False

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("OpenAI model must not be empty")
        if not isinstance(self.zero_retention, bool):
            raise TypeError("zero_retention must be a boolean")

    @property
    def capabilities(self) -> PlannerCapabilities:
        return PlannerCapabilities(
            supports_images=True,
            supports_structured_output=True,
            supports_seed=False,
            supports_zero_retention=self.zero_retention,
        )

    def plan(
        self, request: PlanRequest, *, correction: str | None = None
    ) -> PlanResult:
        payload = self._request_payload(request, correction)
        response = self.transport.create_response(payload)
        try:
            envelope = _decode_envelope(_output_text(response))
            response_model = _required_string(response, "model", "response")
        except (CharacterPlanCodecError, TypeError, ValueError) as exc:
            raise InvalidPlannerOutput(str(exc)) from exc
        return PlanResult(
            plan=envelope["plan"],
            effective_seed=request.seed,
            provider="openai",
            model=self.model,
            model_version=response_model,
            subject_count=envelope["subject_count"],
        )

    def _request_payload(
        self, request: PlanRequest, correction: str | None
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [
            {"type": "input_text", "text": request.prompt}
        ]
        if request.image is not None:
            encoded = base64.b64encode(request.image.data).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": (
                        f"data:{request.image.media_type};base64,{encoded}"
                    ),
                    "detail": "high",
                }
            )
        instructions = _developer_instructions()
        if correction is not None:
            instructions += (
                "\nYour previous output failed local validation. Correct only these "
                f"issues and return the full envelope again: {correction}"
            )
        return {
            "model": self.model,
            "store": False,
            "instructions": instructions,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "lalo_character_plan",
                    "strict": True,
                    "schema": openai_planner_schema(),
                }
            },
        }


def openai_planner_schema() -> dict[str, Any]:
    """Return the strict provider envelope schema used by Responses API."""

    integer_grid = {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "integer"},
        },
    }
    return _strict_object(
        {
            "subject_count": {
                "anyOf": [
                    {"type": "integer", "minimum": 0},
                    {"type": "null"},
                ]
            },
            "plan": _strict_object(
                {
                    "schema_version": {"type": "string", "const": "1.0"},
                    "name": {"type": "string", "minLength": 1},
                    "palette": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": _strict_object(
                            {
                                "id": {"type": "integer", "minimum": 0, "maximum": 3},
                                "name": {"type": "string", "minLength": 1},
                                "srgb": {
                                    "type": "string",
                                    "pattern": "^#[0-9A-Fa-f]{6}$",
                                },
                            }
                        ),
                    },
                    "parts": {
                        "type": "array",
                        "items": _strict_object(
                            {
                                "part_name": {
                                    "type": "string",
                                    "enum": [part.name for part in CANONICAL_PARTS],
                                },
                                "surfaces": {
                                    "type": "array",
                                    "items": _strict_object(
                                        {
                                            "face": {
                                                "type": "string",
                                                "enum": [
                                                    "front",
                                                    "back",
                                                    "left",
                                                    "right",
                                                    "top",
                                                    "bottom",
                                                ],
                                            },
                                            "relief": integer_grid,
                                            "materials": integer_grid,
                                        }
                                    ),
                                },
                                "silhouette_features": {
                                    "type": "array",
                                    "items": _strict_object(
                                        {
                                            "origin_detail_xyz": _integer_triple(),
                                            "size_detail_xyz": _integer_triple(
                                                minimum=1, maximum=10
                                            ),
                                            "material_id": {
                                                "type": "integer",
                                                "minimum": 0,
                                                "maximum": 3,
                                            },
                                        }
                                    ),
                                },
                            }
                        ),
                    },
                }
            ),
        }
    )


def _strict_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _integer_triple(
    *, minimum: int | None = None, maximum: int | None = None
) -> dict[str, Any]:
    item: dict[str, Any] = {"type": "integer"}
    if minimum is not None:
        item["minimum"] = minimum
    if maximum is not None:
        item["maximum"] = maximum
    return {"type": "array", "minItems": 3, "maxItems": 3, "items": item}


def _developer_instructions() -> str:
    dimensions = "; ".join(
        f"{part.name}={part.size_xyz}" for part in CANONICAL_PARTS
    )
    return (
        "Create one Minecraft-style humanoid CharacterPlan, never mesh or code. "
        "The user's text instruction is authoritative and MUST override any "
        "conflicting visual cue in the image. If an image is present, report the "
        "number of people or characters as subject_count; otherwise use null. "
        "Use at most four palette colors. Relief values are -2..2 and material "
        "IDs are 0..3 and must reference the palette. Detail maps use "
        f"{DETAIL_CELLS_PER_MASTER} cells per master voxel. Canonical part "
        f"dimensions (x,y,z) are: {dimensions}. Front/back map shape is "
        "(z*5,x*5), left/right is (z*5,y*5), and top/bottom is (y*5,x*5). "
        "Include only useful faces, keep recognizable eyes/hair/glasses/clothing "
        "cues, and keep relief simple enough for 0.4 mm nozzle FDM printing."
    )


def _output_text(response: dict[str, Any]) -> str:
    output = response.get("output")
    if not isinstance(output, list):
        raise ValueError("response.output must be an array")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "output_text":
                text = block.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if len(texts) != 1:
        raise ValueError("response must contain exactly one output_text block")
    return texts[0]


def _decode_envelope(payload: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CharacterPlanCodecError(f"invalid provider envelope JSON: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"subject_count", "plan"}:
        raise CharacterPlanCodecError(
            "provider envelope must contain only subject_count and plan"
        )
    subject_count = value["subject_count"]
    if subject_count is not None and (
        isinstance(subject_count, bool)
        or not isinstance(subject_count, int)
        or subject_count < 0
    ):
        raise CharacterPlanCodecError(
            "provider envelope subject_count must be a non-negative integer or null"
        )
    return {
        "subject_count": subject_count,
        "plan": character_plan_from_dict(value["plan"]),
    }


def _required_string(value: dict[str, Any], key: str, path: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{path}.{key} must be a non-empty string")
    return result
