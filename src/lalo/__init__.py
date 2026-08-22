"""Lalo geometry tools."""

from lalo.body import CANONICAL_PARTS, PartSpec
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
    "solid_cuboid",
    "write_binary_stl",
]
