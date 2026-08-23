"""Command-line entry point for Lalo."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from lalo.design import CharacterDesigner, DesignRequest
from lalo.design_artifacts import write_design_artifacts
from lalo.designing import design_character
from lalo.openai_designer import OpenAIDesigner
from lalo.openai_planner import OpenAIHTTPTransport
from lalo.planner import ImageInput

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.command != "design":
        parser.print_help()
        return 0
    output = Path(arguments.output)
    if output.exists():
        parser.error(f"output already exists: {output}")
    try:
        request = DesignRequest(
            prompt=arguments.prompt,
            image=_read_image(arguments.image),
            seed=arguments.seed,
        )
        designer = _openai_designer_from_environment()
        result = design_character(request, designer)
        write_design_artifacts(output, request, result, designer.capabilities)
    except (OSError, TypeError, ValueError) as exc:
        print(f"lalo design failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lalo")
    commands = parser.add_subparsers(dest="command")
    design = commands.add_parser("design", help="generate inspectable 2D design views")
    design.add_argument("--prompt", required=True)
    design.add_argument("--image", type=Path)
    design.add_argument("--output", type=Path, required=True)
    design.add_argument("--seed", type=int, default=0)
    return parser


def _read_image(path: Path | None) -> ImageInput | None:
    if path is None:
        return None
    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise ValueError("image must be JPEG, PNG, or WebP")
    return ImageInput(path.read_bytes(), media_type)


def _openai_designer_from_environment() -> CharacterDesigner:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    transport = OpenAIHTTPTransport(
        api_key,
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    return OpenAIDesigner(
        vision_model=os.environ.get("LALO_OPENAI_VISION_MODEL", "gpt-5.4"),
        image_model=os.environ.get("LALO_OPENAI_IMAGE_MODEL", "gpt-image-2"),
        transport=transport,
        zero_retention=os.environ.get("LALO_OPENAI_ZERO_RETENTION") == "1",
    )
