"""Canonical block-figure artifact generation."""

from __future__ import annotations

import math
import os
from pathlib import Path

from lalo.body import CANONICAL_PARTS, mesh_part
from lalo.stl import binary_stl_bytes

MASTER_HEIGHT_VOXELS = 32
DEFAULT_HEIGHT_MM = 80.0


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
