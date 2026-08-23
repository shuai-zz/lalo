"""Canonical humanoid body-part definitions."""

from __future__ import annotations

from dataclasses import dataclass

from lalo.meshing import Mesh, mesh_occupancy
from lalo.voxel import solid_cuboid


@dataclass(frozen=True)
class PartSpec:
    """A body part's size and assembled minimum corner in master voxels."""

    name: str
    size_xyz: tuple[int, int, int]
    origin_xyz: tuple[int, int, int]


DEFAULT_LEG_GAP_MM = 0.8


def assembly_translation_mm(
    part: PartSpec,
    master_scale_mm: float,
    *,
    leg_gap_mm: float = DEFAULT_LEG_GAP_MM,
) -> tuple[float, float, float]:
    """Return a neutral assembly translation with symmetric leg separation."""

    x, y, z = (value * master_scale_mm for value in part.origin_xyz)
    if any(token in part.name for token in ("thigh", "shin", "foot")):
        x += leg_gap_mm / 2 if part.name.startswith("left_") else -leg_gap_mm / 2
    return x, y, z


def mesh_part(part: PartSpec) -> Mesh:
    """Compile a body part into a solid mesh at its local origin."""

    size_x, size_y, size_z = part.size_xyz
    occupancy = solid_cuboid(width=size_x, height=size_y, depth=size_z)
    return mesh_occupancy(occupancy)


# X points toward the character's anatomical left, Y points backward (the
# character faces negative Y), and Z points up from the ground plane.
CANONICAL_PARTS: tuple[PartSpec, ...] = (
    PartSpec("head", (8, 8, 8), (-4, -4, 24)),
    PartSpec("torso", (8, 4, 12), (-4, -2, 12)),
    PartSpec("left_upper_arm", (4, 4, 5), (4, -2, 19)),
    PartSpec("right_upper_arm", (4, 4, 5), (-8, -2, 19)),
    PartSpec("left_forearm", (4, 4, 5), (4, -2, 14)),
    PartSpec("right_forearm", (4, 4, 5), (-8, -2, 14)),
    PartSpec("left_hand", (4, 4, 2), (4, -2, 12)),
    PartSpec("right_hand", (4, 4, 2), (-8, -2, 12)),
    PartSpec("left_thigh", (4, 4, 5), (0, -2, 7)),
    PartSpec("right_thigh", (4, 4, 5), (-4, -2, 7)),
    PartSpec("left_shin", (4, 4, 5), (0, -2, 2)),
    PartSpec("right_shin", (4, 4, 5), (-4, -2, 2)),
    PartSpec("left_foot", (4, 4, 2), (0, -2, 0)),
    PartSpec("right_foot", (4, 4, 2), (-4, -2, 0)),
)
