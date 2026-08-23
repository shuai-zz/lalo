"""Deterministic hand-authored character plans for M1 regression tests."""

from __future__ import annotations

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SurfaceFace,
    SurfaceMap,
)
from lalo.body import CANONICAL_PARTS, PartSpec
from lalo.relief import face_detail_shape


def spider_man_plan() -> CharacterPlan:
    """Return a printable four-color Spider-Man regression fixture."""

    palette = (
        PaletteEntry(0, "spider red", "#C51D34"),
        PaletteEntry(1, "suit blue", "#174A8B"),
        PaletteEntry(2, "eye outline black", "#111111"),
        PaletteEntry(3, "eye white", "#F4F4F0"),
    )
    parts = tuple(
        PartAppearance(part.name, _spider_surfaces(part))
        for part in CANONICAL_PARTS
    )
    return CharacterPlan("1.0", "Spider-Man", palette, parts)


def iron_man_plan() -> CharacterPlan:
    """Return a printable four-color Iron Man regression fixture."""

    palette = (
        PaletteEntry(0, "armor red", "#A71930"),
        PaletteEntry(1, "armor gold", "#D6A536"),
        PaletteEntry(2, "panel dark", "#241A1C"),
        PaletteEntry(3, "reactor cyan", "#87F4FF"),
    )
    parts = tuple(
        PartAppearance(part.name, (_iron_surface(part),))
        for part in CANONICAL_PARTS
    )
    return CharacterPlan("1.0", "Iron Man", palette, parts)


def _spider_surfaces(part: PartSpec) -> tuple[SurfaceMap, ...]:
    """Build named identity layers on every character-visible suit face."""

    faces = (
        SurfaceFace.FRONT,
        SurfaceFace.BACK,
        SurfaceFace.LEFT,
        SurfaceFace.RIGHT,
    )
    if part.name == "head":
        faces += (SurfaceFace.TOP,)
    return tuple(_spider_surface(part, face) for face in faces)


def _spider_surface(part: PartSpec, face: SurfaceFace) -> SurfaceMap:
    rows, columns = face_detail_shape(part, face)
    materials = _grid(rows, columns, 0)
    relief = _grid(rows, columns, 0)
    if part.name == "head":
        _draw_mask_web(materials, relief)
        if face == SurfaceFace.FRONT:
            _draw_spider_eyes(materials, relief)
        elif face == SurfaceFace.TOP:
            # Keep the top web in the material map. Relief on this face would
            # intersect all four engraved side maps at the cube perimeter.
            relief = _grid(rows, columns, 0)
    elif part.name == "torso" and face == SurfaceFace.FRONT:
        for row in range(rows):
            for column in range(columns):
                if row >= 38 or (row >= 24 and (column < 8 or column >= columns - 8)):
                    materials[row][column] = 1
        _draw_torso_web(materials, relief)
        _draw_spider_emblem(materials, relief)
    elif part.name == "torso" and face == SurfaceFace.BACK:
        materials = _grid(rows, columns, 1)
        _rectangle(materials, relief, 0, 13, 0, columns, 0, 0)
        _draw_spider_emblem(materials, relief)
    elif part.name == "torso":
        materials = _grid(rows, columns, 1)
        _rectangle(materials, relief, 0, rows * 2 // 5, 0, columns, 0, 0)
        _draw_simple_web(materials, relief, 0, rows * 2 // 5)
    elif "thigh" in part.name:
        materials = _grid(rows, columns, 1)
    elif "shin" in part.name:
        materials = _grid(rows, columns, 1)
        for row in range(rows * 3 // 5, rows):
            for column in range(columns):
                materials[row][column] = 0
        _draw_boot_web(materials, relief)
    elif "foot" in part.name:
        materials = _grid(rows, columns, 0)
        _draw_simple_web(materials, relief, 0, rows)
    elif "upper_arm" in part.name:
        for row in range(rows * 2 // 3, rows):
            for column in range(columns):
                materials[row][column] = 1
        _draw_simple_web(materials, relief, 0, rows * 2 // 3)
    elif any(token in part.name for token in ("forearm", "hand")):
        _draw_simple_web(materials, relief, 0, rows)
    return _surface(materials, relief, face)


def _iron_surface(part: PartSpec) -> SurfaceMap:
    rows, columns = face_detail_shape(part, SurfaceFace.FRONT)
    materials = _grid(rows, columns, 0)
    relief = _grid(rows, columns, 0)
    if part.name == "head":
        _rectangle(materials, relief, 7, 35, 6, 34, 1, 0)
        _rectangle(materials, relief, 16, 20, 9, 17, 3, 1)
        _rectangle(materials, relief, 16, 20, 23, 31, 3, 1)
        _rectangle(materials, relief, 29, 31, 14, 26, 2, -1)
    elif part.name == "torso":
        _rectangle(materials, relief, 5, 50, 7, columns - 7, 1, 0)
        _rectangle(materials, relief, 20, 34, 14, 26, 2, -1)
        _rectangle(materials, relief, 23, 31, 16, 24, 3, 1)
    elif any(token in part.name for token in ("hand", "foot")):
        materials = _grid(rows, columns, 1)
    else:
        for row in range(rows * 3 // 4, rows):
            for column in range(columns):
                materials[row][column] = 1
    return _surface(materials, relief)


def _draw_mask_web(materials: list[list[int]], relief: list[list[int]]) -> None:
    """Draw radial, concentric mask webbing instead of a rectangular grid."""

    rows, columns = len(materials), len(materials[0])
    center = (rows // 2, columns // 2)
    for endpoint in (
        (3, columns // 2),
        (3, 3),
        (rows // 2, 3),
        (rows - 4, 3),
        (rows - 4, columns // 2),
        (rows - 4, columns - 4),
        (rows // 2, columns - 4),
        (3, columns - 4),
    ):
        _draw_orthogonal_line(materials, relief, center, endpoint, None, -1)

    for radius in (8, 15):
        ring = (
            (center[0] - radius, center[1]),
            (center[0] - radius * 2 // 3, center[1] + radius * 2 // 3),
            (center[0], center[1] + radius),
            (center[0] + radius * 2 // 3, center[1] + radius * 2 // 3),
            (center[0] + radius, center[1]),
            (center[0] + radius * 2 // 3, center[1] - radius * 2 // 3),
            (center[0], center[1] - radius),
            (center[0] - radius * 2 // 3, center[1] - radius * 2 // 3),
        )
        for start, end in zip(ring, ring[1:] + ring[:1]):
            _draw_orthogonal_line(materials, relief, start, end, None, -1)


def _draw_torso_web(materials: list[list[int]], relief: list[list[int]]) -> None:
    """Add collar webbing while keeping the central emblem visually clear."""

    columns = len(materials[0])
    center = columns // 2
    for row, inset in ((6, 4), (12, 6)):
        _draw_line(materials, relief, (row, inset), (row + 2, center - 6), None, -1)
        _draw_line(
            materials,
            relief,
            (row + 2, center + 5),
            (row, columns - inset - 1),
            None,
            -1,
        )


def _draw_spider_emblem(
    materials: list[list[int]], relief: list[list[int]]
) -> None:
    """Engrave an eight-legged spider without changing suit color."""

    columns = len(materials[0])
    center = columns // 2
    _rectangle(materials, relief, 19, 22, center - 1, center + 1, None, -1)
    _rectangle(materials, relief, 22, 26, center - 2, center + 2, None, -1)
    _rectangle(materials, relief, 26, 30, center - 1, center + 1, None, -1)

    left_legs = (
        ((21, center - 1), (18, center - 4), (17, center - 8)),
        ((23, center - 2), (21, center - 5), (21, center - 8)),
        ((25, center - 2), (27, center - 5), (28, center - 8)),
        ((28, center - 1), (30, center - 4), (33, center - 7)),
    )
    for points in left_legs:
        for start, end in zip(points, points[1:]):
            _draw_orthogonal_line(materials, relief, start, end, None, -1)
            _draw_orthogonal_line(
                materials,
                relief,
                (start[0], columns - 2 - start[1]),
                (end[0], columns - 2 - end[1]),
                None,
                -1,
            )


def _draw_orthogonal_line(
    materials: list[list[int]],
    relief: list[list[int]],
    start: tuple[int, int],
    end: tuple[int, int],
    material: int | None,
    level: int,
) -> None:
    """Rasterize an edge-connected two-cell-wide voxel stair step."""

    corner = end[0], start[1]
    for first, second in ((start, corner), (corner, end)):
        _rectangle(
            materials,
            relief,
            min(first[0], second[0]),
            max(first[0], second[0]) + 2,
            min(first[1], second[1]),
            max(first[1], second[1]) + 2,
            material,
            level,
        )


def _draw_simple_web(
    materials: list[list[int]],
    relief: list[list[int]],
    row_start: int,
    row_end: int,
) -> None:
    """Draw a low-density web that remains legible on narrow limb faces."""

    columns = len(materials[0])
    margin = 3
    if row_end - row_start <= margin * 2 or columns <= margin * 2:
        return
    center = columns // 2
    safe_start = row_start + margin
    safe_end = row_end - margin - 1
    _draw_line(materials, relief, (safe_start, center), (safe_end, margin), None, -1)
    _draw_line(
        materials,
        relief,
        (safe_start, center),
        (safe_end, columns - margin - 1),
        None,
        -1,
    )
    spacing = max(6, (row_end - row_start) // 3)
    for row in range(safe_start + spacing, safe_end, spacing):
        _draw_line(
            materials, relief, (row, margin), (row, columns - margin - 1), None, -1
        )


def _draw_boot_web(materials: list[list[int]], relief: list[list[int]]) -> None:
    """Continue subtle engraved web lines across the red boot region."""

    rows, columns = len(materials), len(materials[0])
    red_start = rows * 3 // 5
    margin = 3
    _draw_line(
        materials,
        relief,
        (red_start + margin, columns // 2),
        (rows - margin - 1, margin),
        None,
        -1,
    )
    _draw_line(
        materials,
        relief,
        (red_start + margin, columns // 2),
        (rows - margin - 1, columns - margin - 1),
        None,
        -1,
    )
    for row in range(red_start + margin + 4, rows - margin, 7):
        _draw_line(
            materials, relief, (row, margin), (row, columns - margin - 1), None, -1
        )


def _draw_line(
    materials: list[list[int]],
    relief: list[list[int]],
    start: tuple[int, int],
    end: tuple[int, int],
    material: int | None,
    level: int,
) -> None:
    """Rasterize a printable two-cell-wide line with integer arithmetic."""

    row, column = start
    end_row, end_column = end
    delta_column = abs(end_column - column)
    column_step = 1 if column < end_column else -1
    delta_row = -abs(end_row - row)
    row_step = 1 if row < end_row else -1
    error = delta_column + delta_row
    while True:
        _rectangle(materials, relief, row, row + 2, column, column + 2, material, level)
        if row == end_row and column == end_column:
            break
        doubled = 2 * error
        if doubled >= delta_row:
            error += delta_row
            column += column_step
        if doubled <= delta_column:
            error += delta_column
            row += row_step


def _draw_spider_eyes(
    materials: list[list[int]], relief: list[list[int]]
) -> None:
    """Draw mirrored tapered eyes as printable fine-grid voxel masks."""

    columns = len(materials[0])
    left_profile = (
        (14, 16),
        (13, 16),
        (12, 16),
        (11, 16),
        (10, 16),
        (9, 16),
        (8, 16),
        (7, 16),
        (7, 15),
        (8, 15),
        (8, 14),
        (9, 14),
        (9, 13),
        (10, 13),
        (10, 12),
    )
    white_cells: set[tuple[int, int]] = set()
    for row, (start, end) in enumerate(left_profile, start=10):
        for column in range(start, end):
            white_cells.add((row, column))
            white_cells.add((row, columns - 1 - column))

    outline_cells = {
        (row + row_offset, column + column_offset)
        for row, column in white_cells
        for row_offset in range(-2, 3)
        for column_offset in range(-2, 3)
        if 0 <= row + row_offset < len(materials)
        and 0 <= column + column_offset < columns
    }
    eye_clearance = {
        (row + row_offset, column + column_offset)
        for row, column in outline_cells
        for row_offset in range(-1, 2)
        for column_offset in range(-1, 2)
        if 0 <= row + row_offset < len(materials)
        and 0 <= column + column_offset < columns
    }
    for row, column in eye_clearance:
        relief[row][column] = 0
    for row, column in outline_cells - white_cells:
        materials[row][column] = 2
        relief[row][column] = 1
    for row, column in white_cells:
        materials[row][column] = 3
        relief[row][column] = 1


def _rectangle(
    materials: list[list[int]],
    relief: list[list[int]],
    row_start: int,
    row_end: int,
    column_start: int,
    column_end: int,
    material: int | None,
    level: int,
) -> None:
    for row in range(max(0, row_start), min(len(materials), row_end)):
        for column in range(max(0, column_start), min(len(materials[0]), column_end)):
            if material is not None:
                materials[row][column] = material
            relief[row][column] = level


def _grid(rows: int, columns: int, value: int) -> list[list[int]]:
    return [[value for _ in range(columns)] for _ in range(rows)]


def _surface(
    materials: list[list[int]],
    relief: list[list[int]],
    face: SurfaceFace = SurfaceFace.FRONT,
) -> SurfaceMap:
    return SurfaceMap(
        face,
        tuple(tuple(row) for row in relief),
        tuple(tuple(row) for row in materials),
    )
