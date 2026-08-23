"""End-to-end M1 relief and material artifact generation."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

from lalo.appearance import CharacterPlan, PartAppearance, SurfaceMap
from lalo.body import CANONICAL_PARTS, assembly_translation_mm
from lalo.generate import DEFAULT_HEIGHT_MM, MASTER_HEIGHT_VOXELS
from lalo.glb import write_canonical_glb
from lalo.meshing import Mesh
from lalo.printability import clean_relief_for_fdm
from lalo.protection import canonical_protection_masks, clip_protected_relief
from lalo.relief import (
    DETAIL_CELLS_PER_MASTER,
    compile_part_relief,
    mesh_detailed_part,
)
from lalo.stl import binary_stl_bytes
from lalo.validation import MeshValidation, validate_mesh


@dataclass(frozen=True)
class M1Artifacts:
    """Paths produced by a successful M1 character generation."""

    stl_paths: tuple[Path, ...]
    manifest_path: Path
    preview_path: Path
    character_plan_path: Path
    material_grid_path: Path
    validation_report_path: Path


@dataclass(frozen=True)
class _PartBuild:
    name: str
    mesh: Mesh
    validation: MeshValidation
    expanded_pixels: int
    adjusted_depth_pixels: int
    clipped_pixels: int


def generate_m1_artifacts(
    plan: CharacterPlan,
    output_directory: str | os.PathLike[str],
    *,
    height_mm: float = DEFAULT_HEIGHT_MM,
) -> M1Artifacts:
    """Generate a complete validated M1 artifact directory from ``plan``."""

    height = _validate_height(height_mm)
    output = Path(output_directory)
    _require_empty_output(output)
    processed_plan, builds = _compile_plan(plan, height)
    failures = tuple(build.name for build in builds if not build.validation.valid)
    if failures:
        raise RuntimeError("M1 mesh validation failed for: " + ", ".join(failures))

    master_scale = height / MASTER_HEIGHT_VOXELS
    detail_pitch = master_scale / DETAIL_CELLS_PER_MASTER
    output.mkdir(parents=True, exist_ok=True)
    stl_directory = output / "stl"
    stl_directory.mkdir()
    stl_paths = tuple(
        _write_part_stl(stl_directory, build, detail_pitch) for build in builds
    )
    character_plan_path = _write_json(
        output / "character_plan.json", _plan_document(processed_plan)
    )
    material_grid_path = _write_material_grid(output, processed_plan)
    manifest_path = _write_manifest(
        output, builds, stl_paths, height, master_scale, detail_pitch, processed_plan
    )
    preview_path = write_canonical_glb(
        output,
        height_mm=height,
        plan=processed_plan,
        part_meshes={build.name: build.mesh for build in builds},
        geometry_scale_mm=detail_pitch,
    )
    validation_report_path = _write_validation_report(output, builds, height)
    return M1Artifacts(
        stl_paths=stl_paths,
        manifest_path=manifest_path,
        preview_path=preview_path,
        character_plan_path=character_plan_path,
        material_grid_path=material_grid_path,
        validation_report_path=validation_report_path,
    )


def _compile_plan(
    plan: CharacterPlan, height_mm: float
) -> tuple[CharacterPlan, tuple[_PartBuild, ...]]:
    appearances = {part.part_name: part for part in plan.parts}
    processed_parts: list[PartAppearance] = []
    builds: list[_PartBuild] = []
    for spec in CANONICAL_PARTS:
        appearance = appearances.get(spec.name, PartAppearance(spec.name, ()))
        cleaned_surfaces: list[SurfaceMap] = []
        expanded = 0
        adjusted = 0
        for surface in appearance.surfaces:
            result = clean_relief_for_fdm(surface, height_mm=height_mm)
            cleaned_surfaces.append(result.surface)
            expanded += result.expanded_pixel_count
            adjusted += result.depth_adjustment_count
        protection = clip_protected_relief(
            tuple(cleaned_surfaces), canonical_protection_masks(spec)
        )
        processed = PartAppearance(
            spec.name,
            protection.surfaces,
            appearance.silhouette_features,
        )
        detailed = compile_part_relief(
            spec, processed.surfaces, processed.silhouette_features
        )
        mesh = mesh_detailed_part(detailed)
        processed_parts.append(processed)
        builds.append(
            _PartBuild(
                spec.name,
                mesh,
                validate_mesh(mesh),
                expanded,
                adjusted,
                protection.clipped_pixel_count,
            )
        )
    return (
        CharacterPlan(
            plan.schema_version,
            plan.name,
            plan.palette,
            tuple(processed_parts),
        ),
        tuple(builds),
    )


def _write_part_stl(directory: Path, build: _PartBuild, pitch: float) -> Path:
    path = directory / f"{build.name}.stl"
    path.write_bytes(binary_stl_bytes(build.mesh, scale_mm=pitch))
    return path


def _write_manifest(
    output: Path,
    builds: tuple[_PartBuild, ...],
    stl_paths: tuple[Path, ...],
    height_mm: float,
    master_scale: float,
    detail_pitch: float,
    plan: CharacterPlan,
) -> Path:
    specs = {part.name: part for part in CANONICAL_PARTS}
    entries = []
    for build, stl_path in zip(builds, stl_paths, strict=True):
        data = stl_path.read_bytes()
        bounds = _mesh_bounds(build.mesh)
        spec = specs[build.name]
        entries.append(
            {
                "name": build.name,
                "file": stl_path.relative_to(output).as_posix(),
                "canonical_size_mm": [value * master_scale for value in spec.size_xyz],
                "local_bounds_mm": [
                    [value * detail_pitch for value in bounds[0]],
                    [value * detail_pitch for value in bounds[1]],
                ],
                "assembly_translation_mm": list(
                    assembly_translation_mm(spec, master_scale)
                ),
                "assembly_rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                "byte_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return _write_json(
        output / "manifest.json",
        {
            "schema_version": "1.0",
            "stage": "M1",
            "character": plan.name,
            "height_mm": height_mm,
            "master_voxel_mm": master_scale,
            "detail_pitch_mm": detail_pitch,
            "coordinate_system": {
                "unit": "millimeter",
                "up_axis": "+Z",
                "forward_axis": "-Y",
            },
            "palette": [_palette_document(entry) for entry in plan.palette],
            "parts": entries,
        },
    )


def _write_validation_report(
    output: Path, builds: tuple[_PartBuild, ...], height_mm: float
) -> Path:
    return _write_json(
        output / "validation_report.json",
        {
            "schema_version": "1.0",
            "stage": "M1",
            "status": "passed",
            "height_mm": height_mm,
            "parts": [
                {
                    "name": build.name,
                    "valid": build.validation.valid,
                    "vertex_count": build.validation.vertex_count,
                    "triangle_count": build.validation.triangle_count,
                    "edge_count": build.validation.edge_count,
                    "component_count": build.validation.component_count,
                    "signed_volume_detail_cells": build.validation.signed_volume,
                    "expanded_relief_pixels": build.expanded_pixels,
                    "adjusted_depth_pixels": build.adjusted_depth_pixels,
                    "clipped_protected_pixels": build.clipped_pixels,
                    "issues": [
                        {"code": issue.code, "message": issue.message}
                        for issue in build.validation.issues
                    ],
                }
                for build in builds
            ],
        },
    )


def _write_material_grid(output: Path, plan: CharacterPlan) -> Path:
    document = {
        "schema_version": plan.schema_version,
        "character": plan.name,
        "palette": [_palette_document(entry) for entry in plan.palette],
        "parts": [
            {
                "name": part.part_name,
                "surfaces": [
                    {
                        "face": surface.face.value,
                        "materials": surface.materials,
                    }
                    for surface in part.surfaces
                ],
                "silhouette_materials": [
                    feature.material_id for feature in part.silhouette_features
                ],
            }
            for part in plan.parts
        ],
    }
    raw = _json_bytes(document)
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0) as archive:
        archive.write(raw)
    path = output / "material_grid.json.gz"
    path.write_bytes(buffer.getvalue())
    return path


def _plan_document(plan: CharacterPlan) -> dict[str, object]:
    return {
        "schema_version": plan.schema_version,
        "name": plan.name,
        "palette": [_palette_document(entry) for entry in plan.palette],
        "parts": [
            {
                "part_name": part.part_name,
                "surfaces": [
                    {
                        "face": surface.face.value,
                        "relief": surface.relief,
                        "materials": surface.materials,
                    }
                    for surface in part.surfaces
                ],
                "silhouette_features": [
                    {
                        "origin_detail_xyz": feature.origin_detail_xyz,
                        "size_detail_xyz": feature.size_detail_xyz,
                        "material_id": feature.material_id,
                    }
                    for feature in part.silhouette_features
                ],
            }
            for part in plan.parts
        ],
    }


def _palette_document(entry: object) -> dict[str, object]:
    return {"id": entry.id, "name": entry.name, "srgb": entry.srgb}  # type: ignore[attr-defined]


def _mesh_bounds(mesh: Mesh) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    return (
        tuple(min(vertex[axis] for vertex in mesh.vertices) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in mesh.vertices) for axis in range(3)),
    )


def _write_json(path: Path, document: object) -> Path:
    path.write_bytes(_json_bytes(document))
    return path


def _json_bytes(document: object) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


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
