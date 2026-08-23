"""Concrete OpenAI adapter for the two-dimensional design stage."""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from typing import Any, Protocol

from PIL import Image

from lalo.appearance import PaletteEntry
from lalo.design import (
    CharacterRegion,
    CharacterSheet,
    DesignerCapabilities,
    DesignRaster,
    DesignRequest,
    DesignResult,
    DesignView,
    DesignViewName,
    FeatureImportance,
    IdentityFeature,
    IdentitySpec,
    InvalidDesignerOutput,
)
from lalo.openai_planner import ResponsesTransport, _output_text, _strict_object


class ImagesTransport(Protocol):
    def generate_image(
        self,
        payload: dict[str, Any],
        image: bytes | None = None,
        image_media_type: str | None = None,
    ) -> dict[str, Any]: ...


class DesignTransport(ResponsesTransport, ImagesTransport, Protocol):
    """The two OpenAI calls required by the design pipeline."""


@dataclass(frozen=True)
class OpenAIDesigner:
    """Extract identity, render one sheet, and split it into canonical views."""

    vision_model: str
    image_model: str
    transport: DesignTransport
    zero_retention: bool = False

    def __post_init__(self) -> None:
        if not self.vision_model.strip() or not self.image_model.strip():
            raise ValueError("OpenAI design models must not be empty")
        if not isinstance(self.zero_retention, bool):
            raise TypeError("zero_retention must be a boolean")

    @property
    def capabilities(self) -> DesignerCapabilities:
        return DesignerCapabilities(True, True, False, self.zero_retention)

    def design(
        self, request: DesignRequest, *, correction: str | None = None
    ) -> DesignResult:
        try:
            identity_response = self.transport.create_response(
                self._identity_payload(request, correction)
            )
            envelope = _identity_envelope(_output_text(identity_response))
            image_response = self.transport.generate_image(
                self._image_payload(request, envelope["identity"]),
                request.image.data if request.image is not None else None,
                request.image.media_type if request.image is not None else None,
            )
            sheet = _split_sheet(_image_bytes(image_response))
            model_version = _required_string(
                image_response, "model", fallback=self.image_model
            )
        except InvalidDesignerOutput:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidDesignerOutput(str(exc)) from exc
        return DesignResult(
            identity=envelope["identity"],
            sheet=sheet,
            effective_seed=request.seed,
            provider="openai",
            model=self.image_model,
            model_version=model_version,
            subject_count=envelope["subject_count"],
        )

    def _identity_payload(
        self, request: DesignRequest, correction: str | None
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": request.prompt}]
        if request.image is not None:
            encoded = base64.b64encode(request.image.data).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{request.image.media_type};base64,{encoded}",
                    "detail": "high",
                }
            )
        instructions = _identity_instructions()
        if correction:
            instructions += f"\nCorrect these validation issues: {correction}"
        return {
            "model": self.vision_model,
            "store": False,
            "instructions": instructions,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "lalo_identity",
                    "strict": True,
                    "schema": openai_identity_schema(),
                }
            },
        }

    def _image_payload(
        self, request: DesignRequest, identity: IdentitySpec
    ) -> dict[str, Any]:
        return {
            "model": self.image_model,
            "prompt": _sheet_prompt(request.prompt, identity),
            "size": "1536x1024",
            "quality": "high",
            "output_format": "png",
        }


def openai_identity_schema() -> dict[str, Any]:
    feature = _strict_object(
        {
            "name": {"type": "string", "minLength": 1},
            "region": {"type": "string", "enum": [r.value for r in CharacterRegion]},
            "description": {"type": "string", "minLength": 1},
            "importance": {
                "type": "string",
                "enum": [value.value for value in FeatureImportance],
            },
        }
    )
    palette = _strict_object(
        {
            "id": {"type": "integer", "minimum": 0, "maximum": 3},
            "name": {"type": "string", "minLength": 1},
            "srgb": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
        }
    )
    identity = _strict_object(
        {
            "schema_version": {"type": "string", "const": "1.0"},
            "name": {"type": "string", "minLength": 1},
            "summary": {"type": "string", "minLength": 1},
            "palette": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": palette,
            },
            "features": {"type": "array", "minItems": 1, "items": feature},
        }
    )
    return _strict_object(
        {
            "subject_count": {
                "anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]
            },
            "identity": identity,
        }
    )


def _identity_envelope(payload: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid identity JSON: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"subject_count", "identity"}:
        raise ValueError("identity envelope must contain subject_count and identity")
    count = value["subject_count"]
    if count is not None and (
        isinstance(count, bool) or not isinstance(count, int) or count < 0
    ):
        raise ValueError("subject_count must be a non-negative integer or null")
    raw = value["identity"]
    if not isinstance(raw, dict):
        raise TypeError("identity must be an object")
    try:
        palette = tuple(PaletteEntry(**entry) for entry in raw["palette"])
        features = tuple(
            IdentityFeature(
                name=item["name"],
                region=CharacterRegion(item["region"]),
                description=item["description"],
                importance=FeatureImportance(item["importance"]),
            )
            for item in raw["features"]
        )
        identity = IdentitySpec(
            schema_version=raw["schema_version"],
            name=raw["name"],
            summary=raw["summary"],
            palette=palette,
            features=features,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid identity: {exc}") from exc
    return {"subject_count": count, "identity": identity}


def _image_bytes(response: dict[str, Any]) -> bytes:
    data = response.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise ValueError("image response must contain exactly one data item")
    encoded = data[0].get("b64_json")
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("image response data must contain b64_json")
    try:
        return base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("image response b64_json is invalid") from exc


def _split_sheet(data: bytes) -> CharacterSheet:
    try:
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGB")
    except Exception as exc:
        raise ValueError("generated sheet is not a readable image") from exc
    if image.width % 4 or image.width < 4 or image.height < 1:
        raise ValueError("generated sheet width must divide evenly into four panels")
    panel_width = image.width // 4
    views: list[DesignView] = []
    for index, name in enumerate(DesignViewName):
        panel = image.crop(
            (index * panel_width, 0, (index + 1) * panel_width, image.height)
        )
        output = io.BytesIO()
        panel.save(output, format="PNG")
        views.append(
            DesignView(
                name,
                DesignRaster(output.getvalue(), "image/png", panel_width, image.height),
            )
        )
    return CharacterSheet(tuple(views))


def _identity_instructions() -> str:
    return (
        "Extract one recognizable humanoid character identity for a Minecraft-style "
        "block figure. The user's text overrides conflicting image details. If an "
        "image exists, count people or characters; otherwise subject_count is null. "
        "Choose at most four printable colors and concise features visible from "
        "front, back, left, or right. Do not invent joints, geometry, or backgrounds."
    )


def _sheet_prompt(user_prompt: str, identity: IdentitySpec) -> str:
    colors = ", ".join(f"{p.name} {p.srgb}" for p in identity.palette)
    features = "; ".join(
        f"{f.region.value}: {f.description}" for f in identity.features
    )
    return (
        "Create one production character design sheet as four equal vertical panels "
        "in this exact left-to-right order: FRONT, BACK, LEFT, RIGHT. Show the exact "
        "same neutral-standing Minecraft-style humanoid, centered and full body in "
        "each panel, orthographic camera, identical scale and proportions, separated "
        "legs, block-built body, crisp pixel/voxel-fittable details, flat neutral "
        "background, no perspective, no props, no extra characters, and no text or "
        "labels. Preserve side-specific and rear details. "
        f"User intent: {user_prompt}. Identity: {identity.summary}. "
        f"Palette: {colors}. Required visual features: {features}."
    )


def _required_string(value: dict[str, Any], key: str, *, fallback: str) -> str:
    result = value.get(key, fallback)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"image response {key} must be a non-empty string")
    return result
