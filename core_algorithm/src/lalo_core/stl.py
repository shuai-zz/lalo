"""Binary STL serialization for Lalo meshes."""

from __future__ import annotations

import math
import os
import struct
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

from lalo_core.meshing import Mesh, Vertex

_HEADER = b"Lalo binary STL".ljust(80, b"\0")
_TRIANGLE = struct.Struct("<12fH")


def binary_stl_bytes(mesh: Mesh, *, scale_mm: float = 1.0) -> bytes:
    """Serialize ``mesh`` as deterministic binary STL bytes.

    Coordinates are multiplied by ``scale_mm``. The STL format does not encode
    units, so callers and downstream consumers must interpret them as
    millimeters.
    """

    scale = _validate_scale(scale_mm)
    if len(mesh.faces) > 0xFFFFFFFF:
        raise ValueError("binary STL supports at most 4,294,967,295 triangles")

    output = bytearray(_HEADER)
    output.extend(struct.pack("<I", len(mesh.faces)))

    for face_index, face in enumerate(mesh.faces):
        vertices = _face_vertices(mesh, face, face_index)
        scaled = tuple(
            tuple(float(coordinate) * scale for coordinate in vertex)
            for vertex in vertices
        )
        normal = _unit_normal(*scaled, face_index=face_index)
        output.extend(
            _TRIANGLE.pack(
                *normal,
                *scaled[0],
                *scaled[1],
                *scaled[2],
                0,
            )
        )

    return bytes(output)


def write_binary_stl(
    mesh: Mesh,
    destination: str | os.PathLike[str] | BinaryIO,
    *,
    scale_mm: float = 1.0,
) -> None:
    """Write ``mesh`` to a path or a binary file-like object."""

    data = binary_stl_bytes(mesh, scale_mm=scale_mm)
    if isinstance(destination, (str, os.PathLike)):
        Path(destination).write_bytes(data)
        return

    write = getattr(destination, "write", None)
    if not isinstance(write, Callable):
        raise TypeError("destination must be a path or binary file-like object")
    try:
        written = write(data)
    except TypeError as error:
        raise TypeError("destination must accept binary data") from error
    if written is not None and written != len(data):
        raise OSError("destination did not write the complete STL payload")


def _validate_scale(scale_mm: float) -> float:
    if isinstance(scale_mm, bool) or not isinstance(scale_mm, (int, float)):
        raise TypeError("scale_mm must be a number")
    scale = float(scale_mm)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale_mm must be finite and greater than zero")
    return scale


def _face_vertices(
    mesh: Mesh, face: tuple[int, int, int], face_index: int
) -> tuple[Vertex, Vertex, Vertex]:
    if len(face) != 3:
        raise ValueError(f"face {face_index} must contain exactly three vertex indices")
    vertices: list[Vertex] = []
    for vertex_index in face:
        if isinstance(vertex_index, bool) or not isinstance(vertex_index, int):
            raise TypeError(f"face {face_index} contains a non-integer vertex index")
        if vertex_index < 0:
            raise ValueError(
                f"face {face_index} references missing vertex {vertex_index}"
            )
        try:
            vertices.append(mesh.vertices[vertex_index])
        except IndexError as error:
            raise ValueError(
                f"face {face_index} references missing vertex {vertex_index}"
            ) from error
    return vertices[0], vertices[1], vertices[2]


def _unit_normal(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
    *,
    face_index: int,
) -> tuple[float, float, float]:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    length = math.sqrt(sum(component * component for component in cross))
    if not math.isfinite(length) or length == 0:
        raise ValueError(f"face {face_index} is degenerate or has invalid coordinates")
    return tuple(component / length for component in cross)
