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
        PaletteEntry(2, "web black", "#111111"),
        PaletteEntry(3, "eye white", "#F4F4F0"),
    )
    parts = tuple(
        PartAppearance(part.name, (_spider_surface(part),))
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


def _spider_surface(part: PartSpec) -> SurfaceMap:
    rows, columns = face_detail_shape(part, SurfaceFace.FRONT)
    materials = _grid(rows, columns, 0)
    relief = _grid(rows, columns, 0)
    if part.name == "head":
        _draw_web(materials, relief)
        _draw_spider_eyes(materials, relief)
    elif part.name == "torso":
        for row in range(rows):
            for column in range(columns):
                if row >= 38 or (row >= 24 and (column < 8 or column >= columns - 8)):
                    materials[row][column] = 1
        for row in range(8, 34, 10):
            _rectangle(materials, relief, row, row + 2, 4, columns - 4, 2, -1)
        _rectangle(materials, relief, 18, 44, columns // 2 - 2, columns // 2 + 2, 2, 1)
        _rectangle(materials, relief, 27, 31, columns // 2 - 7, columns // 2 + 7, 2, 1)
    elif any(token in part.name for token in ("thigh", "shin", "foot")):
        materials = _grid(rows, columns, 1)
    elif "upper_arm" in part.name:
        for row in range(rows * 2 // 3, rows):
            for column in range(columns):
                materials[row][column] = 1
    return _surface(materials, relief)


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


def _draw_web(materials: list[list[int]], relief: list[list[int]]) -> None:
    rows, columns = len(materials), len(materials[0])
    for row in range(0, rows, 10):
        _rectangle(materials, relief, row, min(row + 2, rows), 0, columns, 2, -1)
    center = columns // 2
    _rectangle(materials, relief, 0, rows, center - 1, center + 1, 2, -1)


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
    material: int,
    level: int,
) -> None:
    for row in range(max(0, row_start), min(len(materials), row_end)):
        for column in range(max(0, column_start), min(len(materials[0]), column_end)):
            materials[row][column] = material
            relief[row][column] = level


def _grid(rows: int, columns: int, value: int) -> list[list[int]]:
    return [[value for _ in range(columns)] for _ in range(rows)]


def _surface(materials: list[list[int]], relief: list[list[int]]) -> SurfaceMap:
    return SurfaceMap(
        SurfaceFace.FRONT,
        tuple(tuple(row) for row in relief),
        tuple(tuple(row) for row in materials),
    )
