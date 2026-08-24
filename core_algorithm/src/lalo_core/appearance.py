"""Provider-independent M1 character appearance plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from lalo_core.body import CANONICAL_PARTS

PixelGrid: TypeAlias = tuple[tuple[int, ...], ...]
_SRGB_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
_CANONICAL_PART_NAMES = frozenset(part.name for part in CANONICAL_PARTS)


class SurfaceFace(str, Enum):
    """Outward face names in canonical character coordinates."""

    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


@dataclass(frozen=True)
class PaletteEntry:
    """One indexed sRGB material color."""

    id: int
    name: str
    srgb: str

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 0:
            raise ValueError("palette id must be a non-negative integer")
        if not self.name.strip():
            raise ValueError("palette name must not be empty")
        if not _SRGB_PATTERN.fullmatch(self.srgb):
            raise ValueError("palette srgb must use #RRGGBB format")


@dataclass(frozen=True)
class SurfaceMap:
    """Relief levels and palette IDs for one rectangular part face."""

    face: SurfaceFace
    relief: PixelGrid
    materials: PixelGrid

    def __post_init__(self) -> None:
        _validate_grid("relief", self.relief, minimum=-2, maximum=2)
        _validate_grid("materials", self.materials, minimum=0, maximum=3)
        if _shape(self.relief) != _shape(self.materials):
            raise ValueError("relief and material maps must have identical dimensions")


@dataclass(frozen=True)
class SilhouetteFeature:
    """A compact fused box expressed in part-local detail-grid coordinates."""

    origin_detail_xyz: tuple[int, int, int]
    size_detail_xyz: tuple[int, int, int]
    material_id: int

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (*self.origin_detail_xyz, *self.size_detail_xyz)
        ):
            raise TypeError("silhouette origin and size values must be integers")
        if any(value <= 0 for value in self.size_detail_xyz):
            raise ValueError("silhouette size values must be greater than zero")
        if any(value > 10 for value in self.size_detail_xyz):
            raise ValueError("silhouette features must not exceed 10 detail cells per axis")
        if (
            isinstance(self.material_id, bool)
            or not isinstance(self.material_id, int)
            or not 0 <= self.material_id <= 3
        ):
            raise ValueError("silhouette material_id must be between 0 and 3")


@dataclass(frozen=True)
class PartAppearance:
    """Surface appearance maps belonging to one canonical body part."""

    part_name: str
    surfaces: tuple[SurfaceMap, ...]
    silhouette_features: tuple[SilhouetteFeature, ...] = ()

    def __post_init__(self) -> None:
        if self.part_name not in _CANONICAL_PART_NAMES:
            raise ValueError(f"unknown canonical part: {self.part_name}")
        faces = tuple(surface.face for surface in self.surfaces)
        if len(set(faces)) != len(faces):
            raise ValueError(f"part {self.part_name} contains duplicate surface faces")


@dataclass(frozen=True)
class CharacterPlan:
    """Complete constrained appearance input for deterministic M1 geometry."""

    schema_version: str
    name: str
    palette: tuple[PaletteEntry, ...]
    parts: tuple[PartAppearance, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported character plan schema_version")
        if not self.name.strip():
            raise ValueError("character plan name must not be empty")
        if not 1 <= len(self.palette) <= 4:
            raise ValueError("character palette must contain between one and four colors")
        palette_ids = tuple(entry.id for entry in self.palette)
        if palette_ids != tuple(range(len(self.palette))):
            raise ValueError("palette ids must be unique and contiguous from zero")
        part_names = tuple(part.part_name for part in self.parts)
        if len(set(part_names)) != len(part_names):
            raise ValueError("character plan contains duplicate parts")
        valid_materials = set(palette_ids)
        for part in self.parts:
            for surface in part.surfaces:
                referenced = {
                    material for row in surface.materials for material in row
                }
                if not referenced <= valid_materials:
                    raise ValueError(
                        f"surface {part.part_name}.{surface.face.value} references "
                        "a missing palette id"
                    )
            feature_materials = {
                feature.material_id for feature in part.silhouette_features
            }
            if not feature_materials <= valid_materials:
                raise ValueError(
                    f"part {part.part_name} silhouette references a missing palette id"
                )


def _validate_grid(name: str, grid: PixelGrid, *, minimum: int, maximum: int) -> None:
    if not isinstance(grid, tuple) or not grid:
        raise ValueError(f"{name} map must be a non-empty tuple grid")
    width: int | None = None
    for row in grid:
        if not isinstance(row, tuple) or not row:
            raise ValueError(f"{name} map rows must be non-empty tuples")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(f"{name} map must be rectangular")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} map values must be integers")
            if not minimum <= value <= maximum:
                raise ValueError(
                    f"{name} map values must be between {minimum} and {maximum}"
                )


def _shape(grid: PixelGrid) -> tuple[int, int]:
    return len(grid), len(grid[0])
