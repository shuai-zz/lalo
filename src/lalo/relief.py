"""Compile surface relief maps into fine voxel occupancy."""

from __future__ import annotations

from dataclasses import dataclass

from lalo.appearance import SilhouetteFeature, SurfaceFace, SurfaceMap
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
    part: PartSpec,
    surfaces: tuple[SurfaceMap, ...],
    silhouette_features: tuple[SilhouetteFeature, ...] = (),
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
        expected = face_detail_shape(part, surface.face)
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
                surface_cell = _surface_cell(surface.face, row, column, sizes, padding)
                if level > 0:
                    for distance in range(1, level + 1):
                        _set_cell(grid, surface_cell, normal, distance, True)
                else:
                    for distance in range(0, -level):
                        _set_cell(grid, surface_cell, normal, -distance, False)

    for feature_index, feature in enumerate(silhouette_features):
        _fuse_silhouette_feature(grid, feature, padding, feature_index)

    occupancy = tuple(
        tuple(tuple(cell for cell in row) for row in layer) for layer in grid
    )
    return DetailedPart(
        occupancy=occupancy,
        origin_detail_xyz=(-padding, -padding, -padding),
    )


def apply_relief_to_shape(
    part: PartSpec,
    shape: DetailedPart,
    surfaces: tuple[SurfaceMap, ...],
) -> DetailedPart:
    """Project relief along the actual boundary of a canonical custom shape."""

    size_x, size_y, size_z = (
        value * DETAIL_CELLS_PER_MASTER for value in part.size_xyz
    )
    actual_dimensions = (
        len(shape.occupancy),
        len(shape.occupancy[0]),
        len(shape.occupancy[0][0]),
    )
    if shape.origin_detail_xyz != (0, 0, 0) or actual_dimensions != (
        size_z,
        size_y,
        size_x,
    ):
        raise ValueError(
            f"custom shape {part.name} must exactly match its canonical detail envelope"
        )
    faces = tuple(surface.face for surface in surfaces)
    if len(set(faces)) != len(faces):
        raise ValueError("part relief contains duplicate surface faces")
    padding = _RELIEF_PADDING
    grid = [
        [
            [False for _ in range(size_x + padding * 2)]
            for _ in range(size_y + padding * 2)
        ]
        for _ in range(size_z + padding * 2)
    ]
    for z in range(size_z):
        for y in range(size_y):
            for x in range(size_x):
                grid[z + padding][y + padding][x + padding] = shape.occupancy[z][y][x]
    for surface in surfaces:
        expected = face_detail_shape(part, surface.face)
        actual = len(surface.relief), len(surface.relief[0])
        if actual != expected:
            raise ValueError(
                f"{part.name}.{surface.face.value} relief map must be "
                f"{expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}"
            )
        normal = _normal(surface.face)
        for row, values in enumerate(surface.relief):
            for column, level in enumerate(values):
                if level == 0:
                    continue
                boundary = _shape_boundary_cell(
                    shape.occupancy, surface.face, row, column
                )
                if boundary is None or not _locally_planar_boundary(
                    shape.occupancy, surface.face, row, column, boundary
                ):
                    continue
                padded = tuple(value + padding for value in boundary)
                if level > 0:
                    for distance in range(1, level + 1):
                        _set_cell(grid, padded, normal, distance, True)
                else:
                    for distance in range(-level):
                        _set_cell(grid, padded, normal, -distance, False)
    return DetailedPart(
        tuple(tuple(tuple(value for value in row) for row in layer) for layer in grid),
        (-padding, -padding, -padding),
    )


def _shape_boundary_cell(
    occupancy: OccupancyGrid,
    face: SurfaceFace,
    row: int,
    column: int,
) -> tuple[int, int, int] | None:
    size_z, size_y, size_x = (
        len(occupancy),
        len(occupancy[0]),
        len(occupancy[0][0]),
    )
    z = size_z - 1 - row
    if face in (SurfaceFace.FRONT, SurfaceFace.BACK):
        candidates = [y for y in range(size_y) if occupancy[z][y][column]]
        if not candidates:
            return None
        y = min(candidates) if face == SurfaceFace.FRONT else max(candidates)
        return column, y, z
    if face in (SurfaceFace.LEFT, SurfaceFace.RIGHT):
        candidates = [x for x in range(size_x) if occupancy[z][column][x]]
        if not candidates:
            return None
        x = max(candidates) if face == SurfaceFace.LEFT else min(candidates)
        return x, column, z
    if face == SurfaceFace.TOP:
        candidates = [
            z_value for z_value in range(size_z) if occupancy[z_value][row][column]
        ]
        return (column, row, max(candidates)) if candidates else None
    candidates = [
        z_value for z_value in range(size_z) if occupancy[z_value][row][column]
    ]
    return (column, row, min(candidates)) if candidates else None


def _locally_planar_boundary(
    occupancy: OccupancyGrid,
    face: SurfaceFace,
    row: int,
    column: int,
    boundary: tuple[int, int, int],
) -> bool:
    size_z, size_y, size_x = (
        len(occupancy),
        len(occupancy[0]),
        len(occupancy[0][0]),
    )
    max_rows = (
        size_z
        if face
        in (
            SurfaceFace.FRONT,
            SurfaceFace.BACK,
            SurfaceFace.LEFT,
            SurfaceFace.RIGHT,
        )
        else size_y
    )
    max_columns = (
        size_y
        if face
        in (
            SurfaceFace.LEFT,
            SurfaceFace.RIGHT,
        )
        else size_x
    )
    normal_axis = 1 if face in (SurfaceFace.FRONT, SurfaceFace.BACK) else 0
    if face in (SurfaceFace.TOP, SurfaceFace.BOTTOM):
        normal_axis = 2
    for next_row, next_column in (
        (row - 1, column),
        (row + 1, column),
        (row, column - 1),
        (row, column + 1),
    ):
        if not (0 <= next_row < max_rows and 0 <= next_column < max_columns):
            return False
        neighbor = _shape_boundary_cell(occupancy, face, next_row, next_column)
        if neighbor is None or neighbor[normal_axis] != boundary[normal_axis]:
            return False
    return True


def mesh_detailed_part(part: DetailedPart) -> Mesh:
    """Mesh fine occupancy in coordinates relative to the original part box."""

    mesh = mesh_occupancy(part.occupancy)
    ox, oy, oz = part.origin_detail_xyz
    return Mesh(
        vertices=tuple((x + ox, y + oy, z + oz) for x, y, z in mesh.vertices),
        faces=mesh.faces,
    )


def face_detail_shape(part: PartSpec, face: SurfaceFace) -> tuple[int, int]:
    """Return ``(rows, columns)`` required for one fine-grid part face."""

    size_x, size_y, size_z = (
        value * DETAIL_CELLS_PER_MASTER for value in part.size_xyz
    )
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


def _fuse_silhouette_feature(
    grid: list[list[list[bool]]],
    feature: SilhouetteFeature,
    padding: int,
    feature_index: int,
) -> None:
    origin = tuple(value + padding for value in feature.origin_detail_xyz)
    cells = tuple(
        (x, y, z)
        for z in range(origin[2], origin[2] + feature.size_detail_xyz[2])
        for y in range(origin[1], origin[1] + feature.size_detail_xyz[1])
        for x in range(origin[0], origin[0] + feature.size_detail_xyz[0])
    )
    depth, height, width = len(grid), len(grid[0]), len(grid[0][0])
    if any(
        x < 0 or x >= width or y < 0 or y >= height or z < 0 or z >= depth
        for x, y, z in cells
    ):
        raise ValueError(
            f"silhouette feature {feature_index} exceeds the two-cell padding envelope"
        )
    cell_set = set(cells)
    connected = False
    for x, y, z in cells:
        if grid[z][y][x]:
            connected = True
            break
        for dx, dy, dz in (
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
        ):
            neighbor = x + dx, y + dy, z + dz
            if neighbor in cell_set:
                continue
            nx, ny, nz = neighbor
            if (
                0 <= nx < width
                and 0 <= ny < height
                and 0 <= nz < depth
                and grid[nz][ny][nx]
            ):
                connected = True
                break
        if connected:
            break
    if not connected:
        raise ValueError(
            f"silhouette feature {feature_index} must face-connect to the part"
        )
    for x, y, z in cells:
        grid[z][y][x] = True
