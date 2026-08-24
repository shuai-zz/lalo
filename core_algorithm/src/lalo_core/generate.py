"""Canonical block-figure artifact generation."""

from __future__ import annotations

import math
import os
import hashlib
import json
from pathlib import Path

from lalo_core.body import CANONICAL_PARTS, assembly_translation_mm, mesh_part
from lalo_core.stl import binary_stl_bytes

MASTER_HEIGHT_VOXELS = 32
DEFAULT_HEIGHT_MM = 96.0


def write_canonical_stls(
    output_directory: str | os.PathLike[str], *, height_mm: float = DEFAULT_HEIGHT_MM
) -> tuple[Path, ...]:
    """Write the canonical 14-part STL set to an empty directory."""

    height = _validate_height(height_mm)
    output = Path(output_directory)
    _validate_output_directory(output)
    scale_mm = height / MASTER_HEIGHT_VOXELS

    artifacts = tuple(
        (
            output / f"{part.name}.stl",
            binary_stl_bytes(mesh_part(part), scale_mm=scale_mm),
        )
        for part in CANONICAL_PARTS
    )

    output.mkdir(parents=True, exist_ok=True)
    for path, data in artifacts:
        path.write_bytes(data)
    return tuple(path for path, _ in artifacts)


def write_canonical_manifest(
    stl_directory: str | os.PathLike[str],
    *,
    height_mm: float = DEFAULT_HEIGHT_MM,
    destination: str | os.PathLike[str] | None = None,
) -> Path:
    """Write assembly metadata for a complete canonical STL directory."""

    height = _validate_height(height_mm)
    stl_output = Path(stl_directory)
    manifest_path = (
        Path(destination) if destination is not None else stl_output / "manifest.json"
    )
    scale_mm = height / MASTER_HEIGHT_VOXELS
    part_entries = []

    for part in CANONICAL_PARTS:
        stl_path = stl_output / f"{part.name}.stl"
        if not stl_path.is_file():
            raise FileNotFoundError(f"missing canonical STL: {stl_path}")
        stl_data = stl_path.read_bytes()
        relative_file = Path(
            os.path.relpath(stl_path, start=manifest_path.parent)
        ).as_posix()
        part_entries.append(
            {
                "name": part.name,
                "file": relative_file,
                "size_mm": [value * scale_mm for value in part.size_xyz],
                "assembly_translation_mm": list(
                    assembly_translation_mm(part, scale_mm)
                ),
                "assembly_rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                "byte_size": len(stl_data),
                "sha256": hashlib.sha256(stl_data).hexdigest(),
            }
        )

    manifest = {
        "schema_version": "1.0",
        "height_mm": height,
        "master_height_voxels": MASTER_HEIGHT_VOXELS,
        "master_voxel_mm": scale_mm,
        "coordinate_system": {
            "unit": "millimeter",
            "up_axis": "+Z",
            "forward_axis": "-Y",
        },
        "parts": part_entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _validate_height(height_mm: float) -> float:
    if isinstance(height_mm, bool) or not isinstance(height_mm, (int, float)):
        raise TypeError("height_mm must be a number")
    height = float(height_mm)
    if not math.isfinite(height) or height <= 0:
        raise ValueError("height_mm must be finite and greater than zero")
    return height


def _validate_output_directory(output: Path) -> None:
    if output.exists() and not output.is_dir():
        raise FileExistsError(f"output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output directory must be empty: {output}")
