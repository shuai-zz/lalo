"""Canonical humanoid body-part definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PartSpec:
    """A body part's size and assembled minimum corner in master voxels."""

    name: str
    size_xyz: tuple[int, int, int]
    origin_xyz: tuple[int, int, int]


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
    PartSpec("left_foot", (4, 6, 2), (0, -4, 0)),
    PartSpec("right_foot", (4, 6, 2), (-4, -4, 0)),
)
