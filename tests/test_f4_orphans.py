"""Unit tests for core.f4_orphans (bpy-free).

Locks the classification semantics verified against Blender 5.1 and the report
structure (orphan / fake-only lists + identity clusters).
"""

from core.f4_orphans import build_orphan_report, classify


def test_classify_matches_blender_semantics():
    assert classify(users=0, fake=False, linked=False) == "orphan"
    assert classify(users=1, fake=True, linked=False) == "fake_only"
    assert classify(users=1, fake=False, linked=False) == "in_use"
    assert classify(users=2, fake=True, linked=False) == "in_use"  # 1 real + fake
    assert classify(users=0, fake=False, linked=True) == "linked"


def _item(type_, name, users, fake=False, linked=False, fp=None):
    return {"type": type_, "name": name, "users": users, "fake": fake,
            "linked": linked, "fingerprint": fp}


def test_report_lists_orphans_and_fakes():
    items = [
        _item("Material", "Orphan1", 0),
        _item("Mesh", "Orphan2", 0),
        _item("Material", "Kept", 1, fake=True),
        _item("Material", "Used", 3),
    ]
    report = build_orphan_report(items)
    orphan = next(f for f in report.findings if f.category == "orphan")
    fake = next(f for f in report.findings if f.category == "fake_only")
    assert set(orphan.items) == {"Material/Orphan1", "Mesh/Orphan2"}
    assert fake.items == ["Material/Kept"]


def test_identity_cluster_groups_same_fingerprint():
    items = [
        _item("Material", "WoodA", 1, fp="HASH"),
        _item("Material", "WoodB", 0, fp="HASH"),  # an orphan identical to WoodA
        _item("Material", "Other", 1, fp="DIFF"),
    ]
    report = build_orphan_report(items)
    ident = [f for f in report.findings if f.category == "identical"]
    assert len(ident) == 1
    assert set(ident[0].items) == {"Material/WoodA", "Material/WoodB"}
    # member classifications recorded for the Apply step
    classes = {m["id"]: m["cls"] for m in ident[0].data["members"]}
    assert classes["Material/WoodA"] == "in_use"
    assert classes["Material/WoodB"] == "orphan"


def test_clusters_do_not_cross_types():
    # Same fingerprint string but different types must not merge.
    items = [_item("Material", "M", 1, fp="X"), _item("Mesh", "Me", 1, fp="X")]
    report = build_orphan_report(items)
    assert not [f for f in report.findings if f.category == "identical"]


def test_linked_excluded_from_clusters_and_classes():
    items = [
        _item("Material", "Local", 1, fp="H"),
        _item("Material", "FromLib", 1, linked=True, fp="H"),
    ]
    report = build_orphan_report(items)
    assert not [f for f in report.findings if f.category == "identical"]


def test_summary_counts():
    items = [_item("Material", "O", 0), _item("Material", "K", 1, fake=True)]
    report = build_orphan_report(items)
    summary = next(f for f in report.findings if f.category == "summary")
    assert summary.data["orphans"] == 1
    assert summary.data["fake_only"] == 1
    assert summary.data["scanned"] == 2
