"""Validate fingerprint extraction against real Blender data:

    blender --background --factory-startup --python tests/smoke_fingerprint.py

Proves the core/ops contract end-to-end: a 1K and a 2K variant of the same
material hash IDENTICALLY, genuinely different materials differ, mesh identity
works, and image identity stays resolution-SENSITIVE.
"""

import glob
import pathlib
import sys
import traceback

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT.parent))
_bat = glob.glob(str(REPO_ROOT / "wheels" / "blender_asset_tracer-*.whl"))
if _bat:
    sys.path.insert(0, _bat[0])
PKG = REPO_ROOT.name


def _wood_mat(bpy, name, image, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def main():
    import bpy

    __import__(PKG)
    extract = __import__(f"{PKG}.ops.extract", fromlist=["x"])
    fp = __import__(f"{PKG}.core.fingerprint", fromlist=["x"])

    bpy.ops.wm.read_factory_settings(use_empty=True)

    wood_1k = bpy.data.images.new("wood_1k", 1024, 1024)
    wood_2k = bpy.data.images.new("wood_2k", 2048, 2048)
    metal_2k = bpy.data.images.new("metal_2k", 2048, 2048)

    m1 = _wood_mat(bpy, "WoodA", wood_1k)
    m2 = _wood_mat(bpy, "WoodB", wood_2k)
    m3 = _wood_mat(bpy, "MetalX", metal_2k, metallic=1.0)

    f1 = fp.fingerprint_material(extract.extract_material(m1))
    f2 = fp.fingerprint_material(extract.extract_material(m2))
    f3 = fp.fingerprint_material(extract.extract_material(m3))

    checks = []
    checks.append(("1K==2K (resolution-agnostic)", f1 == f2))
    checks.append(("wood != metal", f1 != f3))

    # Mesh identity
    me_a = bpy.data.meshes.new("A")
    me_a.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    me_a.update()
    me_b = bpy.data.meshes.new("B")
    me_b.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    me_b.update()
    me_c = bpy.data.meshes.new("C")
    me_c.from_pydata([(0, 0, 0), (1, 0, 0), (0, 2, 0)], [], [(0, 1, 2)])
    me_c.update()
    ha = fp.fingerprint_mesh(extract.extract_mesh(me_a))
    hb = fp.fingerprint_mesh(extract.extract_mesh(me_b))
    hc = fp.fingerprint_mesh(extract.extract_mesh(me_c))
    checks.append(("identical meshes equal", ha == hb))
    checks.append(("moved-vertex mesh differs", ha != hc))

    # Image identity is resolution-sensitive
    i1 = fp.fingerprint_image(extract.extract_image(wood_1k))
    i2 = fp.fingerprint_image(extract.extract_image(wood_2k))
    checks.append(("image identity res-sensitive", i1 != i2))

    ok = all(passed for _, passed in checks)
    for label, passed in checks:
        print(f"  [{'OK' if passed else 'FAIL'}] {label}")
    print("FP_SMOKE_OK" if ok else "FP_SMOKE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        print("FP_SMOKE_FAIL")
        sys.exit(1)
