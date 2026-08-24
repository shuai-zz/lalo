"""Sample a strict front/back block-character sheet into a Minecraft skin."""

from __future__ import annotations

import argparse
import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageOps


@dataclass(frozen=True)
class SkinArtifacts:
    skin: Path
    review_sheet: Path


@dataclass(frozen=True)
class _Box:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


_UV = {
    "head": {"top": (8, 0, 16, 8), "bottom": (16, 0, 24, 8), "right": (0, 8, 8, 16), "front": (8, 8, 16, 16), "left": (16, 8, 24, 16), "back": (24, 8, 32, 16)},
    "torso": {"top": (20, 16, 28, 20), "bottom": (28, 16, 36, 20), "right": (16, 20, 20, 32), "front": (20, 20, 28, 32), "left": (28, 20, 32, 32), "back": (32, 20, 40, 32)},
    "right_arm": {"top": (44, 16, 48, 20), "bottom": (48, 16, 52, 20), "right": (40, 20, 44, 32), "front": (44, 20, 48, 32), "left": (48, 20, 52, 32), "back": (52, 20, 56, 32)},
    "right_leg": {"top": (4, 16, 8, 20), "bottom": (8, 16, 12, 20), "right": (0, 20, 4, 32), "front": (4, 20, 8, 32), "left": (8, 20, 12, 32), "back": (12, 20, 16, 32)},
    "left_leg": {"top": (20, 48, 24, 52), "bottom": (24, 48, 28, 52), "right": (16, 52, 20, 64), "front": (20, 52, 24, 64), "left": (24, 52, 28, 64), "back": (28, 52, 32, 64)},
    "left_arm": {"top": (36, 48, 40, 52), "bottom": (40, 48, 44, 52), "right": (32, 52, 36, 64), "front": (36, 52, 40, 64), "left": (40, 52, 44, 64), "back": (44, 52, 48, 64)},
}


def sample_skin_sheet(
    source: str | os.PathLike[str], output: str | os.PathLike[str], *, scale: int = 1
) -> SkinArtifacts:
    """Convert a two- or four-panel sheet into an editable scaled skin."""

    destination = Path(output)
    if destination.exists():
        raise FileExistsError(f"output already exists: {destination}")
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise ValueError("scale must be a positive integer")
    image = Image.open(source).convert("RGB")
    boxes = _foreground_boxes(image)
    if len(boxes) not in (2, 4):
        raise ValueError(
            "source must contain exactly two or four separated full-body figures"
        )
    ordered = sorted(boxes, key=lambda box: box.left)
    common_height = max(box.height for box in ordered)
    calibrated = tuple(
        _Box(box.left, box.top, box.right, box.top + common_height) for box in ordered
    )
    front_box = calibrated[0]
    back_box = calibrated[1] if len(calibrated) == 2 else calibrated[2]
    front = _part_crops(image, front_box)
    back = _part_crops(image, back_box)
    right = _side_part_crops(image, calibrated[1]) if len(calibrated) == 4 else None
    left = _side_part_crops(image, calibrated[3]) if len(calibrated) == 4 else None

    skin = Image.new("RGBA", (64 * scale, 64 * scale), (0, 0, 0, 0))
    for part in _UV:
        _paint_part(
            skin,
            part,
            front[part],
            back[part],
            right=None if right is None else right[part],
            left=None if left is None else left[part],
        )

    review = _review_sheet(skin)
    destination.mkdir(parents=True)
    skin_path = destination / "skin.png"
    review_path = destination / "review-sheet.png"
    skin.save(skin_path, format="PNG", optimize=False)
    review.save(review_path, format="PNG", optimize=False)
    return SkinArtifacts(skin_path, review_path)


def _foreground_boxes(image: Image.Image) -> tuple[_Box, ...]:
    pixels = image.load()
    corners = (
        pixels[0, 0], pixels[image.width - 1, 0],
        pixels[0, image.height - 1], pixels[image.width - 1, image.height - 1],
    )
    background = tuple(sum(color[channel] for color in corners) // 4 for channel in range(3))
    foreground = {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if sum((pixels[x, y][channel] - background[channel]) ** 2 for channel in range(3)) > 30**2
    }
    components: list[set[tuple[int, int]]] = []
    while foreground:
        start = foreground.pop()
        component = {start}
        queue = deque((start,))
        while queue:
            x, y = queue.popleft()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in foreground:
                    foreground.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        if len(component) >= image.width * image.height // 200:
            components.append(component)
    boxes = [
        _Box(
            min(x for x, _ in component), min(y for _, y in component),
            max(x for x, _ in component) + 1, max(y for _, y in component) + 1,
        )
        for component in components
    ]
    return tuple(
        sorted(boxes, key=lambda box: box.width * box.height, reverse=True)[:4]
    )


def _part_crops(image: Image.Image, box: _Box) -> dict[str, Image.Image]:
    head_end = box.top + round(box.height * 8 / 32)
    torso_end = box.top + round(box.height * 20 / 32)
    head_search_end = box.top + round(box.height * 7 / 32)
    head_box = _content_box(
        image, _Box(box.left, box.top, box.right, head_search_end)
    )
    center_left, center_right = head_box.left, head_box.right
    middle = (center_left + center_right) // 2
    return {
        "head": image.crop((head_box.left, box.top, head_box.right, head_end)),
        "torso": image.crop((center_left, head_end, center_right, torso_end)),
        "right_arm": image.crop((box.left, head_end, center_left, torso_end)),
        "left_arm": image.crop((center_right, head_end, box.right, torso_end)),
        "right_leg": image.crop((center_left, torso_end, middle, box.bottom)),
        "left_leg": image.crop((middle, torso_end, center_right, box.bottom)),
    }


def _side_part_crops(image: Image.Image, box: _Box) -> dict[str, Image.Image]:
    head_end = box.top + round(box.height * 8 / 32)
    torso_end = box.top + round(box.height * 20 / 32)
    head = _crop_content(
        image, _Box(box.left, box.top, box.right, head_end)
    )
    middle = _crop_content(
        image, _Box(box.left, head_end, box.right, torso_end)
    )
    lower = _crop_content(
        image, _Box(box.left, torso_end, box.right, box.bottom)
    )
    return {
        "head": ImageOps.mirror(head),
        "torso": ImageOps.mirror(middle),
        "right_arm": ImageOps.mirror(middle),
        "left_arm": ImageOps.mirror(middle),
        "right_leg": ImageOps.mirror(lower),
        "left_leg": ImageOps.mirror(lower),
    }


def _crop_content(image: Image.Image, search: _Box) -> Image.Image:
    content = _content_box(image, search)
    return image.crop((content.left, search.top, content.right, search.bottom))


def _content_box(image: Image.Image, search: _Box) -> _Box:
    pixels = image.load()
    corners = (
        pixels[0, 0], pixels[image.width - 1, 0],
        pixels[0, image.height - 1], pixels[image.width - 1, image.height - 1],
    )
    background = tuple(
        sum(color[channel] for color in corners) // 4 for channel in range(3)
    )
    points = [
        (x, y)
        for y in range(search.top, min(search.bottom, image.height))
        for x in range(search.left, min(search.right, image.width))
        if sum(
            (pixels[x, y][channel] - background[channel]) ** 2
            for channel in range(3)
        ) > 30**2
    ]
    if not points:
        raise ValueError("figure contains an empty canonical body region")
    return _Box(
        min(x for x, _ in points), min(y for _, y in points),
        max(x for x, _ in points) + 1, max(y for _, y in points) + 1,
    )


def _paint_part(
    skin: Image.Image,
    part: str,
    front: Image.Image,
    back: Image.Image,
    *,
    right: Image.Image | None,
    left: Image.Image | None,
) -> None:
    faces = _UV[part]
    _paste(skin, faces["front"], front)
    _paste(skin, faces["back"], back)
    _paste(
        skin,
        faces["right"],
        right if right is not None else _side_texture(front, back, left=True),
    )
    _paste(
        skin,
        faces["left"],
        left if left is not None else _side_texture(front, back, left=False),
    )
    _paste(skin, faces["top"], _cap_texture(front, top=True))
    _paste(skin, faces["bottom"], _cap_texture(front, top=False))


def _paste(canvas: Image.Image, rectangle: tuple[int, int, int, int], source: Image.Image) -> None:
    scale = canvas.width // 64
    target = tuple(coordinate * scale for coordinate in rectangle)
    width = target[2] - target[0]
    height = target[3] - target[1]
    canvas.paste(source.resize((width, height), Image.Resampling.LANCZOS).convert("RGBA"), target)


def _side_texture(front: Image.Image, back: Image.Image, *, left: bool) -> Image.Image:
    edge = max(1, round(front.width * 0.2))
    front_edge = front.crop((0 if left else front.width - edge, 0, edge if left else front.width, front.height))
    back_edge = back.crop((back.width - edge if left else 0, 0, back.width if left else edge, back.height))
    width = max(front_edge.width, back_edge.width)
    height = max(front_edge.height, back_edge.height)
    a = front_edge.resize((width, height), Image.Resampling.LANCZOS)
    b = back_edge.resize((width, height), Image.Resampling.LANCZOS)
    return Image.blend(a, b, 0.5)


def _cap_texture(source: Image.Image, *, top: bool) -> Image.Image:
    height = max(1, round(source.height * 0.12))
    return source.crop((0, 0 if top else source.height - height, source.width, height if top else source.height))


def _face(skin: Image.Image, part: str, face: str) -> Image.Image:
    scale = skin.width // 64
    return skin.crop(tuple(coordinate * scale for coordinate in _UV[part][face]))


def _orthographic(skin: Image.Image, face: str, scale: int = 8) -> Image.Image:
    canvas = Image.new("RGB", (16 * scale, 32 * scale), "white")
    placements = (
        ("head", 4, 0), ("right_arm", 0, 8), ("torso", 4, 8),
        ("left_arm", 12, 8), ("right_leg", 4, 20), ("left_leg", 8, 20),
    )
    for part, x, y in placements:
        texture = _face(skin, part, face).resize(
            ((8 if part in ("head", "torso") else 4) * scale,
             (8 if part == "head" else 12) * scale),
            Image.Resampling.NEAREST,
        )
        canvas.paste(texture.convert("RGB"), (x * scale, y * scale))
    return canvas


def _side_view(skin: Image.Image, face: str, scale: int = 8) -> Image.Image:
    canvas = Image.new("RGB", (8 * scale, 32 * scale), "white")
    canvas.paste(_face(skin, "head", face).resize((8 * scale, 8 * scale), Image.Resampling.NEAREST).convert("RGB"), (0, 0))
    canvas.paste(_face(skin, "torso", face).resize((4 * scale, 12 * scale), Image.Resampling.NEAREST).convert("RGB"), (2 * scale, 8 * scale))
    arm = "left_arm" if face == "left" else "right_arm"
    canvas.paste(_face(skin, arm, face).resize((4 * scale, 12 * scale), Image.Resampling.NEAREST).convert("RGB"), (2 * scale, 8 * scale))
    leg = "left_leg" if face == "left" else "right_leg"
    canvas.paste(_face(skin, leg, face).resize((4 * scale, 12 * scale), Image.Resampling.NEAREST).convert("RGB"), (2 * scale, 20 * scale))
    return canvas


def _three_quarter(skin: Image.Image, *, back: bool) -> Image.Image:
    primary = _orthographic(skin, "back" if back else "front", scale=7)
    side = _side_view(skin, "left" if back else "right", scale=7)
    canvas = Image.new("RGB", (primary.width + side.width, primary.height), "white")
    canvas.paste(primary, (0, 0))
    canvas.paste(side, (primary.width, 0))
    return canvas


def _review_sheet(skin: Image.Image) -> Image.Image:
    views = (
        ("FRONT", _orthographic(skin, "front")),
        ("BACK", _orthographic(skin, "back")),
        ("LEFT", _side_view(skin, "left")),
        ("RIGHT", _side_view(skin, "right")),
        ("FRONT + SIDE", _three_quarter(skin, back=False)),
        ("BACK + SIDE", _three_quarter(skin, back=True)),
    )
    cell_width, cell_height = 300, 310
    sheet = Image.new("RGB", (cell_width * 3, cell_height * 2), (238, 238, 238))
    draw = ImageDraw.Draw(sheet)
    for index, (label, view) in enumerate(views):
        column, row = index % 3, index // 3
        x = column * cell_width + (cell_width - view.width) // 2
        y = row * cell_height + 30 + (cell_height - 35 - view.height) // 2
        sheet.paste(view, (x, y))
        draw.text((column * cell_width + 10, row * cell_height + 8), label, fill="black")
    return sheet


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lalo_core.skin_sampling")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=int, default=1)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    artifacts = sample_skin_sheet(arguments.source, arguments.output, scale=arguments.scale)
    print(artifacts.skin)
    print(artifacts.review_sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
