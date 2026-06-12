"""End-to-end report-system v2 check in Blender:

    blender --background --factory-startup --python tests/smoke_report.py

Covers persistence (two scans both kept), the selector, expand toggle on the
active feature, select-the-datablock, export to a file, and clear (removes the
active report, keeps the other).
"""

import glob
import os
import pathlib
import sys
import tempfile
import traceback

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT.parent))
_bat = glob.glob(str(REPO_ROOT / "wheels" / "blender_asset_tracer-*.whl"))
if _bat:
    sys.path.insert(0, _bat[0])
PKG = REPO_ROOT.name


def main():
    import bpy

    addon = __import__(PKG)
    addon.register()
    Report = __import__(f"{PKG}.core.report", fromlist=["Report"]).Report
    tree_mod = __import__(f"{PKG}.core.tree", fromlist=["x"])
    store = __import__(f"{PKG}.ops.report_store", fromlist=["x"])

    checks = []
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for nm in ("OrphanMat", "WoodA", "WoodB"):
            bpy.data.materials.new(nm).use_nodes = True
        obj = bpy.data.objects.new("Cube", bpy.data.meshes.new("CubeMesh"))
        obj.data.materials.append(bpy.data.materials["WoodA"])
        bpy.context.scene.collection.objects.link(obj)
        wm = bpy.context.window_manager

        bpy.ops.assetdoctor.scan_orphans("EXEC_DEFAULT", purge_orphans=False)   # f4
        bpy.ops.assetdoctor.material_dedup("EXEC_DEFAULT", apply=False)         # f3

        checks.append(("f4 persisted", bool(getattr(wm, "assetdoctor_rep_f4"))))
        checks.append(("f3 persisted (after f4)", bool(getattr(wm, "assetdoctor_rep_f3"))))
        checks.append(("active is last run (f3)", store.active_feature(wm) == "f3"))
        checks.append(("both selectable", {k for k, _ in store.available_features(wm)} >= {"f3", "f4"}))

        bpy.ops.assetdoctor.report_select(feature="f4")
        checks.append(("selector switches active", store.active_feature(wm) == "f4"))

        rep = Report.from_json(getattr(wm, "assetdoctor_rep_f4"))
        first = tree_mod.report_to_tree(rep)[0].key
        before = first in store.get_expanded(wm, store.exp_prop("f4"))
        bpy.ops.assetdoctor.report_toggle(key=first, prop=store.exp_prop("f4"))
        after = first in store.get_expanded(wm, store.exp_prop("f4"))
        checks.append(("toggle flips active feature's expand", before != after))

        out = os.path.join(tempfile.mkdtemp(), "rep.txt")
        bpy.ops.assetdoctor.export_report("EXEC_DEFAULT", source="report", filepath=out)
        checks.append(("export wrote a file", os.path.isfile(out) and os.path.getsize(out) > 0))

        bpy.ops.object.select_all(action="DESELECT")
        r = bpy.ops.assetdoctor.select_datablock(type="Material", name="WoodA")
        checks.append(("select material picks object", r == {"FINISHED"} and obj.select_get()))

        bpy.ops.assetdoctor.report_clear()  # clears active (f4)
        checks.append(("clear removes active but keeps the other",
                       not getattr(wm, "assetdoctor_rep_f4") and bool(getattr(wm, "assetdoctor_rep_f3"))))

        ok = all(p for _, p in checks)
        for label, p in checks:
            print(f"  [{'OK' if p else 'FAIL'}] {label}")
        print("REPORT_SMOKE_OK" if ok else "REPORT_SMOKE_FAIL")
        return 0 if ok else 1
    except Exception:
        traceback.print_exc()
        print("REPORT_SMOKE_FAIL")
        return 1
    finally:
        addon.unregister()


if __name__ == "__main__":
    sys.exit(main())
