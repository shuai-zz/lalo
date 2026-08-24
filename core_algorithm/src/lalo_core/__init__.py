"""Isolated experimental kernel for Lalo's deterministic geometry algorithms."""

from lalo_core.appearance import CharacterPlan, PartAppearance, SurfaceFace, SurfaceMap
from lalo_core.body import CANONICAL_PARTS, PartSpec, mesh_part
from lalo_core.generate import write_canonical_manifest, write_canonical_stls
from lalo_core.meshing import Mesh, mesh_occupancy
from lalo_core.printability import clean_relief_for_fdm
from lalo_core.protection import canonical_protection_masks, clip_protected_relief
from lalo_core.relief import compile_part_relief
from lalo_core.validation import validate_mesh

__all__ = [
    "CANONICAL_PARTS",
    "CharacterPlan",
    "Mesh",
    "PartAppearance",
    "PartSpec",
    "SurfaceFace",
    "SurfaceMap",
    "canonical_protection_masks",
    "clean_relief_for_fdm",
    "clip_protected_relief",
    "compile_part_relief",
    "mesh_occupancy",
    "mesh_part",
    "validate_mesh",
    "write_canonical_manifest",
    "write_canonical_stls",
]
