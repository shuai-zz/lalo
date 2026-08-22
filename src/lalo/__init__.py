"""Lalo geometry tools."""

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SurfaceFace,
    SurfaceMap,
)
from lalo.body import CANONICAL_PARTS, PartSpec, mesh_part
from lalo.generate import write_canonical_manifest, write_canonical_stls
from lalo.glb import write_canonical_glb
from lalo.m0 import M0Artifacts, generate_m0_artifacts
from lalo.meshing import Mesh, mesh_occupancy
from lalo.stl import binary_stl_bytes, write_binary_stl
from lalo.validation import MeshValidation, ValidationIssue, validate_mesh
from lalo.voxel import OccupancyGrid, solid_cuboid

__all__ = [
    "CANONICAL_PARTS",
    "CharacterPlan",
    "Mesh",
    "MeshValidation",
    "M0Artifacts",
    "OccupancyGrid",
    "PaletteEntry",
    "PartSpec",
    "PartAppearance",
    "SurfaceFace",
    "SurfaceMap",
    "ValidationIssue",
    "binary_stl_bytes",
    "generate_m0_artifacts",
    "mesh_occupancy",
    "mesh_part",
    "solid_cuboid",
    "validate_mesh",
    "write_canonical_manifest",
    "write_canonical_stls",
    "write_binary_stl",
    "write_canonical_glb",
]
