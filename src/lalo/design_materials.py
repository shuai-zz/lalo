"""Deterministic palette sampling from canonical design-part crops."""

from __future__ import annotations

import io
from collections import deque

from PIL import Image

from lalo.appearance import CharacterPlan, PartAppearance, SurfaceFace, SurfaceMap
from lalo.body import CANONICAL_PARTS
from lalo.design import DesignViewName, IdentitySpec
from lalo.design_crops import DesignPartCrop, DesignPartCrops
from lalo.relief import face_detail_shape

_VIEW_FACES = {
    DesignViewName.FRONT: SurfaceFace.FRONT,
    DesignViewName.BACK: SurfaceFace.BACK,
    DesignViewName.LEFT: SurfaceFace.LEFT,
    DesignViewName.RIGHT: SurfaceFace.RIGHT,
}


def sample_design_materials(
    identity: IdentitySpec, crops: DesignPartCrops
) -> CharacterPlan:
    """Build a zero-relief CharacterPlan from four-view projected colors."""

    by_key = {(crop.part_name, crop.view): crop for crop in crops.crops}
    parts: list[PartAppearance] = []
    for part in CANONICAL_PARTS:
        surfaces: list[SurfaceMap] = []
        for view in DesignViewName:
            face = _VIEW_FACES[view]
            shape = face_detail_shape(part, face)
            materials = _sample_crop(by_key[(part.name, view)], shape, identity)
            relief = tuple(tuple(0 for _ in row) for row in materials)
            surfaces.append(SurfaceMap(face, relief, materials))
        parts.append(PartAppearance(part.name, tuple(surfaces)))
    return CharacterPlan("1.0", identity.name, identity.palette, tuple(parts))


def _sample_crop(
    crop: DesignPartCrop,
    shape: tuple[int, int],
    identity: IdentitySpec,
) -> tuple[tuple[int, ...], ...]:
    try:
        with Image.open(io.BytesIO(crop.image.data)) as source:
            rgba = source.convert("RGBA")
    except OSError as exc:
        raise ValueError(f"part crop {crop.part_name} is not a readable image") from exc
    if rgba.size != (crop.image.width, crop.image.height):
        rgba.close()
        raise ValueError(f"part crop {crop.part_name} dimensions do not match")
    filled = _fill_transparent_pixels(rgba)
    rgba.close()
    rows, columns = shape
    sampled = filled.resize((columns, rows), Image.Resampling.BOX)
    filled.close()
    palette = tuple((_hex_rgb(entry.srgb), entry.id) for entry in identity.palette)
    output = tuple(
        tuple(
            _nearest_palette(sampled.getpixel((column, row)), palette)
            for column in range(columns)
        )
        for row in range(rows)
    )
    sampled.close()
    return output


def _fill_transparent_pixels(image: Image.Image) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    seen = bytearray(width * height)
    queue: deque[int] = deque()
    for y in range(height):
        for x in range(width):
            if pixels[x, y][3] > 0:
                index = y * width + x
                seen[index] = 1
                queue.append(index)
    if not queue:
        raise ValueError("part crop contains no foreground pixels")
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        color = pixels[x, y][:3]
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if not (0 <= next_x < width and 0 <= next_y < height):
                continue
            neighbor = next_y * width + next_x
            if seen[neighbor] == 0:
                seen[neighbor] = 1
                pixels[next_x, next_y] = (*color, 255)
                queue.append(neighbor)
    return image.convert("RGB")


def _hex_rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def _nearest_palette(
    color: tuple[int, int, int],
    palette: tuple[tuple[tuple[int, int, int], int], ...],
) -> int:
    return min(
        palette,
        key=lambda entry: (
            sum(
                (component - target) ** 2 for component, target in zip(color, entry[0])
            ),
            entry[1],
        ),
    )[1]
