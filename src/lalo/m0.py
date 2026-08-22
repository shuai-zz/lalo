"""End-to-end M0 artifact generation."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

from lalo.body import CANONICAL_PARTS, mesh_part
from lalo.generate import (
    DEFAULT_HEIGHT_MM,
    MASTER_HEIGHT_VOXELS,
    write_canonical_manifest,
    write_canonical_stls,
)
from lalo.glb import write_canonical_glb
from lalo.validation import MeshValidation, validate_mesh


@dataclass(frozen=True)
class M0Artifacts:
    """Paths produced by a successful M0 generation."""

    stl_paths: tuple[Path, ...]
    manifest_path: Path
    preview_path: Path
    validation_report_path: Path


def generate_m0_artifacts(
    output_directory: str | os.PathLike[str], *, height_mm: float = DEFAULT_HEIGHT_MM
) -> M0Artifacts:
    """Generate the complete validated, untextured M0 artifact directory."""

    height = _validate_height(height_mm)
    output = Path(output_directory)
    _require_empty_output(output)
    validations = tuple(
        (part.name, validate_mesh(mesh_part(part))) for part in CANONICAL_PARTS
    )
    failures = tuple(name for name, result in validations if not result.valid)
    if failures:
        raise RuntimeError(
            "canonical mesh validation failed for: " + ", ".join(failures)
        )

    stl_directory = output / "stl"
    stl_paths = write_canonical_stls(stl_directory, height_mm=height)
    manifest_path = write_canonical_manifest(
        stl_directory,
        height_mm=height,
        destination=output / "manifest.json",
    )
    preview_path = write_canonical_glb(output, height_mm=height)
    validation_report_path = _write_validation_report(output, height, validations)
    return M0Artifacts(
        stl_paths=stl_paths,
        manifest_path=manifest_path,
        preview_path=preview_path,
        validation_report_path=validation_report_path,
    )


def _write_validation_report(
    output: Path,
    height_mm: float,
    validations: tuple[tuple[str, MeshValidation], ...],
) -> Path:
    scale_mm = height_mm / MASTER_HEIGHT_VOXELS
    report = {
        "schema_version": "1.0",
        "status": "passed",
        "height_mm": height_mm,
        "checks": {
            "finite_coordinates": "passed",
            "valid_indices": "passed",
            "non_degenerate_triangles": "passed",
            "edge_manifold": "passed",
            "single_component": "passed",
            "positive_volume": "passed",
            "self_intersection": "guaranteed_by_occupancy_construction",
        },
        "parts": [
            {
                "name": name,
                "valid": result.valid,
                "vertex_count": result.vertex_count,
                "triangle_count": result.triangle_count,
                "edge_count": result.edge_count,
                "component_count": result.component_count,
                "signed_volume_mm3": result.signed_volume * scale_mm**3,
                "issues": [
                    {"code": issue.code, "message": issue.message}
                    for issue in result.issues
                ],
            }
            for name, result in validations
        ],
    }
    path = output / "validation_report.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _validate_height(height_mm: float) -> float:
    if isinstance(height_mm, bool) or not isinstance(height_mm, (int, float)):
        raise TypeError("height_mm must be a number")
    height = float(height_mm)
    if not math.isfinite(height) or height <= 0:
        raise ValueError("height_mm must be finite and greater than zero")
    return height


def _require_empty_output(output: Path) -> None:
    if output.exists() and not output.is_dir():
        raise FileExistsError(f"output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output directory must be empty: {output}")
