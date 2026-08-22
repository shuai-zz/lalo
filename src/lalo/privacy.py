"""Privacy-safe lifecycle and reproducibility helpers for M2 planning."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from lalo.plan_json import character_plan_to_json
from lalo.planner import PlanRequest, PlannerCapabilities, PlanResult

_IMAGE_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@contextmanager
def transient_image_file(
    request: PlanRequest,
    *,
    parent_directory: str | os.PathLike[str] | None = None,
) -> Iterator[Path | None]:
    """Materialize an optional image privately and always remove the copy."""

    if request.image is None:
        yield None
        return
    with tempfile.TemporaryDirectory(
        prefix="lalo-image-", dir=parent_directory
    ) as temporary_directory:
        path = Path(temporary_directory) / (
            "input" + _IMAGE_SUFFIXES[request.image.media_type]
        )
        path.write_bytes(request.image.data)
        yield path


def planning_metadata(
    request: PlanRequest,
    result: PlanResult,
    capabilities: PlannerCapabilities,
    *,
    generator_version: str,
) -> dict[str, object]:
    """Build reproducibility metadata without retaining private request content."""

    if not isinstance(generator_version, str) or not generator_version.strip():
        raise ValueError("generator_version must not be empty")
    prompt_digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()
    plan_json = character_plan_to_json(result.plan).encode("utf-8")
    return {
        "schema_version": "1.0",
        "prompt_sha256": prompt_digest,
        "input": {
            "has_image": request.image is not None,
            "image_media_type": (
                request.image.media_type if request.image is not None else None
            ),
        },
        "planning": {
            "effective_seed": result.effective_seed,
            "provider_supports_seed": capabilities.supports_seed,
            "provider": result.provider,
            "model": result.model,
            "model_version": result.model_version,
        },
        "character_plan": {
            "schema_version": result.plan.schema_version,
            "sha256": hashlib.sha256(plan_json).hexdigest(),
        },
        "generator_version": generator_version,
    }


def planning_metadata_json(
    request: PlanRequest,
    result: PlanResult,
    capabilities: PlannerCapabilities,
    *,
    generator_version: str,
) -> str:
    """Serialize privacy-safe planning metadata deterministically."""

    return (
        json.dumps(
            planning_metadata(
                request,
                result,
                capabilities,
                generator_version=generator_version,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
