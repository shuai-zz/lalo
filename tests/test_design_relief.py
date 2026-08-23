from __future__ import annotations

import unittest
from dataclasses import replace

from test_design_materials import _identity, _sheet

from lalo import (
    CharacterRegion,
    FeatureImportance,
    IdentityFeature,
    SurfaceMap,
    crop_design_parts,
    infer_design_relief,
    sample_design_materials,
)


class DesignReliefTests(unittest.TestCase):
    def test_material_boundaries_become_one_cell_engravings(self) -> None:
        identity = _identity()
        plan = sample_design_materials(identity, crop_design_parts(_sheet()))
        torso = plan.parts[1]
        front = torso.surfaces[0]
        materials = [list(row) for row in front.materials]
        materials[len(materials) // 2][len(materials[0]) // 2] = 1
        changed = SurfaceMap(
            front.face,
            front.relief,
            tuple(tuple(value for value in row) for row in materials),
        )
        plan = replace(
            plan,
            parts=(
                plan.parts[0],
                replace(torso, surfaces=(changed, *torso.surfaces[1:])),
                *plan.parts[2:],
            ),
        )

        result = infer_design_relief(identity, plan)

        self.assertTrue(
            any(
                level == -1
                for part in result.parts
                for surface in part.surfaces
                for row in surface.relief
                for level in row
            )
        )

    def test_identified_glasses_raise_dark_front_head_details(self) -> None:
        identity = replace(
            _identity(),
            features=(
                IdentityFeature(
                    "round glasses",
                    CharacterRegion.HEAD,
                    "dark eyeglasses",
                    FeatureImportance.PRIMARY,
                ),
            ),
        )
        plan = sample_design_materials(identity, crop_design_parts(_sheet()))
        head = plan.parts[0]
        front = head.surfaces[0]
        materials = [list(row) for row in front.materials]
        materials[len(materials) // 2][len(materials[0]) // 2] = 1
        changed_front = SurfaceMap(
            front.face,
            front.relief,
            tuple(tuple(value for value in row) for row in materials),
        )
        plan = replace(
            plan,
            parts=(
                replace(head, surfaces=(changed_front, *head.surfaces[1:])),
                *plan.parts[1:],
            ),
        )

        result = infer_design_relief(identity, plan)
        output_front = result.parts[0].surfaces[0]

        self.assertEqual(
            output_front.relief[len(materials) // 2][len(materials[0]) // 2], 1
        )


if __name__ == "__main__":
    unittest.main()
