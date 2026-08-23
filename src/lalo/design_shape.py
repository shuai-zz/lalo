"""Bounded voxel shape inference from canonical orthographic silhouettes."""

from __future__ import annotations

import io

from PIL import Image

from lalo.body import CANONICAL_PARTS
from lalo.design import DesignViewName
from lalo.design_crops import DesignPartCrop, DesignPartCrops
from lalo.relief import DETAIL_CELLS_PER_MASTER, DetailedPart, mesh_detailed_part
from lalo.validation import validate_mesh

_HEAD = next(part for part in CANONICAL_PARTS if part.name == "head")
_HEAD_SIZE = _HEAD.size_xyz[0] * DETAIL_CELLS_PER_MASTER
_PROTECTED_BOTTOM_LAYERS = DETAIL_CELLS_PER_MASTER


def compile_head_visual_hull(crops: DesignPartCrops) -> DetailedPart:
    """Intersect four aligned head silhouettes inside the canonical envelope."""

    head_crops = {crop.view: crop for crop in crops.crops if crop.part_name == "head"}
    if set(head_crops) != set(DesignViewName):
        raise ValueError("head visual hull requires front, back, left, and right crops")
    masks = {
        view: _resampled_alpha(head_crops[view], _HEAD_SIZE, _HEAD_SIZE)
        for view in DesignViewName
    }
    grid: list[list[list[bool]]] = []
    for z in range(_HEAD_SIZE):
        if z < _PROTECTED_BOTTOM_LAYERS:
            grid.append([[True for _ in range(_HEAD_SIZE)] for _ in range(_HEAD_SIZE)])
            continue
        row = _HEAD_SIZE - 1 - z
        x_projection = tuple(
            masks[DesignViewName.FRONT][row][x] and masks[DesignViewName.BACK][row][x]
            for x in range(_HEAD_SIZE)
        )
        y_projection = tuple(
            masks[DesignViewName.LEFT][row][y] and masks[DesignViewName.RIGHT][row][y]
            for y in range(_HEAD_SIZE)
        )
        grid.append(
            [
                [x_projection[x] and y_projection[y] for x in range(_HEAD_SIZE)]
                for y in range(_HEAD_SIZE)
            ]
        )
    result = DetailedPart(
        occupancy=tuple(
            tuple(tuple(value for value in row) for row in layer) for layer in grid
        ),
        origin_detail_xyz=(0, 0, 0),
    )
    validation = validate_mesh(mesh_detailed_part(result))
    if not validation.valid or validation.component_count != 1:
        raise ValueError("head visual hull must produce one watertight component")
    return result


def _resampled_alpha(
    crop: DesignPartCrop, width: int, height: int
) -> tuple[tuple[bool, ...], ...]:
    try:
        with Image.open(io.BytesIO(crop.image.data)) as source:
            rgba = source.convert("RGBA")
    except OSError as exc:
        raise ValueError(f"{crop.view.value} head crop is not readable") from exc
    alpha = rgba.getchannel("A").resize((width, height), Image.Resampling.BOX)
    rgba.close()
    mask = tuple(
        tuple(alpha.getpixel((x, y)) >= 64 for x in range(width)) for y in range(height)
    )
    alpha.close()
    if not any(value for row in mask for value in row):
        raise ValueError(f"{crop.view.value} head silhouette is empty")
    return mask
