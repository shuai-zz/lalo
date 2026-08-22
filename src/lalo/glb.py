"""Assembled GLB preview generation."""

from __future__ import annotations

import json
import math
import os
import struct
from collections.abc import Mapping
from pathlib import Path

from lalo.appearance import CharacterPlan, SurfaceFace, SurfaceMap
from lalo.body import CANONICAL_PARTS, mesh_part
from lalo.generate import DEFAULT_HEIGHT_MM, MASTER_HEIGHT_VOXELS
from lalo.meshing import Mesh
from lalo.relief import DETAIL_CELLS_PER_MASTER, face_detail_shape

_GLB_HEADER = struct.Struct("<4sII")
_CHUNK_HEADER = struct.Struct("<I4s")


def write_canonical_glb(
    output_directory: str | os.PathLike[str],
    *,
    height_mm: float = DEFAULT_HEIGHT_MM,
    plan: CharacterPlan | None = None,
    part_meshes: Mapping[str, Mesh] | None = None,
    geometry_scale_mm: float | None = None,
) -> Path:
    """Write an assembled GLB 2.0 preview and return its path."""

    scale_mm = _scale_for_height(height_mm)
    document, binary = _build_document(
        scale_mm, plan, part_meshes, geometry_scale_mm
    )
    json_chunk = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    json_chunk += b" " * (-len(json_chunk) % 4)
    binary += b"\0" * (-len(binary) % 4)

    total_length = (
        _GLB_HEADER.size
        + _CHUNK_HEADER.size
        + len(json_chunk)
        + _CHUNK_HEADER.size
        + len(binary)
    )
    data = b"".join(
        (
            _GLB_HEADER.pack(b"glTF", 2, total_length),
            _CHUNK_HEADER.pack(len(json_chunk), b"JSON"),
            json_chunk,
            _CHUNK_HEADER.pack(len(binary), b"BIN\0"),
            binary,
        )
    )
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "preview.glb"
    path.write_bytes(data)
    return path


def _build_document(
    scale_mm: float,
    plan: CharacterPlan | None = None,
    part_meshes: Mapping[str, Mesh] | None = None,
    geometry_scale_mm: float | None = None,
) -> tuple[dict[str, object], bytes]:
    binary = bytearray()
    buffer_views: list[dict[str, object]] = []
    accessors: list[dict[str, object]] = []
    meshes: list[dict[str, object]] = []
    root_children = list(range(1, len(CANONICAL_PARTS) + 1))
    nodes: list[dict[str, object]] = [
        {
            "name": "Z-up to glTF Y-up",
            "rotation": [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)],
            "children": root_children,
        }
    ]
    mesh_scale = geometry_scale_mm if geometry_scale_mm is not None else scale_mm
    if not math.isfinite(mesh_scale) or mesh_scale <= 0:
        raise ValueError("geometry_scale_mm must be finite and greater than zero")

    for part in CANONICAL_PARTS:
        mesh = part_meshes[part.name] if part_meshes is not None else mesh_part(part)
        position_offset = _append_aligned(
            binary,
            b"".join(
                struct.pack("<3f", *(coordinate * mesh_scale for coordinate in vertex))
                for vertex in mesh.vertices
            ),
        )
        position_view = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": position_offset,
                "byteLength": len(mesh.vertices) * 12,
                "target": 34962,
            }
        )
        position_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": position_view,
                "componentType": 5126,
                "count": len(mesh.vertices),
                "type": "VEC3",
                "min": [
                    min(vertex[axis] for vertex in mesh.vertices) * mesh_scale
                    for axis in range(3)
                ],
                "max": [
                    max(vertex[axis] for vertex in mesh.vertices) * mesh_scale
                    for axis in range(3)
                ],
            }
        )

        index_offset = _append_aligned(
            binary,
            b"".join(struct.pack("<3I", *face) for face in mesh.faces),
        )
        index_view = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": index_offset,
                "byteLength": len(mesh.faces) * 12,
                "target": 34963,
            }
        )
        index_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": index_view,
                "componentType": 5125,
                "count": len(mesh.faces) * 3,
                "type": "SCALAR",
                "min": [min(index for face in mesh.faces for index in face)],
                "max": [max(index for face in mesh.faces for index in face)],
            }
        )

        mesh_index = len(meshes)
        meshes.append(
            {
                "name": part.name,
                "primitives": [
                    {
                        "attributes": {"POSITION": position_accessor},
                        "indices": index_accessor,
                        "material": 0,
                        "mode": 4,
                    }
                ],
            }
        )
        nodes.append(
            {
                "name": part.name,
                "mesh": mesh_index,
                "translation": [value * scale_mm for value in part.origin_xyz],
            }
        )

    if plan is not None:
        _append_material_overlays(
            plan,
            scale_mm,
            binary,
            buffer_views,
            accessors,
            meshes,
            nodes,
            root_children,
        )

    document: dict[str, object] = {
        "asset": {"version": "2.0", "generator": "Lalo"},
        "scene": 0,
        "scenes": [{"name": "Lalo preview", "nodes": [0]}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": _materials(plan),
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(binary)}],
        "extras": {"canonicalUpAxis": "+Z", "canonicalForwardAxis": "-Y"},
    }
    if plan is not None:
        document["extras"] = {
            **document["extras"],
            "characterPlan": plan.name,
        }
    return document, bytes(binary)


def _append_material_overlays(
    plan: CharacterPlan,
    scale_mm: float,
    binary: bytearray,
    buffer_views: list[dict[str, object]],
    accessors: list[dict[str, object]],
    meshes: list[dict[str, object]],
    nodes: list[dict[str, object]],
    root_children: list[int],
) -> None:
    parts_by_name = {part.name: part for part in CANONICAL_PARTS}
    detail_pitch = scale_mm / DETAIL_CELLS_PER_MASTER
    for appearance in plan.parts:
        part = parts_by_name[appearance.part_name]
        positions_by_material: dict[int, list[tuple[float, float, float]]] = {}
        indices_by_material: dict[int, list[int]] = {}
        for surface in appearance.surfaces:
            expected = face_detail_shape(part, surface.face)
            actual = len(surface.materials), len(surface.materials[0])
            if actual != expected:
                raise ValueError(
                    f"{part.name}.{surface.face.value} material map must be "
                    f"{expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}"
                )
            for row, material_row in enumerate(surface.materials):
                for column, material in enumerate(material_row):
                    positions = positions_by_material.setdefault(material, [])
                    indices = indices_by_material.setdefault(material, [])
                    start = len(positions)
                    positions.extend(
                        _patch_vertices(
                            part.size_xyz,
                            surface,
                            row,
                            column,
                            detail_pitch,
                            scale_mm,
                        )
                    )
                    indices.extend((start, start + 1, start + 2, start, start + 2, start + 3))

        primitives = []
        for material in sorted(positions_by_material):
            positions = positions_by_material[material]
            indices = indices_by_material[material]
            position_accessor = _append_positions(
                positions, binary, buffer_views, accessors
            )
            index_accessor = _append_indices(indices, binary, buffer_views, accessors)
            primitives.append(
                {
                    "attributes": {"POSITION": position_accessor},
                    "indices": index_accessor,
                    "material": material,
                    "mode": 4,
                }
            )
        if not primitives:
            continue
        mesh_index = len(meshes)
        meshes.append({"name": f"{part.name}_materials", "primitives": primitives})
        node_index = len(nodes)
        nodes.append(
            {
                "name": f"{part.name}_materials",
                "mesh": mesh_index,
                "translation": [value * scale_mm for value in part.origin_xyz],
            }
        )
        root_children.append(node_index)


def _patch_vertices(
    size_xyz: tuple[int, int, int],
    surface: SurfaceMap,
    row: int,
    column: int,
    pitch: float,
    master_scale: float,
) -> tuple[tuple[float, float, float], ...]:
    size_x, size_y, size_z = (value * master_scale for value in size_xyz)
    level = surface.relief[row][column]
    offset = level * pitch + min(0.01, pitch * 0.02)
    low = column * pitch
    high = (column + 1) * pitch
    if surface.face in (SurfaceFace.FRONT, SurfaceFace.BACK):
        z_high = size_z - row * pitch
        z_low = z_high - pitch
        y = -offset if surface.face == SurfaceFace.FRONT else size_y + offset
        return (low, y, z_low), (high, y, z_low), (high, y, z_high), (low, y, z_high)
    if surface.face in (SurfaceFace.LEFT, SurfaceFace.RIGHT):
        z_high = size_z - row * pitch
        z_low = z_high - pitch
        x = size_x + offset if surface.face == SurfaceFace.LEFT else -offset
        return (x, low, z_low), (x, high, z_low), (x, high, z_high), (x, low, z_high)
    y_low = row * pitch
    y_high = (row + 1) * pitch
    z = size_z + offset if surface.face == SurfaceFace.TOP else -offset
    return (low, y_low, z), (high, y_low, z), (high, y_high, z), (low, y_high, z)


def _append_positions(
    positions: list[tuple[float, float, float]],
    binary: bytearray,
    buffer_views: list[dict[str, object]],
    accessors: list[dict[str, object]],
) -> int:
    offset = _append_aligned(
        binary, b"".join(struct.pack("<3f", *position) for position in positions)
    )
    view = len(buffer_views)
    buffer_views.append(
        {"buffer": 0, "byteOffset": offset, "byteLength": len(positions) * 12, "target": 34962}
    )
    accessor = len(accessors)
    accessors.append(
        {
            "bufferView": view,
            "componentType": 5126,
            "count": len(positions),
            "type": "VEC3",
            "min": [min(position[axis] for position in positions) for axis in range(3)],
            "max": [max(position[axis] for position in positions) for axis in range(3)],
        }
    )
    return accessor


def _append_indices(
    indices: list[int],
    binary: bytearray,
    buffer_views: list[dict[str, object]],
    accessors: list[dict[str, object]],
) -> int:
    offset = _append_aligned(
        binary, b"".join(struct.pack("<I", index) for index in indices)
    )
    view = len(buffer_views)
    buffer_views.append(
        {"buffer": 0, "byteOffset": offset, "byteLength": len(indices) * 4, "target": 34963}
    )
    accessor = len(accessors)
    accessors.append(
        {
            "bufferView": view,
            "componentType": 5125,
            "count": len(indices),
            "type": "SCALAR",
            "min": [min(indices)],
            "max": [max(indices)],
        }
    )
    return accessor


def _materials(plan: CharacterPlan | None) -> list[dict[str, object]]:
    if plan is None:
        return [
            {
                "name": "Lalo neutral",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.72, 0.75, 0.8, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.8,
                },
            }
        ]
    return [
        {
            "name": entry.name,
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": [*_linear_rgb(entry.srgb), 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.8,
            },
        }
        for entry in plan.palette
    ]


def _linear_rgb(srgb: str) -> tuple[float, float, float]:
    channels = tuple(int(srgb[index : index + 2], 16) / 255 for index in (1, 3, 5))
    return tuple(
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    )


def _append_aligned(buffer: bytearray, data: bytes) -> int:
    buffer.extend(b"\0" * (-len(buffer) % 4))
    offset = len(buffer)
    buffer.extend(data)
    return offset


def _scale_for_height(height_mm: float) -> float:
    if isinstance(height_mm, bool) or not isinstance(height_mm, (int, float)):
        raise TypeError("height_mm must be a number")
    height = float(height_mm)
    if not math.isfinite(height) or height <= 0:
        raise ValueError("height_mm must be finite and greater than zero")
    return height / MASTER_HEIGHT_VOXELS
