"""Physical printability cleanup for surface relief maps."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from lalo.appearance import SurfaceMap
from lalo.generate import MASTER_HEIGHT_VOXELS
from lalo.relief import DETAIL_CELLS_PER_MASTER


@dataclass(frozen=True)
class PrintabilityResult:
    """A cleaned surface and counts of programmatic changes."""

    surface: SurfaceMap
    expanded_pixel_count: int
    depth_adjustment_count: int
    detail_pitch_mm: float


def clean_relief_for_fdm(
    surface: SurfaceMap,
    *,
    height_mm: float = 80.0,
    minimum_line_width_mm: float = 0.8,
    minimum_depth_mm: float = 0.4,
) -> PrintabilityResult:
    """Make non-zero relief meet bounded FDM width and depth constraints."""

    height = _positive_number("height_mm", height_mm)
    minimum_width = _positive_number(
        "minimum_line_width_mm", minimum_line_width_mm
    )
    minimum_depth = _positive_number("minimum_depth_mm", minimum_depth_mm)
    pitch = height / MASTER_HEIGHT_VOXELS / DETAIL_CELLS_PER_MASTER
    width_cells = math.ceil(minimum_width / pitch)
    depth_cells = math.ceil(minimum_depth / pitch)
    if depth_cells > 2:
        raise ValueError(
            "minimum relief depth cannot be represented by the -2..2 relief levels"
        )

    rows = len(surface.relief)
    columns = len(surface.relief[0])
    if any(level != 0 for row in surface.relief for level in row) and (
        width_cells > rows or width_cells > columns
    ):
        raise ValueError("minimum line width does not fit this surface map")

    relief = [list(row) for row in surface.relief]
    materials = [list(row) for row in surface.materials]
    depth_adjustments = 0
    for row in range(rows):
        for column in range(columns):
            level = relief[row][column]
            if level != 0 and abs(level) < depth_cells:
                relief[row][column] = depth_cells if level > 0 else -depth_cells
                depth_adjustments += 1

    source_relief = tuple(tuple(row) for row in relief)
    source_materials = surface.materials
    expanded = 0
    for component in _components(source_relief):
        if _component_meets_width(component, width_cells):
            continue
        for row, column in sorted(component):
            row_start = min(max(row - (width_cells - 1) // 2, 0), rows - width_cells)
            column_start = min(
                max(column - (width_cells - 1) // 2, 0), columns - width_cells
            )
            for target_row in range(row_start, row_start + width_cells):
                for target_column in range(column_start, column_start + width_cells):
                    if relief[target_row][target_column] != 0:
                        continue
                    relief[target_row][target_column] = source_relief[row][column]
                    materials[target_row][target_column] = source_materials[row][column]
                    expanded += 1

    cleaned = SurfaceMap(
        face=surface.face,
        relief=tuple(tuple(row) for row in relief),
        materials=tuple(tuple(row) for row in materials),
    )
    return PrintabilityResult(cleaned, expanded, depth_adjustments, pitch)


def _components(grid: tuple[tuple[int, ...], ...]) -> tuple[set[tuple[int, int]], ...]:
    rows, columns = len(grid), len(grid[0])
    unseen = {
        (row, column)
        for row in range(rows)
        for column in range(columns)
        if grid[row][column] != 0
    }
    components: list[set[tuple[int, int]]] = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        sign = 1 if grid[start[0]][start[1]] > 0 else -1
        component = {start}
        queue = deque((start,))
        while queue:
            row, column = queue.popleft()
            for neighbor in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if neighbor not in unseen:
                    continue
                if (1 if grid[neighbor[0]][neighbor[1]] > 0 else -1) != sign:
                    continue
                unseen.remove(neighbor)
                component.add(neighbor)
                queue.append(neighbor)
        components.append(component)
    return tuple(components)


def _component_meets_width(
    component: set[tuple[int, int]], width_cells: int
) -> bool:
    if width_cells <= 1:
        return True
    rows = [pixel[0] for pixel in component]
    columns = [pixel[1] for pixel in component]
    return (
        len(component) >= width_cells * width_cells
        and max(rows) - min(rows) + 1 >= width_cells
        and max(columns) - min(columns) + 1 >= width_cells
    )


def _positive_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return result
