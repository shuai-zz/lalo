"""Privacy-safe, atomic persistence for inspectable design-stage artifacts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from pathlib import Path

from PIL import Image

from lalo.design import DesignerCapabilities, DesignRequest, DesignResult


def write_design_artifacts(
    output_directory: str | os.PathLike[str],
    request: DesignRequest,
    result: DesignResult,
    capabilities: DesignerCapabilities,
) -> Path:
    """Write a complete design package without retaining private request content."""

    output = Path(output_directory)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}-", dir=output.parent
    ) as tmp:
        temporary = Path(tmp) / output.name
        temporary.mkdir()
        (temporary / "identity.json").write_text(
            _identity_json(result), encoding="utf-8"
        )
        for view in result.sheet.views:
            (temporary / f"{view.name.value}.png").write_bytes(view.image.data)
        (temporary / "sheet.png").write_bytes(_joined_sheet_png(result))
        (temporary / "design-metadata.json").write_text(
            _metadata_json(request, result, capabilities), encoding="utf-8"
        )
        temporary.replace(output)
    return output


def _identity_json(result: DesignResult) -> str:
    identity = result.identity
    document = {
        "schema_version": identity.schema_version,
        "name": identity.name,
        "summary": identity.summary,
        "palette": [
            {"id": entry.id, "name": entry.name, "srgb": entry.srgb}
            for entry in identity.palette
        ],
        "features": [
            {
                "name": feature.name,
                "region": feature.region.value,
                "description": feature.description,
                "importance": feature.importance.value,
            }
            for feature in identity.features
        ],
    }
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _metadata_json(
    request: DesignRequest,
    result: DesignResult,
    capabilities: DesignerCapabilities,
) -> str:
    document = {
        "schema_version": "1.0",
        "prompt_sha256": hashlib.sha256(request.prompt.encode()).hexdigest(),
        "input": {
            "has_image": request.image is not None,
            "image_media_type": (
                request.image.media_type if request.image is not None else None
            ),
        },
        "design": {
            "effective_seed": result.effective_seed,
            "provider": result.provider,
            "model": result.model,
            "model_version": result.model_version,
            "provider_supports_seed": capabilities.supports_seed,
            "subject_count": result.subject_count,
        },
    }
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _joined_sheet_png(result: DesignResult) -> bytes:
    panels: list[Image.Image] = []
    try:
        for view in result.sheet.views:
            with Image.open(io.BytesIO(view.image.data)) as panel:
                panels.append(panel.convert("RGB"))
        width, height = panels[0].size
        if any(panel.size != (width, height) for panel in panels):
            raise ValueError("design views must have identical decoded dimensions")
        sheet = Image.new("RGB", (width * len(panels), height))
        for index, panel in enumerate(panels):
            sheet.paste(panel, (index * width, 0))
        encoded = io.BytesIO()
        sheet.save(encoded, format="PNG")
        return encoded.getvalue()
    except OSError as exc:
        raise ValueError("design views must contain readable image data") from exc
    finally:
        for panel in panels:
            panel.close()
