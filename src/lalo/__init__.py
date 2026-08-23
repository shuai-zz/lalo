"""Lalo geometry tools."""

from lalo.appearance import (
    CharacterPlan,
    PaletteEntry,
    PartAppearance,
    SilhouetteFeature,
    SurfaceFace,
    SurfaceMap,
)
from lalo.body import (
    CANONICAL_PARTS,
    DEFAULT_LEG_GAP_MM,
    PartSpec,
    assembly_translation_mm,
    mesh_part,
)
from lalo.generate import write_canonical_manifest, write_canonical_stls
from lalo.fixtures import iron_man_plan, spider_man_plan
from lalo.glb import write_canonical_glb
from lalo.m0 import M0Artifacts, generate_m0_artifacts
from lalo.m1 import M1Artifacts, generate_m1_artifacts
from lalo.m2 import GENERATOR_VERSION, M2Artifacts, generate_m2_artifacts
from lalo.meshing import Mesh, mesh_occupancy
from lalo.openai_planner import (
    OpenAIHTTPTransport,
    OpenAIPlanner,
    ResponsesTransport,
    openai_planner_schema,
)
from lalo.plan_json import (
    CharacterPlanCodecError,
    character_plan_from_dict,
    character_plan_from_json,
    character_plan_to_dict,
    character_plan_to_json,
)
from lalo.planner import (
    CharacterPlanner,
    ImageInput,
    InvalidPlannerOutput,
    PlanRequest,
    PlannerCapabilities,
    PlanResult,
    SUPPORTED_IMAGE_MEDIA_TYPES,
)
from lalo.planning import SingleSubjectError, UnsupportedPlannerError, plan_character
from lalo.protection import (
    ProtectionMask,
    ProtectionResult,
    canonical_protection_masks,
    clip_protected_relief,
)
from lalo.printability import PrintabilityResult, clean_relief_for_fdm
from lalo.privacy import (
    planning_metadata,
    planning_metadata_json,
    transient_image_file,
)
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
    "CharacterPlanCodecError",
    "CharacterPlanner",
    "DETAIL_CELLS_PER_MASTER",
    "DEFAULT_LEG_GAP_MM",
    "DetailedPart",
    "Mesh",
    "MeshValidation",
    "M0Artifacts",
    "M1Artifacts",
    "M2Artifacts",
    "ImageInput",
    "GENERATOR_VERSION",
    "InvalidPlannerOutput",
    "OccupancyGrid",
    "OpenAIHTTPTransport",
    "OpenAIPlanner",
    "PaletteEntry",
    "PlanRequest",
    "PlanResult",
    "PlannerCapabilities",
    "PartSpec",
    "PartAppearance",
    "ProtectionMask",
    "ProtectionResult",
    "ResponsesTransport",
    "PrintabilityResult",
    "SurfaceFace",
    "SurfaceMap",
    "SUPPORTED_IMAGE_MEDIA_TYPES",
    "SingleSubjectError",
    "UnsupportedPlannerError",
    "SilhouetteFeature",
    "ValidationIssue",
    "binary_stl_bytes",
    "assembly_translation_mm",
    "character_plan_from_dict",
    "character_plan_from_json",
    "character_plan_to_dict",
    "character_plan_to_json",
    "compile_part_relief",
    "canonical_protection_masks",
    "clip_protected_relief",
    "clean_relief_for_fdm",
    "generate_m0_artifacts",
    "generate_m1_artifacts",
    "generate_m2_artifacts",
    "iron_man_plan",
    "mesh_occupancy",
    "mesh_part",
    "openai_planner_schema",
    "plan_character",
    "planning_metadata",
    "planning_metadata_json",
    "mesh_detailed_part",
    "solid_cuboid",
    "spider_man_plan",
    "transient_image_file",
    "validate_mesh",
    "write_canonical_manifest",
    "write_canonical_stls",
    "write_binary_stl",
    "write_canonical_glb",
]
