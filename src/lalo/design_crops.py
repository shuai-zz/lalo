"""Deterministic canonical part crops from orthographic character views."""

from __future__ import annotations

import io
import math
from collections import deque
from dataclasses import dataclass
from statistics import median

from PIL import Image

from lalo.body import CANONICAL_PARTS, PartSpec
from lalo.design import (
    CharacterSheet,
    DesignRaster,
    DesignViewName,
)


@dataclass(frozen=True)
class DesignPartCrop:
    """One lossless part crop and its pixel box in the source view."""

    part_name: str
    view: DesignViewName
    image: DesignRaster
    source_box: tuple[int, int, int, int]

    def __post_init__(self) -> None:
        if self.part_name not in {part.name for part in CANONICAL_PARTS}:
            raise ValueError(f"unknown canonical part: {self.part_name}")
        if not isinstance(self.view, DesignViewName):
            raise TypeError("part crop view must be a DesignViewName")
        if not isinstance(self.image, DesignRaster):
            raise TypeError("part crop image must be a DesignRaster")
        left, top, right, bottom = self.source_box
        if min(left, top) < 0 or right <= left or bottom <= top:
            raise ValueError("part crop source_box must have positive area")


@dataclass(frozen=True)
class DesignPartCrops:
    """All canonical part crops in stable view-major order."""

    crops: tuple[DesignPartCrop, ...]

    def __post_init__(self) -> None:
        expected = tuple(
            (view, part.name) for view in DesignViewName for part in CANONICAL_PARTS
        )
        actual = tuple((crop.view, crop.part_name) for crop in self.crops)
        if actual != expected:
            raise ValueError(
                "part crops must contain every canonical part in view-major order"
            )


def crop_design_parts(
    sheet: CharacterSheet, *, background_tolerance: int = 24
) -> DesignPartCrops:
    """Locate each figure and crop its canonical projected part rectangles."""

    if isinstance(background_tolerance, bool) or not isinstance(
        background_tolerance, int
    ):
        raise TypeError("background_tolerance must be an integer")
    if not 0 <= background_tolerance <= 255:
        raise ValueError("background_tolerance must be between 0 and 255")
    crops: list[DesignPartCrop] = []
    for view in sheet.views:
        image = _decode_raster(view.image)
        figure_box = _largest_foreground_box(image, background_tolerance)
        for part in CANONICAL_PARTS:
            source_box = _part_box(part, view.name, figure_box)
            cropped = image.crop(source_box)
            encoded = io.BytesIO()
            cropped.save(encoded, format="PNG")
            crops.append(
                DesignPartCrop(
                    part.name,
                    view.name,
                    DesignRaster(
                        encoded.getvalue(),
                        "image/png",
                        cropped.width,
                        cropped.height,
                    ),
                    source_box,
                )
            )
        image.close()
    return DesignPartCrops(tuple(crops))


def _decode_raster(raster: DesignRaster) -> Image.Image:
    try:
        with Image.open(io.BytesIO(raster.data)) as source:
            image = source.convert("RGB")
    except OSError as exc:
        raise ValueError("design view is not a readable image") from exc
    if image.size != (raster.width, raster.height):
        image.close()
        raise ValueError("design view decoded dimensions do not match its contract")
    return image


def _largest_foreground_box(
    image: Image.Image, tolerance: int
) -> tuple[int, int, int, int]:
    width, height = image.size
    if width < 8 or height < 32:
        raise ValueError("design view is too small for canonical part cropping")
    pixels = image.load()
    border = [pixels[x, 0] for x in range(width)]
    border.extend(pixels[x, height - 1] for x in range(width))
    border.extend(pixels[0, y] for y in range(1, height - 1))
    border.extend(pixels[width - 1, y] for y in range(1, height - 1))
    background = tuple(int(median(channel)) for channel in zip(*border))
    foreground = bytearray(width * height)
    for y in range(height):
        offset = y * width
        for x in range(width):
            if max(abs(a - b) for a, b in zip(pixels[x, y], background)) > tolerance:
                foreground[offset + x] = 1

    best: tuple[int, int, int, int, int] | None = None
    for start in range(width * height):
        if foreground[start] != 1:
            continue
        foreground[start] = 2
        queue = deque((start,))
        count = 0
        min_x = max_x = start % width
        min_y = max_y = start // width
        while queue:
            index = queue.popleft()
            x, y = index % width, index // width
            count += 1
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = next_y * width + next_x
                    if foreground[neighbor] == 1:
                        foreground[neighbor] = 2
                        queue.append(neighbor)
        component = (count, min_x, min_y, max_x + 1, max_y + 1)
        if best is None or component[0] > best[0]:
            best = component
    if best is None:
        raise ValueError("design view has no foreground character")
    count, left, top, right, bottom = best
    if count < 32 or right - left < 4 or bottom - top < 16:
        raise ValueError("design view foreground character is too small")
    return left, top, right, bottom


def _part_box(
    part: PartSpec,
    view: DesignViewName,
    figure_box: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    figure_left, figure_top, figure_right, figure_bottom = figure_box
    figure_width = figure_right - figure_left
    figure_height = figure_bottom - figure_top
    if view in (DesignViewName.FRONT, DesignViewName.BACK):
        axis_origin, axis_size = part.origin_xyz[0], part.size_xyz[0]
        axis_min, axis_max = -8, 8
        reverse = view == DesignViewName.BACK
    else:
        axis_origin, axis_size = part.origin_xyz[1], part.size_xyz[1]
        axis_min, axis_max = -4, 4
        reverse = view == DesignViewName.RIGHT
    axis_start = axis_origin
    axis_end = axis_origin + axis_size
    if reverse:
        axis_start, axis_end = (
            axis_max - axis_end + axis_min,
            axis_max - axis_start + axis_min,
        )
    left = figure_left + math.floor(
        (axis_start - axis_min) / (axis_max - axis_min) * figure_width
    )
    right = figure_left + math.ceil(
        (axis_end - axis_min) / (axis_max - axis_min) * figure_width
    )
    part_bottom = part.origin_xyz[2]
    part_top = part_bottom + part.size_xyz[2]
    top = figure_top + math.floor((32 - part_top) / 32 * figure_height)
    bottom = figure_top + math.ceil((32 - part_bottom) / 32 * figure_height)
    left = max(figure_left, min(left, figure_right - 1))
    right = max(left + 1, min(right, figure_right))
    top = max(figure_top, min(top, figure_bottom - 1))
    bottom = max(top + 1, min(bottom, figure_bottom))
    return left, top, right, bottom
