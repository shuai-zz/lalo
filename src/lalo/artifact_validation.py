"""Independent validation of complete printable artifact packages."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from lalo.body import CANONICAL_PARTS
from lalo.plan_json import character_plan_from_json

_REQUIRED_FILES = {
    "character_plan.json",
    "manifest.json",
    "material_grid.json.gz",
    "preview.glb",
    "result.zip",
    "validation_report.json",
}


@dataclass(frozen=True)
class ArtifactValidationResult:
    """Stable validation outcome suitable for CLI and API consumers."""

    valid: bool
    errors: tuple[str, ...]


def validate_artifact_directory(
    directory: str | os.PathLike[str],
) -> ArtifactValidationResult:
    """Validate layout, metadata, hashes, reports, and archive contents."""

    root = Path(directory)
    errors: list[str] = []
    if not root.is_dir():
        return ArtifactValidationResult(False, ("missing_artifact_directory",))
    names = {path.name for path in root.iterdir() if path.is_file()}
    for missing in sorted(_REQUIRED_FILES - names):
        errors.append(f"missing_file:{missing}")
    _validate_plan(root, errors)
    _validate_material_grid(root, errors)
    _validate_glb(root, errors)
    _validate_manifest(root, errors)
    _validate_report(root, errors)
    _validate_zip(root, errors)
    unique = tuple(dict.fromkeys(errors))
    return ArtifactValidationResult(not unique, unique)


def _validate_plan(root: Path, errors: list[str]) -> None:
    try:
        character_plan_from_json((root / "character_plan.json").read_bytes())
    except (OSError, TypeError, ValueError):
        errors.append("invalid_character_plan")


def _validate_material_grid(root: Path, errors: list[str]) -> None:
    try:
        document = json.loads(gzip.decompress((root / "material_grid.json.gz").read_bytes()))
        if not isinstance(document, dict) or not isinstance(document.get("parts"), list):
            raise ValueError
    except (OSError, EOFError, gzip.BadGzipFile, json.JSONDecodeError, ValueError):
        errors.append("invalid_material_grid")


def _validate_glb(root: Path, errors: list[str]) -> None:
    try:
        if (root / "preview.glb").read_bytes()[:4] != b"glTF":
            raise ValueError
    except (OSError, ValueError):
        errors.append("invalid_preview_glb")


def _validate_manifest(root: Path, errors: list[str]) -> None:
    try:
        document = json.loads((root / "manifest.json").read_text("utf-8"))
        parts = document["parts"]
        if not isinstance(parts, list):
            raise ValueError
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        errors.append("invalid_manifest")
        return
    expected = {part.name for part in CANONICAL_PARTS}
    actual = {part.get("name") for part in parts if isinstance(part, dict)}
    if actual != expected or len(parts) != len(expected):
        errors.append("invalid_manifest_parts")
        return
    for part in parts:
        try:
            relative = part["file"]
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != relative:
                raise ValueError
            path = root.joinpath(*pure.parts)
            data = path.read_bytes()
            if len(data) != part["byte_size"]:
                errors.append(f"size_mismatch:{part['name']}")
            if hashlib.sha256(data).hexdigest() != part["sha256"]:
                errors.append(f"hash_mismatch:{part['name']}")
        except (OSError, KeyError, TypeError, ValueError):
            name = part.get("name", "unknown") if isinstance(part, dict) else "unknown"
            errors.append(f"invalid_manifest_part:{name}")


def _validate_report(root: Path, errors: list[str]) -> None:
    try:
        report = json.loads((root / "validation_report.json").read_text("utf-8"))
        parts = report["parts"]
        if report["status"] != "passed" or len(parts) != len(CANONICAL_PARTS):
            raise ValueError
        if any(not part.get("valid") for part in parts):
            raise ValueError
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        errors.append("invalid_validation_report")


def _validate_zip(root: Path, errors: list[str]) -> None:
    archive_path = root / "result.zip"
    try:
        expected = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and path != archive_path
        }
        with zipfile.ZipFile(archive_path) as archive:
            if archive.namelist() != sorted(expected):
                raise ValueError
            for name, data in expected.items():
                if archive.read(name) != data:
                    raise ValueError
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        errors.append("invalid_result_zip")
