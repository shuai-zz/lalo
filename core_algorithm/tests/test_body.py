from __future__ import annotations

import unittest
from collections import Counter

from lalo_core.body import CANONICAL_PARTS, PartSpec, assembly_translation_mm, mesh_part
from lalo_core.meshing import Mesh


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

    def test_compiles_head_at_local_origin(self) -> None:
        mesh = mesh_part(_by_name()["head"])

        self.assertEqual(_bounds(mesh), ((0, 0, 0), (8, 8, 8)))
        self.assertAlmostEqual(_signed_volume(mesh), 8 * 8 * 8)
        self.assertEqual(_edge_incidence(mesh), {2})

    def test_compiles_distinct_torso_and_foot_dimensions(self) -> None:
        parts = _by_name()

        self.assertEqual(_bounds(mesh_part(parts["torso"]))[1], (8, 4, 12))
        self.assertEqual(_bounds(mesh_part(parts["left_foot"]))[1], (4, 4, 2))

    def test_assembled_origin_does_not_change_local_mesh(self) -> None:
        first = PartSpec("example", (2, 3, 4), (0, 0, 0))
        moved = PartSpec("example", (2, 3, 4), (100, -20, 8))

        self.assertEqual(mesh_part(first), mesh_part(moved))

    def test_neutral_assembly_separates_legs_symmetrically(self) -> None:
        parts = _by_name()
        right = assembly_translation_mm(parts["right_thigh"], 3.0)
        left = assembly_translation_mm(parts["left_thigh"], 3.0)

        right_max_x = right[0] + parts["right_thigh"].size_xyz[0] * 3.0
        left_min_x = left[0]
        self.assertAlmostEqual(left_min_x - right_max_x, 0.8)
        self.assertAlmostEqual(right[0], -12.4)
        self.assertAlmostEqual(left[0], 0.4)
        self.assertEqual(assembly_translation_mm(parts["head"], 3.0), (-12.0, -12.0, 72.0))


def _by_name() -> dict[str, PartSpec]:
    return {part.name: part for part in CANONICAL_PARTS}


def _left_arm_names() -> tuple[str, ...]:
    return "left_upper_arm", "left_forearm", "left_hand"


def _left_leg_names() -> tuple[str, ...]:
    return "left_thigh", "left_shin", "left_foot"


def _max_x(part: PartSpec) -> int:
    return part.origin_xyz[0] + part.size_xyz[0]


def _bounds(mesh: Mesh) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    return (
        tuple(min(vertex[axis] for vertex in mesh.vertices) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in mesh.vertices) for axis in range(3)),
    )


def _edge_incidence(mesh: Mesh) -> set[int]:
    edges: Counter[tuple[int, int]] = Counter()
    for a, b, c in mesh.faces:
        edges.update(
            (
                tuple(sorted((a, b))),
                tuple(sorted((b, c))),
                tuple(sorted((c, a))),
            )
        )
    return set(edges.values())


def _signed_volume(mesh: Mesh) -> float:
    volume_times_six = 0
    for a_index, b_index, c_index in mesh.faces:
        ax, ay, az = mesh.vertices[a_index]
        bx, by, bz = mesh.vertices[b_index]
        cx, cy, cz = mesh.vertices[c_index]
        volume_times_six += (
            ax * (by * cz - bz * cy)
            + ay * (bz * cx - bx * cz)
            + az * (bx * cy - by * cx)
        )
    return volume_times_six / 6


if __name__ == "__main__":
    unittest.main()
