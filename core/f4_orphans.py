"""F4 analysis: classify datablocks (orphan / fake-user-only / in-use) and find
identical ones. bpy-free; the ops layer supplies the datablock info dicts.

Classification rule, verified against Blender 5.1:
    users == 0                      -> "orphan"      (removed on reload/save)
    use_fake_user and users == 1    -> "fake_only"   (kept alive only by Fake User)
    otherwise (users >= 1)          -> "in_use"
    id.library is not None          -> "linked"      (lives in another file; skip)

datablock info dict contract (from ops):
    { "type": "Material", "name": "Wood", "users": int,
      "fake": bool, "linked": bool, "fingerprint": str | None }
"""

from __future__ import annotations

from .cluster import group_identical
from .report import Finding, Report


def classify(users: int, fake: bool, linked: bool) -> str:
    if linked:
        return "linked"
    if users == 0:
        return "orphan"
    if fake and users == 1:
        return "fake_only"
    return "in_use"


def _label(info: dict) -> str:
    return f"{info['type']}/{info['name']}"


def build_orphan_report(items: list[dict]) -> Report:
    """Produce the F4 report from datablock info dicts."""
    report = Report(title="Orphans, fake users & duplicates", feature="F4")

    enriched = [{**it, "cls": classify(it["users"], it["fake"], it["linked"])} for it in items]
    cls_by_label = {_label(e): e["cls"] for e in enriched}

    orphans = sorted((e for e in enriched if e["cls"] == "orphan"), key=_label)
    fakes = sorted((e for e in enriched if e["cls"] == "fake_only"), key=_label)

    if orphans:
        report.add(Finding(
            category="orphan",
            message=f"{len(orphans)} orphaned datablock(s) — no users; removed on reload/save",
            severity="warning",
            items=[_label(e) for e in orphans],
        ))
    if fakes:
        report.add(Finding(
            category="fake_only",
            message=f"{len(fakes)} datablock(s) kept alive only by a Fake User",
            severity="info",
            items=[_label(e) for e in fakes],
        ))

    # Identity clusters across non-linked, fingerprintable datablocks. Key on
    # type+fingerprint so types never merge.
    labeled = [
        (_label(e), f"{e['type']}:{e['fingerprint']}")
        for e in enriched
        if not e["linked"] and e["fingerprint"]
    ]
    clusters = group_identical(sorted(labeled))
    for _key, members in sorted(clusters.items(), key=lambda kv: kv[1][0]):
        members = sorted(members)
        annotated = [f"{m} [{cls_by_label.get(m, '?')}]" for m in members]
        report.add(Finding(
            category="identical",
            message=f"{len(members)} identical datablocks: " + ", ".join(annotated),
            severity="warning",
            items=members,
            data={"members": [{"id": m, "cls": cls_by_label.get(m)} for m in members]},
        ))

    report.add(Finding(
        category="summary",
        message=(
            f"{len(enriched)} datablocks scanned: {len(orphans)} orphan, "
            f"{len(fakes)} fake-only, {len(clusters)} identical group(s)"
        ),
        severity="info",
        data={
            "scanned": len(enriched),
            "orphans": len(orphans),
            "fake_only": len(fakes),
            "identical_groups": len(clusters),
        },
    ))
    return report
