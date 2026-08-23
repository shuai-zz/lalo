"""Deterministic packaging for complete printable artifact directories."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

_ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def write_artifact_zip(
    artifact_directory: str | os.PathLike[str], *, filename: str = "result.zip"
) -> Path:
    """Package every existing artifact file with stable metadata and ordering."""

    root = Path(artifact_directory)
    if not root.is_dir():
        raise ValueError("artifact_directory must be an existing directory")
    output = root / filename
    files = tuple(
        sorted(
            (path for path in root.rglob("*") if path.is_file() and path != output),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )
    if not files:
        raise ValueError("artifact_directory contains no files to package")
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=1,
        ) as archive:
            for path in files:
                relative = path.relative_to(root).as_posix()
                info = zipfile.ZipInfo(relative, _ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes(), compresslevel=1)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output
