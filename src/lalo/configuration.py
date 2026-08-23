"""Offline provider discovery and environment validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse


@dataclass(frozen=True)
class ProviderStatus:
    """Public, non-secret provider capability summary."""

    name: str
    configured: bool
    text: bool
    image_input: bool
    image_generation: bool
    structured_output: bool


@dataclass(frozen=True)
class ConfigurationCheck:
    """Stable configuration result without credential values."""

    valid: bool
    errors: tuple[str, ...]


def provider_statuses(
    environment: Mapping[str, str] | None = None,
) -> tuple[ProviderStatus, ...]:
    """Return supported providers and whether their required secret exists."""

    env = os.environ if environment is None else environment
    return (
        ProviderStatus(
            name="openai",
            configured=bool(env.get("OPENAI_API_KEY", "").strip()),
            text=True,
            image_input=True,
            image_generation=True,
            structured_output=True,
        ),
    )


def check_configuration(
    environment: Mapping[str, str] | None = None,
) -> ConfigurationCheck:
    """Validate the OpenAI-compatible design provider without a network call."""

    env = os.environ if environment is None else environment
    errors: list[str] = []
    if not env.get("OPENAI_API_KEY", "").strip():
        errors.append("missing:OPENAI_API_KEY")
    base_url = env.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        errors.append("invalid:OPENAI_BASE_URL")
    for variable in ("LALO_OPENAI_VISION_MODEL", "LALO_OPENAI_IMAGE_MODEL"):
        if variable in env and not env[variable].strip():
            errors.append(f"invalid:{variable}")
    retention = env.get("LALO_OPENAI_ZERO_RETENTION")
    if retention is not None and retention not in {"0", "1"}:
        errors.append("invalid:LALO_OPENAI_ZERO_RETENTION")
    return ConfigurationCheck(not errors, tuple(errors))
