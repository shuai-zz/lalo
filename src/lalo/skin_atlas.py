"""Convert a standard Minecraft skin atlas into a deterministic Lalo plan."""

from __future__ import annotations

from collections.abc import Iterable

from PIL import Image

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SurfaceFace,
    SurfaceMap,
)
from lalo.body import CANONICAL_PARTS, PartSpec
from lalo.relief import face_detail_shape

_RELIEF_LEVELS = {0: -2, 64: -1, 128: 0, 192: 1, 255: 2}

# Boxes use Pillow's (left, top, right, bottom) convention on a 64x64 atlas.
_FACE_BOXES: dict[str, dict[SurfaceFace, tuple[int, int, int, int]]] = {
    "head": {
        SurfaceFace.TOP: (8, 0, 16, 8),
        SurfaceFace.RIGHT: (0, 8, 8, 16),
        SurfaceFace.FRONT: (8, 8, 16, 16),
        SurfaceFace.LEFT: (16, 8, 24, 16),
        SurfaceFace.BACK: (24, 8, 32, 16),
    },
    "torso": {
        SurfaceFace.RIGHT: (16, 20, 20, 32),
        SurfaceFace.FRONT: (20, 20, 28, 32),
        SurfaceFace.LEFT: (28, 20, 32, 32),
        SurfaceFace.BACK: (32, 20, 40, 32),
    },
    "right_arm": {
        SurfaceFace.RIGHT: (40, 20, 44, 32),
        SurfaceFace.FRONT: (44, 20, 48, 32),
        SurfaceFace.LEFT: (48, 20, 52, 32),
        SurfaceFace.BACK: (52, 20, 56, 32),
    },
    "right_leg": {
        SurfaceFace.RIGHT: (0, 20, 4, 32),
        SurfaceFace.FRONT: (4, 20, 8, 32),
        SurfaceFace.LEFT: (8, 20, 12, 32),
        SurfaceFace.BACK: (12, 20, 16, 32),
    },
    "left_leg": {
        SurfaceFace.RIGHT: (16, 52, 20, 64),
        SurfaceFace.FRONT: (20, 52, 24, 64),
        SurfaceFace.LEFT: (24, 52, 28, 64),
        SurfaceFace.BACK: (28, 52, 32, 64),
    },
    "left_arm": {
        SurfaceFace.RIGHT: (32, 52, 36, 64),
        SurfaceFace.FRONT: (36, 52, 40, 64),
        SurfaceFace.LEFT: (40, 52, 44, 64),
        SurfaceFace.BACK: (44, 52, 48, 64),
    },
}

_PART_SOURCE: dict[str, tuple[str, int, int]] = {
    "head": ("head", 0, 8),
    "torso": ("torso", 0, 12),
    "left_upper_arm": ("left_arm", 0, 5),
    "left_forearm": ("left_arm", 5, 10),
    "left_hand": ("left_arm", 10, 12),
    "right_upper_arm": ("right_arm", 0, 5),
    "right_forearm": ("right_arm", 5, 10),
    "right_hand": ("right_arm", 10, 12),
    "left_thigh": ("left_leg", 0, 5),
    "left_shin": ("left_leg", 5, 10),
    "left_foot": ("left_leg", 10, 12),
    "right_thigh": ("right_leg", 0, 5),
    "right_shin": ("right_leg", 5, 10),
    "right_foot": ("right_leg", 10, 12),
}


def character_plan_from_skin_atlas(
    skin: Image.Image,
    *,
    name: str,
    palette: tuple[PaletteEntry, ...],
    relief_mask: Image.Image | None = None,
) -> CharacterPlan:
    """Map a 64x64 (or integer-scale) Minecraft skin onto Lalo body parts.

    ``relief_mask`` is optional grayscale artwork with the same dimensions. Its
    pixels must be one of 0, 64, 128, 192, or 255, mapping to relief -2..2.
    """

    scale = _atlas_scale(skin)
    if not 1 <= len(palette) <= 4:
        raise ValueError("palette must contain between one and four colors")
    if relief_mask is not None and relief_mask.size != skin.size:
        raise ValueError("relief mask dimensions must match the skin atlas")
    rgba = skin.convert("RGBA")
    mask = relief_mask.convert("L") if relief_mask is not None else None
    palette_labs = tuple(_hex_to_lab(entry.srgb) for entry in palette)

    appearances = tuple(
        _part_appearance(part, rgba, mask, palette_labs, scale)
        for part in CANONICAL_PARTS
    )
    return CharacterPlan("1.0", name, palette, appearances)


def _atlas_scale(image: Image.Image) -> int:
    width, height = image.size
    if width != height or width < 64 or width % 64:
        raise ValueError("skin atlas must be square and an integer multiple of 64x64")
    return width // 64


def _part_appearance(
    part: PartSpec,
    skin: Image.Image,
    mask: Image.Image | None,
    palette_labs: tuple[tuple[float, float, float], ...],
    scale: int,
) -> PartAppearance:
    source, row_start, row_end = _PART_SOURCE[part.name]
    surfaces = []
    for face, box in _FACE_BOXES[source].items():
        sliced = _slice_box(box, row_start, row_end, scale)
        output_shape = face_detail_shape(part, face)
        color_crop = skin.crop(sliced).resize(
            output_shape[::-1], Image.Resampling.NEAREST
        )
        materials = tuple(
            tuple(_nearest_palette(pixel, palette_labs) for pixel in row)
            for row in _rows(color_crop)
        )
        if mask is None:
            relief = tuple(tuple(0 for _ in row) for row in materials)
        else:
            mask_crop = mask.crop(sliced).resize(
                output_shape[::-1], Image.Resampling.NEAREST
            )
            relief = tuple(
                tuple(_relief_level(value) for value in row)
                for row in _rows(mask_crop)
            )
        surfaces.append(SurfaceMap(face, relief, materials))
    return PartAppearance(part.name, tuple(surfaces))


def _slice_box(
    box: tuple[int, int, int, int], row_start: int, row_end: int, scale: int
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    source_height = bottom - top
    if source_height != row_end - row_start:
        top += row_start
        bottom = top + row_end - row_start
    return left * scale, top * scale, right * scale, bottom * scale


def _rows(image: Image.Image) -> Iterable[tuple[object, ...]]:
    width, height = image.size
    pixels = image.load()
    assert pixels is not None
    return (tuple(pixels[x, y] for x in range(width)) for y in range(height))


def _relief_level(value: object) -> int:
    if not isinstance(value, int) or value not in _RELIEF_LEVELS:
        raise ValueError("relief mask pixels must be one of 0, 64, 128, 192, or 255")
    return _RELIEF_LEVELS[value]


def _nearest_palette(
    pixel: object, palette_labs: tuple[tuple[float, float, float], ...]
) -> int:
    red, green, blue, alpha = pixel  # type: ignore[misc]
    if alpha < 128:
        return 0
    lab = _rgb_to_lab(red, green, blue)
    return min(
        range(len(palette_labs)),
        key=lambda index: sum((a - b) ** 2 for a, b in zip(lab, palette_labs[index])),
    )


def _hex_to_lab(srgb: str) -> tuple[float, float, float]:
    return _rgb_to_lab(*(int(srgb[index : index + 2], 16) for index in (1, 3, 5)))


def _rgb_to_lab(red: int, green: int, blue: int) -> tuple[float, float, float]:
    channels = tuple(
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in (red / 255, green / 255, blue / 255)
    )
    x = (
        channels[0] * 0.4124564
        + channels[1] * 0.3575761
        + channels[2] * 0.1804375
    ) / 0.95047
    y = channels[0] * 0.2126729 + channels[1] * 0.7151522 + channels[2] * 0.072175
    z = (
        channels[0] * 0.0193339
        + channels[1] * 0.119192
        + channels[2] * 0.9503041
    ) / 1.08883

    def pivot(value: float) -> float:
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    fx, fy, fz = pivot(x), pivot(y), pivot(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)
