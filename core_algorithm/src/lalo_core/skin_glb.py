"""Render a standard Minecraft skin on a fixed classic block body as GLB."""

from __future__ import annotations

import argparse
import io
import json
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

from lalo_core.skin_sampling import _UV

_GLB_HEADER = struct.Struct("<4sII")
_CHUNK_HEADER = struct.Struct("<I4s")
_FLOAT3 = struct.Struct("<3f")
_FLOAT2 = struct.Struct("<2f")
_USHORT = struct.Struct("<H")


@dataclass(frozen=True)
class _Part:
    name: str
    origin: tuple[float, float, float]
    size: tuple[float, float, float]


_PARTS = (
    _Part("head", (-4, -4, 24), (8, 8, 8)),
    _Part("torso", (-4, -2, 12), (8, 4, 12)),
    _Part("right_arm", (-8, -2, 12), (4, 4, 12)),
    _Part("left_arm", (4, -2, 12), (4, 4, 12)),
    _Part("right_leg", (-4, -2, 0), (4, 4, 12)),
    _Part("left_leg", (0, -2, 0), (4, 4, 12)),
)


def write_textured_skin_glb(
    skin_path: str | os.PathLike[str], destination: str | os.PathLike[str]
) -> Path:
    """Write a deterministic self-contained GLB for rotating skin review."""

    output = Path(destination)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    texture = _normalized_skin_png(skin_path)
    document, binary = _build_glb(texture)
    json_chunk = json.dumps(
        document, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    json_chunk += b" " * (-len(json_chunk) % 4)
    binary += b"\x00" * (-len(binary) % 4)
    total = 12 + 8 + len(json_chunk) + 8 + len(binary)
    payload = b"".join(
        (
            _GLB_HEADER.pack(b"glTF", 2, total),
            _CHUNK_HEADER.pack(len(json_chunk), b"JSON"),
            json_chunk,
            _CHUNK_HEADER.pack(len(binary), b"BIN\x00"),
            binary,
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return output


def _normalized_skin_png(path: str | os.PathLike[str]) -> bytes:
    with Image.open(path) as source:
        source.load()
        if source.size != (64, 64):
            raise ValueError("skin must be exactly 64x64 pixels")
        skin = source.convert("RGBA")
    stream = io.BytesIO()
    skin.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue()


def _build_glb(texture: bytes) -> tuple[dict[str, object], bytes]:
    binary = bytearray()
    buffer_views: list[dict[str, object]] = []
    accessors: list[dict[str, object]] = []
    meshes: list[dict[str, object]] = []
    nodes: list[dict[str, object]] = []

    for part in _PARTS:
        positions, normals, texcoords, indices = _cuboid_data(part)
        position_accessor = _append_accessor(
            binary, buffer_views, accessors, positions, component_type=5126,
            accessor_type="VEC3", count=24, target=34962,
            minimum=[min(vertex[axis] for vertex in positions) for axis in range(3)],
            maximum=[max(vertex[axis] for vertex in positions) for axis in range(3)],
            packer=_FLOAT3,
        )
        texcoord_accessor = _append_accessor(
            binary, buffer_views, accessors, texcoords, component_type=5126,
            accessor_type="VEC2", count=24, target=34962, packer=_FLOAT2,
        )
        normal_accessor = _append_accessor(
            binary, buffer_views, accessors, normals, component_type=5126,
            accessor_type="VEC3", count=24, target=34962, packer=_FLOAT3,
        )
        index_accessor = _append_accessor(
            binary, buffer_views, accessors, indices, component_type=5123,
            accessor_type="SCALAR", count=36, target=34963, packer=_USHORT,
        )
        meshes.append(
            {
                "name": part.name,
                "primitives": [
                    {
                        "attributes": {
                            "NORMAL": normal_accessor,
                            "POSITION": position_accessor,
                            "TEXCOORD_0": texcoord_accessor,
                        },
                        "indices": index_accessor,
                        "material": 0,
                        "mode": 4,
                    }
                ],
            }
        )
        nodes.append({"name": part.name, "mesh": len(meshes) - 1})

    _align(binary)
    image_offset = len(binary)
    binary.extend(texture)
    buffer_views.append(
        {"buffer": 0, "byteOffset": image_offset, "byteLength": len(texture)}
    )
    document: dict[str, object] = {
        "asset": {"generator": "lalo-core-experiment", "version": "2.0"},
        "scene": 0,
        "scenes": [{"name": "Skin Review", "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [
            {
                "name": "skin",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 1.0,
                },
                "alphaMode": "OPAQUE",
                "doubleSided": False,
            }
        ],
        "textures": [{"sampler": 0, "source": 0}],
        "samplers": [
            {"magFilter": 9728, "minFilter": 9728, "wrapS": 33071, "wrapT": 33071}
        ],
        "images": [
            {
                "name": "skin.png",
                "bufferView": len(buffer_views) - 1,
                "mimeType": "image/png",
            }
        ],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    return document, bytes(binary)


def _cuboid_data(
    part: _Part,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[float, float, float]],
    list[tuple[float, float]],
    list[int],
]:
    x0, y0, z0 = part.origin
    width, depth, height = part.size
    x1, y1, z1 = x0 + width, y0 + depth, z0 + height
    faces = {
        "front": ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),
        "back": ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)),
        "right": ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)),
        "left": ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)),
        "top": ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
        "bottom": ((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)),
    }
    face_normals = {
        "front": (0.0, 0.0, 1.0),
        "back": (0.0, 0.0, -1.0),
        "right": (-1.0, 0.0, 0.0),
        "left": (1.0, 0.0, 0.0),
        "top": (0.0, 1.0, 0.0),
        "bottom": (0.0, -1.0, 0.0),
    }
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    texcoords: list[tuple[float, float]] = []
    indices: list[int] = []
    for face_name, vertices in faces.items():
        start = len(positions)
        positions.extend(_gltf_vertex(vertex) for vertex in vertices)
        normals.extend((face_normals[face_name],) * 4)
        texcoords.extend(_uv_coordinates(_UV[part.name][face_name]))
        indices.extend((start, start + 1, start + 2, start, start + 2, start + 3))
    return positions, normals, texcoords, indices


def _gltf_vertex(vertex: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vertex
    return float(x), float(z), float(-y)


def _uv_coordinates(rectangle: tuple[int, int, int, int]) -> tuple[tuple[float, float], ...]:
    x0, y0, x1, y1 = rectangle
    u0, u1 = (x0 + 0.5) / 64, (x1 - 0.5) / 64
    v0, v1 = (y0 + 0.5) / 64, (y1 - 0.5) / 64
    return (u0, v1), (u1, v1), (u1, v0), (u0, v0)


def _append_accessor(
    binary: bytearray,
    buffer_views: list[dict[str, object]],
    accessors: list[dict[str, object]],
    values: Iterable[object],
    *,
    component_type: int,
    accessor_type: str,
    count: int,
    target: int,
    packer: struct.Struct,
    minimum: list[float] | None = None,
    maximum: list[float] | None = None,
) -> int:
    _align(binary)
    offset = len(binary)
    for value in values:
        if isinstance(value, tuple):
            binary.extend(packer.pack(*value))
        else:
            binary.extend(packer.pack(value))
    view_index = len(buffer_views)
    buffer_views.append(
        {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(binary) - offset,
            "target": target,
        }
    )
    accessor: dict[str, object] = {
        "bufferView": view_index,
        "byteOffset": 0,
        "componentType": component_type,
        "count": count,
        "type": accessor_type,
    }
    if minimum is not None:
        accessor["min"] = minimum
    if maximum is not None:
        accessor["max"] = maximum
    accessors.append(accessor)
    return len(accessors) - 1


def _align(buffer: bytearray) -> None:
    buffer.extend(b"\x00" * (-len(buffer) % 4))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lalo_core.skin_glb")
    parser.add_argument("skin", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    print(write_textured_skin_glb(arguments.skin, arguments.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
