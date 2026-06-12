"""Find mesh objects whose name contains a keyword (default: "billboard").

Scans every ``*.blend`` under a directory, newest file first, reading each one
OFFLINE via Blender Asset Tracer (BAT) -- no Blender launch needed. Objects live
in the DNA as ``OB`` blocks; the name is ``id.name`` (with a 2-char "OB" prefix)
and ``type == 1`` (OB_MESH) marks a mesh.

Usage:
    python tools/find_billboards.py <directory> [keyword]
    python tools/find_billboards.py <directory> [keyword] --first   # stop at first hit

Examples:
    python tools/find_billboards.py "E:/BlenderSync/SynologyDrive"
    python tools/find_billboards.py "E:/assets" tree --first
"""

from __future__ import annotations

import glob
import pathlib
import sys

OB_MESH = 1  # Blender DNA object type for a mesh (object.type field)


ZSTD_HINT = (
    "Blender 3.0+ saves compressed .blend files with ZStandard, which needs the\n"
    "    `zstandard` Python module. Install it with:\n\n"
    "        pip install zstandard\n"
)


def _ensure_bat_importable() -> None:
    """Put the bundled BAT wheel on sys.path if BAT isn't already importable."""
    try:
        import blender_asset_tracer.blendfile  # noqa: F401

        return
    except Exception:
        pass
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    for whl in glob.glob(str(repo_root / "wheels" / "blender_asset_tracer-*.whl")):
        sys.path.insert(0, whl)
        return


def _zstandard_available() -> bool:
    """Whether the `zstandard` module is importable (needed for compressed files)."""
    try:
        import zstandard  # noqa: F401

        return True
    except Exception:
        return False


def _is_zstd_error(exc: Exception) -> bool:
    """True when a per-file read failed only because zstandard is missing."""
    return "zstandard" in str(exc).lower()


def iter_blend_files_newest_first(root: pathlib.Path):
    """Yield ``*.blend`` under ``root`` sorted by modification time, newest first."""
    ignore = {".git", "__pycache__", "blender_backups", "dist"}
    files = [
        p
        for p in root.rglob("*.blend")
        if not any(part in ignore for part in p.parts)
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def find_mesh_objects(blend: pathlib.Path, keyword: str) -> list[str]:
    """Return names of MESH objects in ``blend`` whose name contains ``keyword``
    (case-insensitive). Reads the file offline via BAT."""
    from blender_asset_tracer import blendfile

    needle = keyword.lower()
    hits: list[str] = []
    bfile = blendfile.BlendFile(blend)
    try:
        for block in bfile.find_blocks_from_code(b"OB"):
            if block.get(b"type") != OB_MESH:
                continue
            raw = block.get((b"id", b"name"), as_str=True, default="")
            name = raw[2:] if raw[:2] == "OB" else raw  # strip the "OB" id prefix
            if needle in name.lower():
                hits.append(name)
    finally:
        bfile.close()
    return hits


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    stop_first = "--first" in argv
    if not args:
        print(__doc__)
        return 2

    root = pathlib.Path(args[0])
    keyword = args[1] if len(args) > 1 else "billboard"
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 2

    _ensure_bat_importable()

    if not _zstandard_available():
        print(
            "WARNING: the `zstandard` module is not installed.\n"
            "    Compressed .blend files (the default since Blender 3.0) cannot be\n"
            "    read and would be silently skipped. " + ZSTD_HINT
        )

    total_files = 0
    matched_files = 0
    for blend in iter_blend_files_newest_first(root):
        total_files += 1
        try:
            hits = find_mesh_objects(blend, keyword)
        except Exception as exc:  # corrupt/unreadable -> note and keep going
            if _is_zstd_error(exc):
                # A real dependency gap, not a corrupt file -- stop and tell the user.
                print(f"\nERROR reading {blend}\n    {ZSTD_HINT}")
                return 3
            print(f"  ! {blend}  ({type(exc).__name__}: {exc})")
            continue
        if hits:
            matched_files += 1
            print(f"{blend}")
            for name in hits:
                print(f"    MESH  {name}")
            if stop_first:
                print(f"\nStopped at first match (--first).")
                return 0

    print(
        f"\nScanned {total_files} .blend file(s); "
        f"{matched_files} contained a mesh matching {keyword!r}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
