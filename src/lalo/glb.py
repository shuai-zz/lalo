"""Assembled GLB preview generation."""

from __future__ import annotations

import json
import math
import os
import struct
from pathlib import Path

from lalo.body import CANONICAL_PARTS, mesh_part
from lalo.generate import DEFAULT_HEIGHT_MM, MASTER_HEIGHT_VOXELS

_GLB_HEADER = struct.Struct("<4sII")
_CHUNK_HEADER = struct.Struct("<I4s")


def write_canonical_glb(
    output_directory: str | os.PathLike[str], *, height_mm: float = DEFAULT_HEIGHT_MM
) -> Path:
    """Write an assembled GLB 2.0 preview and return its path."""

    scale_mm = _scale_for_height(height_mm)
    document, binary = _build_document(scale_mm)
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


def _build_document(scale_mm: float) -> tuple[dict[str, object], bytes]:
    binary = bytearray()
    buffer_views: list[dict[str, object]] = []
    accessors: list[dict[str, object]] = []
    meshes: list[dict[str, object]] = []
    nodes: list[dict[str, object]] = [
        {
            "name": "Z-up to glTF Y-up",
            "rotation": [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)],
            "children": list(range(1, len(CANONICAL_PARTS) + 1)),
        }
    ]

    for part in CANONICAL_PARTS:
        mesh = mesh_part(part)
        position_offset = _append_aligned(
            binary,
            b"".join(
                struct.pack("<3f", *(coordinate * scale_mm for coordinate in vertex))
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
                "min": [0.0, 0.0, 0.0],
                "max": [value * scale_mm for value in part.size_xyz],
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

    document: dict[str, object] = {
        "asset": {"version": "2.0", "generator": "Lalo"},
        "scene": 0,
        "scenes": [{"name": "Lalo preview", "nodes": [0]}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [
            {
                "name": "Lalo neutral",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.72, 0.75, 0.8, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.8,
                },
            }
        ],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(binary)}],
        "extras": {"canonicalUpAxis": "+Z", "canonicalForwardAxis": "-Y"},
    }
    return document, bytes(binary)


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
