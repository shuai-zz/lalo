from __future__ import annotations

import unittest

from lalo.body import CANONICAL_PARTS, PartSpec


class CanonicalBodyTests(unittest.TestCase):
    def test_defines_the_expected_fourteen_parts(self) -> None:
        self.assertEqual(
            tuple(part.name for part in CANONICAL_PARTS),
            (
                "head",
                "torso",
                "left_upper_arm",
                "right_upper_arm",
                "left_forearm",
                "right_forearm",
                "left_hand",
                "right_hand",
                "left_thigh",
                "right_thigh",
                "left_shin",
                "right_shin",
                "left_foot",
                "right_foot",
            ),
        )

    def test_uses_canonical_head_torso_and_limb_envelopes(self) -> None:
        parts = _by_name()

        self.assertEqual(parts["head"].size_xyz, (8, 8, 8))
        self.assertEqual(parts["torso"].size_xyz, (8, 4, 12))
        self.assertEqual(
            sum(parts[name].size_xyz[2] for name in _left_arm_names()), 12
        )
        self.assertEqual(
            sum(parts[name].size_xyz[2] for name in _left_leg_names()), 12
        )

    def test_paired_parts_have_equal_sizes_and_mirrored_x_bounds(self) -> None:
        parts = _by_name()
        for left_name in (
            "left_upper_arm",
            "left_forearm",
            "left_hand",
            "left_thigh",
            "left_shin",
            "left_foot",
        ):
            right_name = left_name.replace("left_", "right_")
            left = parts[left_name]
            right = parts[right_name]
            self.assertEqual(left.size_xyz, right.size_xyz)
            self.assertEqual(left.origin_xyz[0], -_max_x(right))
            self.assertEqual(_max_x(left), -right.origin_xyz[0])
            self.assertEqual(left.origin_xyz[1:], right.origin_xyz[1:])

    def test_assembled_height_runs_from_zero_to_thirty_two(self) -> None:
        minimum_z = min(part.origin_xyz[2] for part in CANONICAL_PARTS)
        maximum_z = max(
            part.origin_xyz[2] + part.size_xyz[2] for part in CANONICAL_PARTS
        )

        self.assertEqual(minimum_z, 0)
        self.assertEqual(maximum_z, 32)

    def test_default_segment_split_is_five_five_two(self) -> None:
        parts = _by_name()

        self.assertEqual(
            tuple(parts[name].size_xyz[2] for name in _left_arm_names()), (5, 5, 2)
        )
        self.assertEqual(
            tuple(parts[name].size_xyz[2] for name in _left_leg_names()), (5, 5, 2)
        )

    def test_part_specs_are_immutable(self) -> None:
        with self.assertRaises(AttributeError):
            CANONICAL_PARTS[0].name = "changed"  # type: ignore[misc]


def _by_name() -> dict[str, PartSpec]:
    return {part.name: part for part in CANONICAL_PARTS}


def _left_arm_names() -> tuple[str, ...]:
    return "left_upper_arm", "left_forearm", "left_hand"


def _left_leg_names() -> tuple[str, ...]:
    return "left_thigh", "left_shin", "left_foot"


def _max_x(part: PartSpec) -> int:
    return part.origin_xyz[0] + part.size_xyz[0]


if __name__ == "__main__":
    unittest.main()
