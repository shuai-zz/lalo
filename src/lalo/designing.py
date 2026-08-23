"""Application policy for bounded, privacy-safe 2D character design."""

from __future__ import annotations

from lalo.design import (
    CharacterDesigner,
    DesignRequest,
    DesignResult,
    InvalidDesignerOutput,
)


class UnsupportedDesignerError(ValueError):
    """A designer cannot satisfy mandatory request or privacy requirements."""


class DesignSubjectError(ValueError):
    """An image request did not resolve to exactly one person or character."""

    def __init__(self, subject_count: int | None) -> None:
        self.subject_count = subject_count
        super().__init__(
            "design image must contain exactly one person or character "
            f"(detected={subject_count})"
        )


def design_character(
    request: DesignRequest, designer: CharacterDesigner
) -> DesignResult:
    """Design one character, allowing one correction for invalid output."""

    capabilities = designer.capabilities
    if not capabilities.supports_structured_output:
        raise UnsupportedDesignerError(
            "designer must support structured identity output"
        )
    if request.image is not None:
        if not capabilities.supports_images:
            raise UnsupportedDesignerError("designer does not support image input")
        if not capabilities.supports_zero_retention:
            raise UnsupportedDesignerError(
                "image design requires declared zero-retention support"
            )

    try:
        result = designer.design(request)
    except InvalidDesignerOutput as first_error:
        result = designer.design(request, correction=first_error.feedback)

    if request.image is not None and result.subject_count != 1:
        raise DesignSubjectError(result.subject_count)
    return result
