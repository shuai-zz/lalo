"""Generate repeatable image-first review artifacts for a directory of sheets."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from lalo_core.skin_glb import write_textured_skin_glb
from lalo_core.skin_sampling import sample_skin_sheet


def evaluate_skin_sheets(
    source_directory: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    *,
    scale: int = 4,
) -> Path:
    """Generate skin, review, GLB, and a manifest for every PNG sheet."""

    source_root = Path(source_directory)
    output = Path(destination)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if not source_root.is_dir():
        raise ValueError(f"source directory does not exist: {source_root}")
    sources = tuple(sorted(source_root.glob("*.png"), key=lambda path: path.name))
    if not sources:
        raise ValueError("source directory must contain at least one PNG sheet")
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise ValueError("scale must be a positive integer")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temporary:
        staging = Path(temporary) / output.name
        staging.mkdir()
        samples: list[dict[str, object]] = []
        for source in sources:
            sample_name = source.stem
            sample_output = staging / sample_name
            artifacts = sample_skin_sheet(source, sample_output, scale=scale)
            glb = write_textured_skin_glb(
                artifacts.skin, sample_output / "preview.glb"
            )
            samples.append(
                {
                    "name": sample_name,
                    "source": str(source.resolve()),
                    "skin": str(artifacts.skin.relative_to(staging)),
                    "review_sheet": str(artifacts.review_sheet.relative_to(staging)),
                    "glb": str(glb.relative_to(staging)),
                }
            )
        manifest = staging / "manifest.json"
        manifest.write_text(
            json.dumps(
                {"format_version": 1, "scale": scale, "samples": samples},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        staging.replace(output)
    return output / "manifest.json"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lalo_core.skin_batch")
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=int, default=4)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    print(
        evaluate_skin_sheets(
            arguments.source_directory, arguments.output, scale=arguments.scale
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
