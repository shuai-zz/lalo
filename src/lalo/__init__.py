"""Lalo geometry tools."""

from lalo.body import CANONICAL_PARTS, PartSpec, mesh_part
from lalo.generate import write_canonical_manifest, write_canonical_stls
from lalo.meshing import Mesh, mesh_occupancy
from lalo.stl import binary_stl_bytes, write_binary_stl
from lalo.voxel import OccupancyGrid, solid_cuboid

__all__ = [
    "CANONICAL_PARTS",
    "Mesh",
    "OccupancyGrid",
    "PartSpec",
    "binary_stl_bytes",
    "mesh_occupancy",
    "mesh_part",
    "solid_cuboid",
    "write_canonical_manifest",
    "write_canonical_stls",
    "write_binary_stl",
]
