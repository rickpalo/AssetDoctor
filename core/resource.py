"""Memory/disk estimation for the F5 Resource Analyzer. bpy-free; ops supplies
plain dicts extracted from datablocks.

All RAM/VRAM figures are **estimates** (Blender exposes no exact per-datablock
byte counts) and are labeled as such in the UI. Disk figures are accurate where
a file/packed size is available.

Model (documented, deliberately simple — good for ranking the heavy hitters):
  * Images:  RAM ≈ width*height*(depth_bits/8)  [depth is Blender's bits-per-pixel,
             so 8-bit RGBA=32, 32-bit float RGBA=128]. VRAM ≈ RAM * 4/3 (mipmaps).
  * Meshes:  RAM from element counts via per-element constants below.
             VRAM ≈ loops * GPU vertex stride (pos+normal+uv ~ 32 B).
"""

from __future__ import annotations

# Rough per-element mesh RAM constants (bytes). Approximate by design.
_MESH_VERT_B = 40
_MESH_EDGE_B = 16
_MESH_LOOP_B = 24
_MESH_POLY_B = 16
_MESH_GPU_STRIDE = 32  # per-loop GPU vertex (position + normal + one UV)
_MIPMAP_FACTOR = 4 / 3


def image_estimate(info: dict) -> dict:
    """info: {width, height, depth(bits/px)}. Returns {ram, vram} bytes."""
    px = max(0, info.get("width", 0)) * max(0, info.get("height", 0))
    ram = px * (info.get("depth", 0) // 8)
    return {"ram": ram, "vram": int(ram * _MIPMAP_FACTOR)}


def mesh_estimate(info: dict) -> dict:
    """info: {verts, edges, loops, polys}. Returns {ram, vram} bytes."""
    ram = (
        info.get("verts", 0) * _MESH_VERT_B
        + info.get("edges", 0) * _MESH_EDGE_B
        + info.get("loops", 0) * _MESH_LOOP_B
        + info.get("polys", 0) * _MESH_POLY_B
    )
    return {"ram": ram, "vram": info.get("loops", 0) * _MESH_GPU_STRIDE}


def human_bytes(n: int) -> str:
    """Human-readable size, e.g. 1536 -> '1.5 KB'."""
    n = float(max(0, n))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
