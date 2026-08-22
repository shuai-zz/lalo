"""End-to-end M2 planning and deterministic artifact generation."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from dataclasses import dataclass
from pathlib import Path

from lalo.generate import DEFAULT_HEIGHT_MM
from lalo.m1 import M1Artifacts, generate_m1_artifacts
from lalo.plan_json import character_plan_to_json
from lalo.planner import CharacterPlanner, PlanRequest
from lalo.planning import plan_character
from lalo.privacy import planning_metadata

try:
    GENERATOR_VERSION = importlib.metadata.version("lalo")
except importlib.metadata.PackageNotFoundError:
    GENERATOR_VERSION = "0.0.0"


@dataclass(frozen=True)
class M2Artifacts:
    """Paths produced by a successful provider-to-printable M2 run."""

    m1: M1Artifacts
    provider_plan_path: Path
    planning_metadata_path: Path


def generate_m2_artifacts(
    request: PlanRequest,
    planner: CharacterPlanner,
    output_directory: str | os.PathLike[str],
    *,
    height_mm: float = DEFAULT_HEIGHT_MM,
    generator_version: str = GENERATOR_VERSION,
) -> M2Artifacts:
    """Plan one character and compile its complete printable artifact set."""

    output = Path(output_directory)
    _require_empty_output(output)
    result = plan_character(request, planner)
    artifacts = generate_m1_artifacts(
        result.plan, output, height_mm=height_mm
    )

    provider_plan_text = character_plan_to_json(result.plan)
    provider_plan_path = output / "provider_character_plan.json"
    provider_plan_path.write_text(provider_plan_text, encoding="utf-8")

    metadata = planning_metadata(
        request,
        result,
        planner.capabilities,
        generator_version=generator_version,
    )
    plan_metadata = metadata["character_plan"]
    assert isinstance(plan_metadata, dict)
    plan_metadata["file"] = provider_plan_path.name
    plan_metadata["byte_size"] = len(provider_plan_text.encode("utf-8"))
    plan_metadata["sha256"] = hashlib.sha256(
        provider_plan_text.encode("utf-8")
    ).hexdigest()
    planning_metadata_path = output / "planning_metadata.json"
    planning_metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return M2Artifacts(
        m1=artifacts,
        provider_plan_path=provider_plan_path,
        planning_metadata_path=planning_metadata_path,
    )


def _require_empty_output(output: Path) -> None:
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError("output path must be absent or an empty directory")
