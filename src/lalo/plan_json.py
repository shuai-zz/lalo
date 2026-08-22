"""Strict local JSON codec for provider-produced character plans."""

from __future__ import annotations

import json
from typing import Any

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SilhouetteFeature,
    SurfaceFace,
    SurfaceMap,
)


class CharacterPlanCodecError(ValueError):
    """Provider JSON does not match the local CharacterPlan contract."""


def character_plan_to_dict(plan: CharacterPlan) -> dict[str, Any]:
    """Return the canonical JSON-compatible representation of a plan."""

    return {
        "schema_version": plan.schema_version,
        "name": plan.name,
        "palette": [
            {"id": entry.id, "name": entry.name, "srgb": entry.srgb}
            for entry in plan.palette
        ],
        "parts": [
            {
                "part_name": part.part_name,
                "surfaces": [
                    {
                        "face": surface.face.value,
                        "relief": [list(row) for row in surface.relief],
                        "materials": [list(row) for row in surface.materials],
                    }
                    for surface in part.surfaces
                ],
                "silhouette_features": [
                    {
                        "origin_detail_xyz": list(feature.origin_detail_xyz),
                        "size_detail_xyz": list(feature.size_detail_xyz),
                        "material_id": feature.material_id,
                    }
                    for feature in part.silhouette_features
                ],
            }
            for part in plan.parts
        ],
    }


def character_plan_to_json(plan: CharacterPlan) -> str:
    """Encode a plan as deterministic compact UTF-8 JSON text."""

    return json.dumps(
        character_plan_to_dict(plan),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def character_plan_from_json(payload: str | bytes) -> CharacterPlan:
    """Decode untrusted UTF-8 JSON and validate it entirely locally."""

    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CharacterPlanCodecError("payload must be UTF-8 JSON") from exc
    if not isinstance(payload, str):
        raise TypeError("payload must be str or bytes")
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, CharacterPlanCodecError) as exc:
        raise CharacterPlanCodecError(f"invalid character plan JSON: {exc}") from exc
    return character_plan_from_dict(value)


def character_plan_from_dict(value: object) -> CharacterPlan:
    """Build a CharacterPlan from a strict JSON-compatible object tree."""

    root = _object(value, "$", {"schema_version", "name", "palette", "parts"})
    palette_values = _array(root["palette"], "$.palette")
    part_values = _array(root["parts"], "$.parts")
    try:
        return CharacterPlan(
            schema_version=_string(root["schema_version"], "$.schema_version"),
            name=_string(root["name"], "$.name"),
            palette=tuple(
                _palette(entry, f"$.palette[{index}]")
                for index, entry in enumerate(palette_values)
            ),
            parts=tuple(
                _part(part, f"$.parts[{index}]")
                for index, part in enumerate(part_values)
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, CharacterPlanCodecError):
            raise
        raise CharacterPlanCodecError(f"invalid CharacterPlan: {exc}") from exc


def _palette(value: object, path: str) -> PaletteEntry:
    item = _object(value, path, {"id", "name", "srgb"})
    return PaletteEntry(
        id=_integer(item["id"], f"{path}.id"),
        name=_string(item["name"], f"{path}.name"),
        srgb=_string(item["srgb"], f"{path}.srgb"),
    )


def _part(value: object, path: str) -> PartAppearance:
    item = _object(
        value, path, {"part_name", "surfaces", "silhouette_features"}
    )
    surfaces = _array(item["surfaces"], f"{path}.surfaces")
    features = _array(item["silhouette_features"], f"{path}.silhouette_features")
    return PartAppearance(
        part_name=_string(item["part_name"], f"{path}.part_name"),
        surfaces=tuple(
            _surface(surface, f"{path}.surfaces[{index}]")
            for index, surface in enumerate(surfaces)
        ),
        silhouette_features=tuple(
            _feature(feature, f"{path}.silhouette_features[{index}]")
            for index, feature in enumerate(features)
        ),
    )


def _surface(value: object, path: str) -> SurfaceMap:
    item = _object(value, path, {"face", "relief", "materials"})
    face_value = _string(item["face"], f"{path}.face")
    try:
        face = SurfaceFace(face_value)
    except ValueError as exc:
        raise CharacterPlanCodecError(f"{path}.face has an invalid value") from exc
    return SurfaceMap(
        face=face,
        relief=_grid(item["relief"], f"{path}.relief"),
        materials=_grid(item["materials"], f"{path}.materials"),
    )


def _feature(value: object, path: str) -> SilhouetteFeature:
    item = _object(
        value, path, {"origin_detail_xyz", "size_detail_xyz", "material_id"}
    )
    return SilhouetteFeature(
        origin_detail_xyz=_triple(item["origin_detail_xyz"], f"{path}.origin_detail_xyz"),
        size_detail_xyz=_triple(item["size_detail_xyz"], f"{path}.size_detail_xyz"),
        material_id=_integer(item["material_id"], f"{path}.material_id"),
    )


def _object(value: object, path: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CharacterPlanCodecError(f"{path} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        unknown = sorted(actual - keys)
        raise CharacterPlanCodecError(
            f"{path} has invalid keys (missing={missing}, unknown={unknown})"
        )
    return value


def _array(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise CharacterPlanCodecError(f"{path} must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise CharacterPlanCodecError(f"{path} must be a string")
    return value


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CharacterPlanCodecError(f"{path} must be an integer")
    return value


def _grid(value: object, path: str) -> tuple[tuple[int, ...], ...]:
    rows = _array(value, path)
    return tuple(
        tuple(
            _integer(cell, f"{path}[{row_index}][{column_index}]")
            for column_index, cell in enumerate(_array(row, f"{path}[{row_index}]"))
        )
        for row_index, row in enumerate(rows)
    )


def _triple(value: object, path: str) -> tuple[int, int, int]:
    values = _array(value, path)
    if len(values) != 3:
        raise CharacterPlanCodecError(f"{path} must contain exactly three integers")
    return tuple(_integer(item, f"{path}[{index}]") for index, item in enumerate(values))  # type: ignore[return-value]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterPlanCodecError(f"duplicate object key: {key}")
        result[key] = value
    return result
