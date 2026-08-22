"""Provider-neutral contracts for M2 character planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from lalo.appearance import CharacterPlan

SUPPORTED_IMAGE_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)


@dataclass(frozen=True)
class ImageInput:
    """An in-memory reference image supplied to a character planner."""

    data: bytes
    media_type: str

    def __post_init__(self) -> None:
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("image data must be non-empty bytes")
        if self.media_type not in SUPPORTED_IMAGE_MEDIA_TYPES:
            raise ValueError("image media_type must be JPEG, PNG, or WebP")


@dataclass(frozen=True)
class PlanRequest:
    """Text-first input for producing one constrained character plan."""

    prompt: str
    image: ImageInput | None = None
    seed: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("planner prompt must not be empty")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("planner seed must be an integer")


@dataclass(frozen=True)
class PlannerCapabilities:
    """Features and data-handling guarantees declared by a planner."""

    supports_images: bool
    supports_structured_output: bool
    supports_seed: bool
    supports_zero_retention: bool

    def __post_init__(self) -> None:
        for field_name in (
            "supports_images",
            "supports_structured_output",
            "supports_seed",
            "supports_zero_retention",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean")


@dataclass(frozen=True)
class PlanResult:
    """A validated plan together with identifiers needed to reproduce it."""

    plan: CharacterPlan
    effective_seed: int
    provider: str
    model: str
    model_version: str
    subject_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.plan, CharacterPlan):
            raise TypeError("planner result plan must be a CharacterPlan")
        if isinstance(self.effective_seed, bool) or not isinstance(
            self.effective_seed, int
        ):
            raise TypeError("effective_seed must be an integer")
        for field_name in ("provider", "model", "model_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.subject_count is not None and (
            isinstance(self.subject_count, bool)
            or not isinstance(self.subject_count, int)
            or self.subject_count < 0
        ):
            raise ValueError("subject_count must be a non-negative integer or None")


class InvalidPlannerOutput(ValueError):
    """A provider response failed safe local schema or semantic validation."""

    def __init__(self, feedback: str) -> None:
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("invalid-output feedback must not be empty")
        self.feedback = feedback
        super().__init__(feedback)


@runtime_checkable
class CharacterPlanner(Protocol):
    """Replaceable synchronous provider for constrained character planning."""

    @property
    def capabilities(self) -> PlannerCapabilities:
        """Return the provider features used by orchestration policy."""

    def plan(
        self, request: PlanRequest, *, correction: str | None = None
    ) -> PlanResult:
        """Produce a validated character plan for one request."""
