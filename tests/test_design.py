from __future__ import annotations

import unittest

from lalo import (
    CharacterDesigner,
    CharacterRegion,
    CharacterSheet,
    DesignerCapabilities,
    DesignRaster,
    DesignRequest,
    DesignResult,
    DesignSubjectError,
    DesignView,
    DesignViewName,
    FeatureImportance,
    IdentityFeature,
    IdentitySpec,
    ImageInput,
    InvalidDesignerOutput,
    PaletteEntry,
    UnsupportedDesignerError,
    design_character,
)


class DesignContractTests(unittest.TestCase):
    def test_accepts_complete_four_view_design(self) -> None:
        result = _result(subject_count=1)

        self.assertEqual(result.identity.features[0].name, "white eyes")
        self.assertEqual(
            tuple(view.name for view in result.sheet.views), tuple(DesignViewName)
        )

    def test_rejects_missing_reordered_or_inconsistent_views(self) -> None:
        views = _views()
        with self.assertRaisesRegex(ValueError, "exactly front, back, left, right"):
            CharacterSheet(views[:-1])
        with self.assertRaisesRegex(ValueError, "exactly front, back, left, right"):
            CharacterSheet((views[1], views[0], views[2], views[3]))
        changed = DesignView(
            DesignViewName.RIGHT,
            DesignRaster(b"right", "image/png", 32, 64),
        )
        with self.assertRaisesRegex(ValueError, "identical dimensions"):
            CharacterSheet((*views[:-1], changed))

    def test_rejects_invalid_identity_specs_and_features(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one feature"):
            IdentitySpec("1.0", "hero", "red suit", _palette(), ())
        secondary = IdentityFeature(
            "blue legs",
            CharacterRegion.LEGS,
            "dark blue leg panels",
            FeatureImportance.SECONDARY,
        )
        with self.assertRaisesRegex(ValueError, "primary feature"):
            IdentitySpec("1.0", "hero", "red suit", _palette(), (secondary,))
        duplicate = _feature()
        with self.assertRaisesRegex(ValueError, "duplicate feature"):
            IdentitySpec("1.0", "hero", "red suit", _palette(), (duplicate, duplicate))

    def test_validates_request_raster_and_capability_primitives(self) -> None:
        with self.assertRaisesRegex(ValueError, "prompt"):
            DesignRequest(" ")
        with self.assertRaisesRegex(ValueError, "non-empty"):
            DesignRaster(b"", "image/png", 64, 64)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            DesignRaster(b"png", "image/png", 0, 64)
        with self.assertRaisesRegex(TypeError, "boolean"):
            DesignerCapabilities(True, True, True, 1)  # type: ignore[arg-type]

    def test_protocol_supports_structural_designer(self) -> None:
        self.assertIsInstance(_FakeDesigner(), CharacterDesigner)


class DesignOrchestrationTests(unittest.TestCase):
    def test_text_request_returns_validated_design(self) -> None:
        designer = _FakeDesigner()

        result = design_character(DesignRequest("red masked hero"), designer)

        self.assertEqual(result.identity.name, "hero")
        self.assertEqual(designer.corrections, [None])

    def test_invalid_output_gets_one_correction_retry(self) -> None:
        designer = _FakeDesigner(fail_once=True)

        design_character(DesignRequest("red masked hero"), designer)

        self.assertEqual(designer.corrections, [None, "views inconsistent"])

    def test_image_requires_privacy_and_exactly_one_subject(self) -> None:
        request = DesignRequest(
            "make this person a block character",
            image=ImageInput(b"photo", "image/jpeg"),
        )
        with self.assertRaisesRegex(UnsupportedDesignerError, "zero-retention"):
            design_character(request, _FakeDesigner(zero_retention=False))
        with self.assertRaisesRegex(DesignSubjectError, "detected=2"):
            design_character(request, _FakeDesigner(subject_count=2))

    def test_structured_identity_output_is_mandatory(self) -> None:
        with self.assertRaisesRegex(UnsupportedDesignerError, "structured"):
            design_character(
                DesignRequest("hero"), _FakeDesigner(structured_output=False)
            )


class _FakeDesigner:
    def __init__(
        self,
        *,
        fail_once: bool = False,
        zero_retention: bool = True,
        structured_output: bool = True,
        subject_count: int | None = 1,
    ) -> None:
        self.fail_once = fail_once
        self.subject_count = subject_count
        self.corrections: list[str | None] = []
        self._capabilities = DesignerCapabilities(
            supports_images=True,
            supports_structured_output=structured_output,
            supports_seed=True,
            supports_zero_retention=zero_retention,
        )

    @property
    def capabilities(self) -> DesignerCapabilities:
        return self._capabilities

    def design(
        self, request: DesignRequest, *, correction: str | None = None
    ) -> DesignResult:
        self.corrections.append(correction)
        if self.fail_once and correction is None:
            raise InvalidDesignerOutput("views inconsistent")
        return _result(subject_count=self.subject_count)


def _palette() -> tuple[PaletteEntry, ...]:
    return (
        PaletteEntry(0, "red", "#C51D34"),
        PaletteEntry(1, "white", "#F3F4F6"),
    )


def _feature() -> IdentityFeature:
    return IdentityFeature(
        "white eyes",
        CharacterRegion.HEAD,
        "large tapered white eye shapes with dark borders",
        FeatureImportance.PRIMARY,
    )


def _views() -> tuple[DesignView, ...]:
    return tuple(
        DesignView(name, DesignRaster(name.value.encode(), "image/png", 64, 64))
        for name in DesignViewName
    )


def _result(*, subject_count: int | None) -> DesignResult:
    return DesignResult(
        identity=IdentitySpec(
            "1.0", "hero", "red masked block hero", _palette(), (_feature(),)
        ),
        sheet=CharacterSheet(_views()),
        effective_seed=7,
        provider="test",
        model="fake-designer",
        model_version="1",
        subject_count=subject_count,
    )


if __name__ == "__main__":
    unittest.main()
