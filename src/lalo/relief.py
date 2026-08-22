"""Compile surface relief maps into fine voxel occupancy."""

from __future__ import annotations

from dataclasses import dataclass

from lalo.appearance import SurfaceFace, SurfaceMap
from lalo.body import PartSpec
from lalo.meshing import Mesh, mesh_occupancy
from lalo.voxel import OccupancyGrid

DETAIL_CELLS_PER_MASTER = 5
_RELIEF_PADDING = 2


@dataclass(frozen=True)
class DetailedPart:
    """Fine occupancy plus its origin relative to the part's master-voxel box."""

    occupancy: OccupancyGrid
    origin_detail_xyz: tuple[int, int, int]


def compile_part_relief(
    part: PartSpec, surfaces: tuple[SurfaceMap, ...]
) -> DetailedPart:
    """Apply face-normal relief maps to a solid fine-grid part."""

    faces = tuple(surface.face for surface in surfaces)
    if len(set(faces)) != len(faces):
        raise ValueError("part relief contains duplicate surface faces")

    size_x, size_y, size_z = (
        value * DETAIL_CELLS_PER_MASTER for value in part.size_xyz
    )
    padding = _RELIEF_PADDING
    grid = [
        [
            [False for _ in range(size_x + padding * 2)]
            for _ in range(size_y + padding * 2)
        ]
        for _ in range(size_z + padding * 2)
    ]
    for z in range(padding, padding + size_z):
        for y in range(padding, padding + size_y):
            for x in range(padding, padding + size_x):
                grid[z][y][x] = True

    sizes = size_x, size_y, size_z
    for surface in surfaces:
        expected = _expected_shape(surface.face, sizes)
        actual = len(surface.relief), len(surface.relief[0])
        if actual != expected:
            raise ValueError(
                f"{part.name}.{surface.face.value} relief map must be "
                f"{expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}"
            )
        normal = _normal(surface.face)
        for row, relief_row in enumerate(surface.relief):
            for column, level in enumerate(relief_row):
                if level == 0:
                    continue
                surface_cell = _surface_cell(
                    surface.face, row, column, sizes, padding
                )
                if level > 0:
                    for distance in range(1, level + 1):
                        _set_cell(grid, surface_cell, normal, distance, True)
                else:
                    for distance in range(0, -level):
                        _set_cell(grid, surface_cell, normal, -distance, False)

    occupancy = tuple(
        tuple(tuple(cell for cell in row) for row in layer) for layer in grid
    )
    return DetailedPart(
        occupancy=occupancy,
        origin_detail_xyz=(-padding, -padding, -padding),
    )


def mesh_detailed_part(part: DetailedPart) -> Mesh:
    """Mesh fine occupancy in coordinates relative to the original part box."""

    mesh = mesh_occupancy(part.occupancy)
    ox, oy, oz = part.origin_detail_xyz
    return Mesh(
        vertices=tuple((x + ox, y + oy, z + oz) for x, y, z in mesh.vertices),
        faces=mesh.faces,
    )


def _expected_shape(
    face: SurfaceFace, sizes: tuple[int, int, int]
) -> tuple[int, int]:
    size_x, size_y, size_z = sizes
    if face in (SurfaceFace.FRONT, SurfaceFace.BACK):
        return size_z, size_x
    if face in (SurfaceFace.LEFT, SurfaceFace.RIGHT):
        return size_z, size_y
    return size_y, size_x


def _normal(face: SurfaceFace) -> tuple[int, int, int]:
    return {
        SurfaceFace.FRONT: (0, -1, 0),
        SurfaceFace.BACK: (0, 1, 0),
        SurfaceFace.LEFT: (1, 0, 0),
        SurfaceFace.RIGHT: (-1, 0, 0),
        SurfaceFace.TOP: (0, 0, 1),
        SurfaceFace.BOTTOM: (0, 0, -1),
    }[face]


def _surface_cell(
    face: SurfaceFace,
    row: int,
    column: int,
    sizes: tuple[int, int, int],
    padding: int,
) -> tuple[int, int, int]:
    size_x, size_y, size_z = sizes
    if face == SurfaceFace.FRONT:
        return padding + column, padding, padding + size_z - 1 - row
    if face == SurfaceFace.BACK:
        return padding + column, padding + size_y - 1, padding + size_z - 1 - row
    if face == SurfaceFace.LEFT:
        return padding + size_x - 1, padding + column, padding + size_z - 1 - row
    if face == SurfaceFace.RIGHT:
        return padding, padding + column, padding + size_z - 1 - row
    if face == SurfaceFace.TOP:
        return padding + column, padding + row, padding + size_z - 1
    return padding + column, padding + row, padding


def _set_cell(
    grid: list[list[list[bool]]],
    surface_cell: tuple[int, int, int],
    normal: tuple[int, int, int],
    distance: int,
    value: bool,
) -> None:
    x = surface_cell[0] + normal[0] * distance
    y = surface_cell[1] + normal[1] * distance
    z = surface_cell[2] + normal[2] * distance
    grid[z][y][x] = value
