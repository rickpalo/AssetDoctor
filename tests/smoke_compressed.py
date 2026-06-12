"""Regression: BAT must read COMPRESSED .blend files (Blender's default).

    blender --background --factory-startup --python tests/smoke_compressed.py

Our committed fixtures are saved uncompressed, so this guards the real-world
case: a zstd-compressed file, read via Blender's bundled zstandard. If a future
Blender drops bundled zstandard this fails loudly here rather than silently in
the field.
"""

import glob
import pathlib
import sys
import tempfile
import traceback

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, glob.glob(str(REPO_ROOT / "wheels" / "blender_asset_tracer-*.whl"))[0])
sys.path.insert(0, str(REPO_ROOT))


def main():
    import bpy

    from core import blendscan

    checks = []
    try:
        checks.append(("Blender bundles zstandard", _has_zstandard()))

        bpy.ops.wm.read_factory_settings(use_empty=True)
        o = bpy.data.objects.new("O", bpy.data.meshes.new("M"))
        bpy.context.scene.collection.objects.link(o)
        tmp = pathlib.Path(tempfile.mkdtemp()) / "compressed.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(tmp), compress=True)

        # scan_file must succeed on the compressed file (no library links here).
        refs = blendscan.scan_file(tmp)
        checks.append(("scan_file reads compressed .blend", isinstance(refs, list)))

        ok = all(p for _, p in checks)
        for label, p in checks:
            print(f"  [{'OK' if p else 'FAIL'}] {label}")
        print("COMPRESSED_SMOKE_OK" if ok else "COMPRESSED_SMOKE_FAIL")
        return 0 if ok else 1
    except Exception:
        traceback.print_exc()
        print("COMPRESSED_SMOKE_FAIL")
        return 1


def _has_zstandard():
    try:
        import zstandard  # noqa: F401

        return True
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
