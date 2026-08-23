"""Provider-neutral contracts for the 2D character design stage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from lalo.appearance import PaletteEntry
from lalo.planner import SUPPORTED_IMAGE_MEDIA_TYPES, ImageInput


class CharacterRegion(str, Enum):
    """Coarse visual regions understood before UV or geometry compilation."""

    HEAD = "head"
    TORSO = "torso"
    ARMS = "arms"
    LEGS = "legs"
    ACCESSORY = "accessory"


class FeatureImportance(str, Enum):
    """How strongly a feature contributes to recognizable identity."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class DesignViewName(str, Enum):
    """Required orthographic views in canonical sheet order."""

    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class IdentityFeature:
    """One semantic feature that should survive later stylization."""

    name: str
    region: CharacterRegion
    description: str
    importance: FeatureImportance

    def __post_init__(self) -> None:
        for field_name in ("name", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"identity feature {field_name} must not be empty")
        if not isinstance(self.region, CharacterRegion):
            raise TypeError("identity feature region must be a CharacterRegion")
        if not isinstance(self.importance, FeatureImportance):
            raise TypeError("identity feature importance must be a FeatureImportance")


@dataclass(frozen=True)
class IdentitySpec:
    """A compact, editable visual brief shared by every generated view."""

    schema_version: str
    name: str
    summary: str
    palette: tuple[PaletteEntry, ...]
    features: tuple[IdentityFeature, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported identity spec schema_version")
        for field_name in ("name", "summary"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"identity spec {field_name} must not be empty")
        if not 1 <= len(self.palette) <= 4:
            raise ValueError(
                "identity palette must contain between one and four colors"
            )
        if tuple(entry.id for entry in self.palette) != tuple(range(len(self.palette))):
            raise ValueError("identity palette ids must be contiguous from zero")
        if not self.features:
            raise ValueError("identity spec must contain at least one feature")
        names = tuple(feature.name for feature in self.features)
        if len(set(names)) != len(names):
            raise ValueError("identity spec contains duplicate feature names")
        if not any(
            feature.importance == FeatureImportance.PRIMARY for feature in self.features
        ):
            raise ValueError("identity spec must contain a primary feature")


@dataclass(frozen=True)
class DesignRaster:
    """One in-memory raster artifact with explicit dimensions."""

    data: bytes
    media_type: str
    width: int
    height: int

    def __post_init__(self) -> None:
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("design raster data must be non-empty bytes")
        if self.media_type not in SUPPORTED_IMAGE_MEDIA_TYPES:
            raise ValueError("design raster media_type must be JPEG, PNG, or WebP")
        for field_name in ("width", "height"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"design raster {field_name} must be a positive integer"
                )


@dataclass(frozen=True)
class DesignView:
    """One named orthographic character view."""

    name: DesignViewName
    image: DesignRaster

    def __post_init__(self) -> None:
        if not isinstance(self.name, DesignViewName):
            raise TypeError("design view name must be a DesignViewName")
        if not isinstance(self.image, DesignRaster):
            raise TypeError("design view image must be a DesignRaster")


@dataclass(frozen=True)
class CharacterSheet:
    """Exactly four consistent orthographic views of one character."""

    views: tuple[DesignView, ...]

    def __post_init__(self) -> None:
        names = tuple(view.name for view in self.views)
        required = tuple(DesignViewName)
        if names != required:
            raise ValueError(
                "character sheet views must be exactly front, back, left, right"
            )
        dimensions = {(view.image.width, view.image.height) for view in self.views}
        if len(dimensions) != 1:
            raise ValueError("character sheet views must have identical dimensions")


@dataclass(frozen=True)
class DesignRequest:
    """Text-first input for producing one character design package."""

    prompt: str
    image: ImageInput | None = None
    seed: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("design prompt must not be empty")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("design seed must be an integer")


@dataclass(frozen=True)
class DesignerCapabilities:
    """Features and privacy guarantees declared by a design provider."""

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
class DesignResult:
    """A validated 2D design plus reproducibility identifiers."""

    identity: IdentitySpec
    sheet: CharacterSheet
    effective_seed: int
    provider: str
    model: str
    model_version: str
    subject_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, IdentitySpec):
            raise TypeError("design result identity must be an IdentitySpec")
        if not isinstance(self.sheet, CharacterSheet):
            raise TypeError("design result sheet must be a CharacterSheet")
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


class InvalidDesignerOutput(ValueError):
    """A provider response failed safe local schema or semantic validation."""

    def __init__(self, feedback: str) -> None:
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("invalid-output feedback must not be empty")
        self.feedback = feedback
        super().__init__(feedback)


@runtime_checkable
class CharacterDesigner(Protocol):
    """Replaceable synchronous provider for 2D character design."""

    @property
    def capabilities(self) -> DesignerCapabilities:
        """Return provider features used by orchestration policy."""

    def design(
        self, request: DesignRequest, *, correction: str | None = None
    ) -> DesignResult:
        """Produce a validated identity specification and four-view sheet."""
