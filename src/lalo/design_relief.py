"""Conservative physical detail inference from design material structure."""

from __future__ import annotations

from dataclasses import replace

from lalo.appearance import CharacterPlan, PartAppearance, SurfaceFace, SurfaceMap
from lalo.design import CharacterRegion, IdentitySpec

_GLASSES_TERMS = (
    "glasses",
    "spectacles",
    "goggles",
    "eyewear",
    "眼镜",
    "镜框",
    "护目镜",
)


def infer_design_relief(identity: IdentitySpec, plan: CharacterPlan) -> CharacterPlan:
    """Engrave material boundaries and raise explicitly identified glasses."""

    glasses = any(
        feature.region == CharacterRegion.HEAD
        and any(
            term in f"{feature.name} {feature.description}".lower()
            for term in _GLASSES_TERMS
        )
        for feature in identity.features
    )
    darkest = min(
        plan.palette,
        key=lambda entry: sum(
            weight * int(entry.srgb[index : index + 2], 16)
            for weight, index in ((299, 1), (587, 3), (114, 5))
        ),
    ).id
    parts: list[PartAppearance] = []
    for part in plan.parts:
        surfaces = tuple(
            _surface_relief(
                surface,
                raise_glasses=glasses and part.part_name == "head",
                darkest=darkest,
            )
            for surface in part.surfaces
        )
        parts.append(replace(part, surfaces=surfaces))
    return replace(plan, parts=tuple(parts))


def _surface_relief(
    surface: SurfaceMap, *, raise_glasses: bool, darkest: int
) -> SurfaceMap:
    rows, columns = len(surface.materials), len(surface.materials[0])
    relief = [list(row) for row in surface.relief]
    margin = 2
    for row in range(margin, rows - margin):
        for column in range(margin, columns - margin):
            material = surface.materials[row][column]
            neighbors = (
                surface.materials[next_row][next_column]
                for next_row, next_column in (
                    (row - 1, column),
                    (row + 1, column),
                    (row, column - 1),
                    (row, column + 1),
                )
                if 0 <= next_row < rows and 0 <= next_column < columns
            )
            if relief[row][column] == 0 and any(
                neighbor < material for neighbor in neighbors
            ):
                relief[row][column] = -1
    if raise_glasses and surface.face == SurfaceFace.FRONT:
        start, end = rows * 3 // 10, rows * 7 // 10
        for row in range(start, end):
            for column in range(columns):
                if surface.materials[row][column] == darkest:
                    relief[row][column] = 1
    return SurfaceMap(
        surface.face,
        tuple(tuple(value for value in row) for row in relief),
        surface.materials,
    )
