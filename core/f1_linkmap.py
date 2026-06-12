"""F1 orchestration: turn a folder scan into a reviewable Report + link graph.

bpy-free. The operator layer calls :func:`build_link_report`, then shows the
Report and offers the JSON/CSV/DOT exports (the graph's ``to_dot``; the Report's
own ``to_json``/``to_csv``).
"""

from __future__ import annotations

import ntpath
import pathlib

from .blendscan import ScanResult, map_folder
from .report import Finding, Report


def _name(path: str) -> str:
    return ntpath.basename(path) or path


def build_link_report(root: pathlib.Path) -> tuple[Report, ScanResult]:
    """Scan ``root`` synchronously and produce the F1 link-map report."""
    scan = map_folder(root)
    return report_from_scan(scan, root), scan


def report_from_scan(scan: ScanResult, root: pathlib.Path) -> Report:
    """Build the F1 report from an already-computed scan (sync or modal)."""
    report = Report(title=f"Link map: {root}", feature="F1")

    # Per-file read errors.
    for path, msg in sorted(scan.errors.items()):
        report.add(
            Finding(
                category="unreadable_file",
                message=f"Could not read {_name(path)}: {msg}",
                severity="error",
                items=[path],
            )
        )

    # Broken links and non-relative (absolute) link paths.
    for path, refs in sorted(scan.refs.items()):
        for ref in refs:
            if not ref.exists:
                report.add(
                    Finding(
                        category="broken_link",
                        message=f"{_name(path)} links missing library {ref.stored_path}",
                        severity="error",
                        items=[path, ref.resolved_path or ref.stored_path],
                        data={"stored": ref.stored_path},
                    )
                )
            elif not ref.is_relative:
                report.add(
                    Finding(
                        category="absolute_path",
                        message=f"{_name(path)} links {ref.stored_path} by absolute path "
                        "(not portable; consider making it relative)",
                        severity="warning",
                        items=[path, ref.resolved_path],
                        data={"stored": ref.stored_path},
                    )
                )

    # Circular library references.
    for cycle in scan.graph.find_cycles():
        report.add(
            Finding(
                category="circular_link",
                message="Circular library reference: "
                + " -> ".join(_name(n) for n in cycle),
                severity="error",
                items=cycle,
            )
        )

    # Summary (info).
    g = scan.graph
    report.add(
        Finding(
            category="summary",
            message=(
                f"{len(g.nodes)} files, {len(g.edges)} link(s); "
                f"{len(g.roots())} root(s), {len(g.leaves())} leaf/asset file(s)"
            ),
            severity="info",
            data={
                "files": len(g.nodes),
                "links": len(g.edges),
                "roots": sorted(_name(n) for n in g.roots()),
                "leaves": sorted(_name(n) for n in g.leaves()),
            },
        )
    )
    return report
