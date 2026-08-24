from __future__ import annotations

import unittest

from lalo_core.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SilhouetteFeature,
    SurfaceFace,
    SurfaceMap,
)


class AppearancePlanTests(unittest.TestCase):
    def test_accepts_immutable_four_color_multi_part_plan(self) -> None:
        plan = CharacterPlan(
            schema_version="1.0",
            name="hero",
            palette=_palette(4),
            parts=(
                PartAppearance("head", (_surface(SurfaceFace.FRONT, 3),)),
                PartAppearance("torso", (_surface(SurfaceFace.BACK, 2),)),
            ),
        )

        self.assertEqual(plan.parts[0].surfaces[0].relief[0], (0, 1))
        with self.assertRaises(TypeError):
            plan.parts[0].surfaces[0].relief[0][0] = 1  # type: ignore[index]

    def test_rejects_invalid_palette(self) -> None:
        with self.assertRaisesRegex(ValueError, "#RRGGBB"):
            PaletteEntry(0, "red", "red")
        with self.assertRaisesRegex(ValueError, "between one and four"):
            CharacterPlan("1.0", "hero", _palette(5), ())
        with self.assertRaisesRegex(ValueError, "contiguous"):
            CharacterPlan(
                "1.0",
                "hero",
                (PaletteEntry(1, "red", "#FF0000"),),
                (),
            )

    def test_rejects_ragged_mismatched_and_out_of_range_maps(self) -> None:
        with self.assertRaisesRegex(ValueError, "rectangular"):
            SurfaceMap(SurfaceFace.FRONT, ((0,), (0, 1)), ((0,), (0, 1)))
        with self.assertRaisesRegex(ValueError, "identical dimensions"):
            SurfaceMap(SurfaceFace.FRONT, ((0, 1),), ((0,),))
        with self.assertRaisesRegex(ValueError, "between -2 and 2"):
            SurfaceMap(SurfaceFace.FRONT, ((3,),), ((0,),))
        with self.assertRaisesRegex(ValueError, "between 0 and 3"):
            SurfaceMap(SurfaceFace.FRONT, ((0,),), ((4,),))

    def test_rejects_unknown_or_duplicate_parts_and_faces(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown canonical part"):
            PartAppearance("cape", ())
        with self.assertRaisesRegex(ValueError, "duplicate surface"):
            PartAppearance(
                "head",
                (_surface(SurfaceFace.FRONT), _surface(SurfaceFace.FRONT)),
            )
        head = PartAppearance("head", ())
        with self.assertRaisesRegex(ValueError, "duplicate parts"):
            CharacterPlan("1.0", "hero", _palette(1), (head, head))

    def test_rejects_unknown_material_reference_and_schema(self) -> None:
        part = PartAppearance("head", (_surface(SurfaceFace.FRONT, material=1),))
        with self.assertRaisesRegex(ValueError, "missing palette"):
            CharacterPlan("1.0", "hero", _palette(1), (part,))
        with self.assertRaisesRegex(ValueError, "schema_version"):
            CharacterPlan("2.0", "hero", _palette(1), ())

    def test_validates_silhouette_features_and_palette_references(self) -> None:
        feature = SilhouetteFeature((-2, 1, 1), (2, 2, 2), 1)
        part = PartAppearance("head", (), (feature,))
        plan = CharacterPlan("1.0", "ears", _palette(2), (part,))
        self.assertEqual(plan.parts[0].silhouette_features, (feature,))

        with self.assertRaisesRegex(ValueError, "greater than zero"):
            SilhouetteFeature((0, 0, 0), (0, 1, 1), 0)
        with self.assertRaisesRegex(ValueError, "10 detail cells"):
            SilhouetteFeature((0, 0, 0), (11, 1, 1), 0)
        with self.assertRaisesRegex(ValueError, "missing palette"):
            CharacterPlan("1.0", "ears", _palette(1), (part,))


def _palette(count: int) -> tuple[PaletteEntry, ...]:
    return tuple(
        PaletteEntry(index, f"color-{index}", f"#{index:02X}{index:02X}{index:02X}")
        for index in range(count)
    )


def _surface(
    face: SurfaceFace, material: int = 0
) -> SurfaceMap:
    return SurfaceMap(
        face=face,
        relief=((0, 1), (0, 0)),
        materials=((material, material), (material, material)),
    )


if __name__ == "__main__":
    unittest.main()
