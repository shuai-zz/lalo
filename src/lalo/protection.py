"""Relief keep-out masks for future joint interfaces."""

from __future__ import annotations

from dataclasses import dataclass

from lalo.appearance import PixelGrid, SurfaceFace, SurfaceMap
from lalo.body import PartSpec
from lalo.relief import DETAIL_CELLS_PER_MASTER, face_detail_shape

BooleanGrid = tuple[tuple[bool, ...], ...]


@dataclass(frozen=True)
class ProtectionMask:
    """Pixels where geometry-changing relief is forbidden on one face."""

    face: SurfaceFace
    protected: BooleanGrid


@dataclass(frozen=True)
class ProtectionResult:
    """Clipped surfaces plus the number of changed relief pixels."""

    surfaces: tuple[SurfaceMap, ...]
    clipped_pixel_count: int


def canonical_protection_masks(part: PartSpec) -> tuple[ProtectionMask, ...]:
    """Return placeholder keep-outs for the canonical reusable joint layout."""

    full_faces = _full_protected_faces(part.name)
    masks = [
        ProtectionMask(face, _filled(face_detail_shape(part, face), True))
        for face in full_faces
    ]
    if part.name == "torso":
        shoulder_rows = 4 * DETAIL_CELLS_PER_MASTER
        for face in (SurfaceFace.LEFT, SurfaceFace.RIGHT):
            rows, columns = face_detail_shape(part, face)
            masks.append(
                ProtectionMask(
                    face,
                    tuple(
                        tuple(row < shoulder_rows for _ in range(columns))
                        for row in range(rows)
                    ),
                )
            )
    return tuple(masks)


def clip_protected_relief(
    surfaces: tuple[SurfaceMap, ...], masks: tuple[ProtectionMask, ...]
) -> ProtectionResult:
    """Zero relief covered by masks without changing material assignments."""

    masks_by_face: dict[SurfaceFace, ProtectionMask] = {}
    for mask in masks:
        if mask.face in masks_by_face:
            raise ValueError(f"duplicate protection mask for {mask.face.value}")
        _validate_boolean_grid(mask)
        masks_by_face[mask.face] = mask

    clipped = 0
    output: list[SurfaceMap] = []
    for surface in surfaces:
        mask = masks_by_face.get(surface.face)
        if mask is None:
            output.append(surface)
            continue
        if _shape(mask.protected) != _shape(surface.relief):
            raise ValueError(
                f"protection mask for {surface.face.value} must match surface dimensions"
            )
        rows: list[tuple[int, ...]] = []
        for relief_row, mask_row in zip(surface.relief, mask.protected, strict=True):
            values: list[int] = []
            for level, is_protected in zip(relief_row, mask_row, strict=True):
                if is_protected and level != 0:
                    clipped += 1
                    values.append(0)
                else:
                    values.append(level)
            rows.append(tuple(values))
        output.append(
            SurfaceMap(
                face=surface.face,
                relief=tuple(rows),
                materials=surface.materials,
            )
        )
    return ProtectionResult(tuple(output), clipped)


def _full_protected_faces(part_name: str) -> tuple[SurfaceFace, ...]:
    if part_name == "head":
        return (SurfaceFace.BOTTOM,)
    if part_name == "torso":
        return SurfaceFace.TOP, SurfaceFace.BOTTOM
    if part_name.endswith("upper_arm") or part_name.endswith("forearm"):
        return SurfaceFace.TOP, SurfaceFace.BOTTOM
    if part_name.endswith("hand") or part_name.endswith("foot"):
        return (SurfaceFace.TOP,)
    if part_name.endswith("thigh") or part_name.endswith("shin"):
        return SurfaceFace.TOP, SurfaceFace.BOTTOM
    return ()


def _filled(shape: tuple[int, int], value: bool) -> BooleanGrid:
    rows, columns = shape
    return tuple(tuple(value for _ in range(columns)) for _ in range(rows))


def _validate_boolean_grid(mask: ProtectionMask) -> None:
    if not isinstance(mask.protected, tuple) or not mask.protected:
        raise ValueError("protection mask must be a non-empty tuple grid")
    width = len(mask.protected[0])
    if width == 0 or any(len(row) != width for row in mask.protected):
        raise ValueError("protection mask must be rectangular")
    if any(
        not isinstance(value, bool) for row in mask.protected for value in row
    ):
        raise TypeError("protection mask values must be bool")


def _shape(grid: PixelGrid | BooleanGrid) -> tuple[int, int]:
    return len(grid), len(grid[0])
