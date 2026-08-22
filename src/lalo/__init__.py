"""Lalo geometry tools."""

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SilhouetteFeature,
    SurfaceFace,
    SurfaceMap,
)
from lalo.body import CANONICAL_PARTS, PartSpec, mesh_part
from lalo.generate import write_canonical_manifest, write_canonical_stls
from lalo.fixtures import iron_man_plan, spider_man_plan
from lalo.glb import write_canonical_glb
from lalo.m0 import M0Artifacts, generate_m0_artifacts
from lalo.m1 import M1Artifacts, generate_m1_artifacts
from lalo.meshing import Mesh, mesh_occupancy
from lalo.planner import (
    CharacterPlanner,
    ImageInput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
    SUPPORTED_IMAGE_MEDIA_TYPES,
)
from lalo.protection import (
    ProtectionMask,
    ProtectionResult,
    canonical_protection_masks,
    clip_protected_relief,
)
from lalo.printability import PrintabilityResult, clean_relief_for_fdm
from lalo.relief import (
    DETAIL_CELLS_PER_MASTER,
    DetailedPart,
    compile_part_relief,
    mesh_detailed_part,
)
from lalo.stl import binary_stl_bytes, write_binary_stl
from lalo.validation import MeshValidation, ValidationIssue, validate_mesh
from lalo.voxel import OccupancyGrid, solid_cuboid

__all__ = [
    "CANONICAL_PARTS",
    "CharacterPlan",
    "CharacterPlanner",
    "DETAIL_CELLS_PER_MASTER",
    "DetailedPart",
    "Mesh",
    "MeshValidation",
    "M0Artifacts",
    "M1Artifacts",
    "ImageInput",
    "OccupancyGrid",
    "PaletteEntry",
    "PlanRequest",
    "PlanResult",
    "PlannerCapabilities",
    "PartSpec",
    "PartAppearance",
    "ProtectionMask",
    "ProtectionResult",
    "PrintabilityResult",
    "SurfaceFace",
    "SurfaceMap",
    "SUPPORTED_IMAGE_MEDIA_TYPES",
    "SilhouetteFeature",
    "ValidationIssue",
    "binary_stl_bytes",
    "compile_part_relief",
    "canonical_protection_masks",
    "clip_protected_relief",
    "clean_relief_for_fdm",
    "generate_m0_artifacts",
    "generate_m1_artifacts",
    "iron_man_plan",
    "mesh_occupancy",
    "mesh_part",
    "mesh_detailed_part",
    "solid_cuboid",
    "spider_man_plan",
    "validate_mesh",
    "write_canonical_manifest",
    "write_canonical_stls",
    "write_binary_stl",
    "write_canonical_glb",
]
