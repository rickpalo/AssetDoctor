"""F2 analysis: report what is linked into a file, grouped by source library.
bpy-free; the ops layer gathers the linked datablocks and performs the actual
make-local (which must happen in a live Blender session).

linked item dict contract (from ops):
    { "type": "Object", "name": "Tree", "library": "//libA.blend",
      "indirect": bool }   # indirect = pulled in transitively (library.parent set)
"""

from __future__ import annotations

import ntpath

from .report import Finding, Report


def _libname(path: str) -> str:
    return ntpath.basename(path) or path


def build_makelocal_report(items: list[dict]) -> Report:
    report = Report(title="Make local", feature="F2")

    by_lib: dict[str, list[dict]] = {}
    for it in items:
        by_lib.setdefault(it["library"], []).append(it)

    indirect_total = 0
    for lib in sorted(by_lib):
        members = sorted(by_lib[lib], key=lambda m: (m["type"], m["name"]))
        n_indirect = sum(1 for m in members if m.get("indirect"))
        indirect_total += n_indirect
        tag = f" ({n_indirect} indirect)" if n_indirect else ""
        report.add(Finding(
            category="linked_library",
            message=f"{len(members)} datablock(s) linked from {_libname(lib)}{tag}",
            severity="info",
            items=[f"{m['type']}/{m['name']}" for m in members],
            data={"library": lib, "indirect": n_indirect},
        ))

    report.add(Finding(
        category="summary",
        message=(
            f"{len(items)} linked datablock(s) from {len(by_lib)} librar(ies); "
            f"{indirect_total} indirect"
        ),
        severity="warning" if items else "info",
        data={"linked": len(items), "libraries": len(by_lib), "indirect": indirect_total},
    ))
    return report
