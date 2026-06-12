"""Unit tests for core.f2_makelocal (bpy-free)."""

from core.f2_makelocal import build_makelocal_report


def _it(type_, name, library, indirect=False):
    return {"type": type_, "name": name, "library": library, "indirect": indirect}


def test_empty_is_info_summary():
    report = build_makelocal_report([])
    summary = next(f for f in report.findings if f.category == "summary")
    assert summary.severity == "info"
    assert summary.data == {"linked": 0, "libraries": 0, "indirect": 0}


def test_groups_by_library_and_counts_indirect():
    items = [
        _it("Object", "Tree", "//libA.blend"),
        _it("Mesh", "TreeMesh", "//libA.blend"),
        _it("Object", "Rock", "//libB.blend", indirect=True),
    ]
    report = build_makelocal_report(items)
    libs = [f for f in report.findings if f.category == "linked_library"]
    assert len(libs) == 2
    summary = next(f for f in report.findings if f.category == "summary")
    assert summary.data == {"linked": 3, "libraries": 2, "indirect": 1}
    assert summary.severity == "warning"  # there is linked data to act on


def test_library_finding_lists_members():
    items = [_it("Object", "Tree", "//libA.blend"), _it("Material", "Bark", "//libA.blend")]
    report = build_makelocal_report(items)
    f = next(f for f in report.findings if f.category == "linked_library")
    assert set(f.items) == {"Object/Tree", "Material/Bark"}
    assert f.data["library"] == "//libA.blend"
