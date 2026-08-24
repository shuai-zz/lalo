from __future__ import annotations

import unittest

from lalo_core.appearance import SurfaceFace, SurfaceMap
from lalo_core.body import CANONICAL_PARTS, PartSpec
from lalo_core.protection import (
    ProtectionMask,
    canonical_protection_masks,
    clip_protected_relief,
)
from lalo_core.relief import face_detail_shape


class ProtectionMaskTests(unittest.TestCase):
    def test_canonical_mating_faces_are_fully_protected(self) -> None:
        parts = {part.name: part for part in CANONICAL_PARTS}
        expectations = {
            "head": (SurfaceFace.BOTTOM,),
            "torso": (SurfaceFace.TOP, SurfaceFace.BOTTOM),
            "left_upper_arm": (SurfaceFace.TOP, SurfaceFace.BOTTOM),
            "left_forearm": (SurfaceFace.TOP, SurfaceFace.BOTTOM),
            "left_hand": (SurfaceFace.TOP,),
            "left_thigh": (SurfaceFace.TOP, SurfaceFace.BOTTOM),
            "left_shin": (SurfaceFace.TOP, SurfaceFace.BOTTOM),
            "left_foot": (SurfaceFace.TOP,),
        }
        for part_name, faces in expectations.items():
            with self.subTest(part=part_name):
                masks = _by_face(canonical_protection_masks(parts[part_name]))
                for face in faces:
                    self.assertEqual(
                        _shape(masks[face].protected),
                        face_detail_shape(parts[part_name], face),
                    )
                    self.assertTrue(all(all(row) for row in masks[face].protected))

    def test_torso_shoulders_protect_top_four_master_voxels(self) -> None:
        torso = next(part for part in CANONICAL_PARTS if part.name == "torso")
        masks = _by_face(canonical_protection_masks(torso))

        for face in (SurfaceFace.LEFT, SurfaceFace.RIGHT):
            mask = masks[face].protected
            self.assertTrue(all(all(row) for row in mask[:20]))
            self.assertTrue(all(not any(row) for row in mask[20:]))

    def test_clips_relief_but_preserves_materials_and_unprotected_pixels(self) -> None:
        surface = SurfaceMap(
            SurfaceFace.FRONT,
            relief=((1, -1), (2, 1)),
            materials=((0, 1), (2, 3)),
        )
        mask = ProtectionMask(
            SurfaceFace.FRONT,
            protected=((True, False), (False, True)),
        )

        result = clip_protected_relief((surface,), (mask,))

        self.assertEqual(result.surfaces[0].relief, ((0, -1), (2, 0)))
        self.assertIs(result.surfaces[0].materials, surface.materials)
        self.assertEqual(result.clipped_pixel_count, 2)

    def test_rejects_mismatched_or_duplicate_masks(self) -> None:
        surface = SurfaceMap(SurfaceFace.FRONT, ((1, 0),), ((0, 0),))
        wrong = ProtectionMask(SurfaceFace.FRONT, ((True,),))
        with self.assertRaisesRegex(ValueError, "match surface dimensions"):
            clip_protected_relief((surface,), (wrong,))
        valid = ProtectionMask(SurfaceFace.FRONT, ((True, False),))
        with self.assertRaisesRegex(ValueError, "duplicate protection"):
            clip_protected_relief((surface,), (valid, valid))

    def test_no_matching_mask_returns_original_surface(self) -> None:
        surface = SurfaceMap(SurfaceFace.BACK, ((1,),), ((0,),))
        result = clip_protected_relief((surface,), ())

        self.assertIs(result.surfaces[0], surface)
        self.assertEqual(result.clipped_pixel_count, 0)


def _by_face(masks: tuple[ProtectionMask, ...]) -> dict[SurfaceFace, ProtectionMask]:
    return {mask.face: mask for mask in masks}


def _shape(grid: tuple[tuple[bool, ...], ...]) -> tuple[int, int]:
    return len(grid), len(grid[0])


if __name__ == "__main__":
    unittest.main()
