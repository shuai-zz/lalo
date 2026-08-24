"""Deterministic mesh extraction from voxel occupancy grids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, TypeAlias

Vertex: TypeAlias = tuple[int, int, int]
Face: TypeAlias = tuple[int, int, int]


@dataclass(frozen=True)
class Mesh:
    """An indexed triangle mesh in exact grid coordinates."""

    vertices: tuple[Vertex, ...]
    faces: tuple[Face, ...]


# Neighbor offset followed by the outward-wound corners of that voxel face.
_FACE_DEFINITIONS: tuple[
    tuple[Vertex, tuple[Vertex, Vertex, Vertex, Vertex]], ...
] = (
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
)


def mesh_occupancy(occupancy: Iterable[Iterable[Iterable[object]]]) -> Mesh:
    """Extract an axis-aligned triangle mesh from a binary occupancy grid.

    The input is indexed as ``occupancy[z][y][x]``. Every value must be a bool
    or the integer 0 or 1. Only faces between an occupied cell and an empty cell
    (or the grid boundary) are emitted. Vertices at identical grid coordinates
    are shared exactly.

    Raises:
        TypeError: If the input is not a three-dimensional iterable or contains
            values other than bool, 0, or 1.
        ValueError: If the grid is empty, ragged, or has no occupied cells.
    """

    grid = _normalize_grid(occupancy)
    depth = len(grid)
    height = len(grid[0])
    width = len(grid[0][0])

    vertices: list[Vertex] = []
    vertex_indices: dict[Vertex, int] = {}
    faces: list[Face] = []

    def occupied(x: int, y: int, z: int) -> bool:
        return (
            0 <= x < width
            and 0 <= y < height
            and 0 <= z < depth
            and grid[z][y][x]
        )

    def vertex_index(vertex: Vertex) -> int:
        if vertex not in vertex_indices:
            vertex_indices[vertex] = len(vertices)
            vertices.append(vertex)
        return vertex_indices[vertex]

    for z, layer in enumerate(grid):
        for y, row in enumerate(layer):
            for x, is_occupied in enumerate(row):
                if not is_occupied:
                    continue

                for (dx, dy, dz), corners in _FACE_DEFINITIONS:
                    if occupied(x + dx, y + dy, z + dz):
                        continue

                    quad = tuple(
                        vertex_index((x + cx, y + cy, z + cz))
                        for cx, cy, cz in corners
                    )
                    faces.append((quad[0], quad[1], quad[2]))
                    faces.append((quad[0], quad[2], quad[3]))

    if not faces:
        raise ValueError("occupancy grid must contain at least one occupied cell")

    return Mesh(vertices=tuple(vertices), faces=tuple(faces))


def _normalize_grid(
    occupancy: Iterable[Iterable[Iterable[object]]],
) -> tuple[tuple[tuple[bool, ...], ...], ...]:
    try:
        raw_layers = tuple(occupancy)
    except TypeError as error:
        raise TypeError("occupancy grid must be a three-dimensional iterable") from error

    if not raw_layers:
        raise ValueError("occupancy grid must not be empty")

    layers: list[tuple[tuple[bool, ...], ...]] = []
    expected_height: int | None = None
    expected_width: int | None = None

    for raw_layer in raw_layers:
        try:
            raw_rows = tuple(raw_layer)
        except TypeError as error:
            raise TypeError("occupancy grid must be a three-dimensional iterable") from error

        if not raw_rows:
            raise ValueError("occupancy grid dimensions must not be empty")
        if expected_height is None:
            expected_height = len(raw_rows)
        elif len(raw_rows) != expected_height:
            raise ValueError("occupancy grid must be rectangular")

        rows: list[tuple[bool, ...]] = []
        for raw_row in raw_rows:
            try:
                raw_values = tuple(raw_row)
            except TypeError as error:
                raise TypeError(
                    "occupancy grid must be a three-dimensional iterable"
                ) from error

            if not raw_values:
                raise ValueError("occupancy grid dimensions must not be empty")
            if expected_width is None:
                expected_width = len(raw_values)
            elif len(raw_values) != expected_width:
                raise ValueError("occupancy grid must be rectangular")

            values: list[bool] = []
            for value in raw_values:
                if not isinstance(value, (bool, int)) or value not in (0, 1):
                    raise TypeError("occupancy values must be bool, 0, or 1")
                values.append(bool(value))
            rows.append(tuple(values))
        layers.append(tuple(rows))

    return tuple(layers)
