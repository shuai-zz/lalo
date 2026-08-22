"""Application policy for bounded, provider-neutral character planning."""

from __future__ import annotations

from lalo.planner import (
    CharacterPlanner,
    InvalidPlannerOutput,
    PlanRequest,
    PlanResult,
)


class UnsupportedPlannerError(ValueError):
    """A planner cannot satisfy mandatory request or privacy requirements."""


class SingleSubjectError(ValueError):
    """An image request did not resolve to exactly one person or character."""

    def __init__(self, subject_count: int | None) -> None:
        self.subject_count = subject_count
        super().__init__(
            "image must contain exactly one person or character "
            f"(detected={subject_count})"
        )


def plan_character(request: PlanRequest, planner: CharacterPlanner) -> PlanResult:
    """Plan one character, allowing one correction for invalid provider output."""

    capabilities = planner.capabilities
    if request.image is not None:
        if not capabilities.supports_images:
            raise UnsupportedPlannerError("planner does not support image input")
        if not capabilities.supports_zero_retention:
            raise UnsupportedPlannerError(
                "image planning requires declared zero-retention support"
            )

    try:
        result = planner.plan(request)
    except InvalidPlannerOutput as first_error:
        result = planner.plan(request, correction=first_error.feedback)

    if request.image is not None and result.subject_count != 1:
        raise SingleSubjectError(result.subject_count)
    return result
