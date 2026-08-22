"""Voxel occupancy primitives."""

from __future__ import annotations

from typing import TypeAlias

OccupancyGrid: TypeAlias = tuple[tuple[tuple[bool, ...], ...], ...]


def solid_cuboid(width: int, height: int, depth: int) -> OccupancyGrid:
    """Return a solid immutable cuboid indexed as ``grid[z][y][x]``."""

    dimensions = {"width": width, "height": height, "depth": depth}
    for name, value in dimensions.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")

    row = (True,) * width
    layer = (row,) * height
    return (layer,) * depth
