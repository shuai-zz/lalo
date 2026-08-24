"""Topology validation for generated meshes."""

from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass

from lalo_core.meshing import Face, Mesh


@dataclass(frozen=True)
class ValidationIssue:
    """One machine-readable mesh validation failure."""

    code: str
    message: str


@dataclass(frozen=True)
class MeshValidation:
    """Structured result of validating one mesh."""

    valid: bool
    issues: tuple[ValidationIssue, ...]
    vertex_count: int
    triangle_count: int
    edge_count: int
    component_count: int | None
    signed_volume: float | None


def validate_mesh(mesh: Mesh) -> MeshValidation:
    """Validate topology required of an M0 printable solid."""

    issues: list[ValidationIssue] = []
    if not mesh.vertices:
        issues.append(ValidationIssue("empty_vertices", "mesh has no vertices"))
    if not mesh.faces:
        issues.append(ValidationIssue("empty_faces", "mesh has no triangles"))

    coordinates_valid = True
    for index, vertex in enumerate(mesh.vertices):
        if len(vertex) != 3 or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in vertex
        ):
            coordinates_valid = False
            issues.append(
                ValidationIssue(
                    "invalid_vertex", f"vertex {index} must contain three finite numbers"
                )
            )

    valid_faces: list[Face] = []
    seen_faces: set[tuple[int, int, int]] = set()
    for face_index, face in enumerate(mesh.faces):
        if len(face) != 3 or any(
            isinstance(index, bool) or not isinstance(index, int) for index in face
        ):
            issues.append(
                ValidationIssue(
                    "invalid_face", f"face {face_index} must contain three integer indices"
                )
            )
            continue
        if any(index < 0 or index >= len(mesh.vertices) for index in face):
            issues.append(
                ValidationIssue(
                    "invalid_index", f"face {face_index} references a missing vertex"
                )
            )
            continue

        valid_faces.append(face)
        canonical = tuple(sorted(face))
        if canonical in seen_faces:
            issues.append(
                ValidationIssue(
                    "duplicate_triangle", f"face {face_index} duplicates another triangle"
                )
            )
        seen_faces.add(canonical)

        if len(set(face)) < 3 or (
            coordinates_valid and _triangle_area_twice(mesh, face) == 0
        ):
            issues.append(
                ValidationIssue("degenerate_triangle", f"face {face_index} is degenerate")
            )

    edge_counts: Counter[tuple[int, int]] = Counter()
    for a, b, c in valid_faces:
        edge_counts.update(
            (
                tuple(sorted((a, b))),
                tuple(sorted((b, c))),
                tuple(sorted((c, a))),
            )
        )
    bad_edge_count = sum(count != 2 for count in edge_counts.values())
    if bad_edge_count:
        issues.append(
            ValidationIssue(
                "non_manifold_edges",
                f"mesh has {bad_edge_count} edges without exactly two incident triangles",
            )
        )

    component_count = _component_count(valid_faces) if valid_faces else None
    if component_count is not None and component_count != 1:
        issues.append(
            ValidationIssue(
                "disconnected_mesh",
                f"mesh has {component_count} disconnected triangle components",
            )
        )

    signed_volume = (
        _signed_volume(mesh, valid_faces)
        if valid_faces
        and coordinates_valid
        and len(valid_faces) == len(mesh.faces)
        else None
    )
    if signed_volume is not None and signed_volume <= 0:
        issues.append(
            ValidationIssue(
                "non_positive_volume",
                f"mesh signed volume must be positive, got {signed_volume}",
            )
        )

    return MeshValidation(
        valid=not issues,
        issues=tuple(issues),
        vertex_count=len(mesh.vertices),
        triangle_count=len(mesh.faces),
        edge_count=len(edge_counts),
        component_count=component_count,
        signed_volume=signed_volume,
    )


def _triangle_area_twice(mesh: Mesh, face: Face) -> float:
    a, b, c = (mesh.vertices[index] for index in face)
    ab = tuple(b[axis] - a[axis] for axis in range(3))
    ac = tuple(c[axis] - a[axis] for axis in range(3))
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return math.sqrt(sum(value * value for value in cross))


def _component_count(faces: list[Face]) -> int:
    faces_by_vertex: dict[int, list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for vertex_index in face:
            faces_by_vertex[vertex_index].append(face_index)

    unseen = set(range(len(faces)))
    components = 0
    while unseen:
        components += 1
        queue = deque((unseen.pop(),))
        while queue:
            face_index = queue.popleft()
            for vertex_index in faces[face_index]:
                for neighbor in faces_by_vertex[vertex_index]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
    return components


def _signed_volume(mesh: Mesh, faces: list[Face]) -> float:
    volume_times_six = 0.0
    for a_index, b_index, c_index in faces:
        ax, ay, az = mesh.vertices[a_index]
        bx, by, bz = mesh.vertices[b_index]
        cx, cy, cz = mesh.vertices[c_index]
        volume_times_six += (
            ax * (by * cz - bz * cy)
            + ay * (bz * cx - bx * cz)
            + az * (bx * cy - by * cx)
        )
    return volume_times_six / 6.0
