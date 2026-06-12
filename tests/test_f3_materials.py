"""Unit tests for core.f3_materials (bpy-free)."""

from core.f3_materials import build_dedup_plan, choose_canonical, parse_name_list


def test_parse_name_list():
    assert parse_name_list("") == []
    assert parse_name_list("a, b ;c\nd") == ["a", "b", "c", "d"]
    assert parse_name_list("wood*, metal") == ["wood*", "metal"]


def _m(id_, name, linked=False, max_res=0):
    return {"id": id_, "name": name, "linked": linked, "max_res": max_res, "fingerprint": "H"}


def test_canonical_prefers_highest_resolution():
    members = [_m("Wood1K", "Wood", max_res=1024), _m("Wood2K", "Wood", max_res=2048)]
    best, reason = choose_canonical(members, [], [])
    assert best["id"] == "Wood2K"
    assert "resolution" in reason


def test_canonical_local_over_linked_at_equal_res():
    members = [_m("WoodLib", "Wood", linked=True, max_res=2048),
               _m("WoodLocal", "Wood", linked=False, max_res=2048)]
    best, _ = choose_canonical(members, [], [])
    assert best["id"] == "WoodLocal"


def test_whitelist_wins_over_resolution():
    members = [_m("WoodHi", "WoodHi", max_res=4096), _m("WoodMaster", "WoodMaster", max_res=512)]
    best, reason = choose_canonical(members, ["WoodMaster"], [])
    assert best["id"] == "WoodMaster"
    assert reason == "whitelisted"


def test_blacklisted_never_canonical():
    members = [_m("WoodBad", "WoodBad", max_res=4096), _m("WoodGood", "WoodGood", max_res=512)]
    best, _ = choose_canonical(members, [], ["WoodBad"])
    assert best["id"] == "WoodGood"


def test_all_blacklisted_keeps_best_with_note():
    members = [_m("A", "A", max_res=512), _m("B", "B", max_res=2048)]
    best, reason = choose_canonical(members, [], ["A", "B"])
    assert best["id"] == "B"  # highest res among the forced pool
    assert "blacklisted" in reason


def test_glob_patterns_match():
    members = [_m("wood_master", "wood_master", max_res=256), _m("wood_2k", "wood_2k", max_res=2048)]
    best, _ = choose_canonical(members, ["wood_master*"], [])
    assert best["id"] == "wood_master"


def test_build_plan_groups_and_summary():
    items = [
        _m("WoodA", "WoodA", max_res=1024),
        _m("WoodB", "WoodB", max_res=2048),
        {"id": "Stone", "name": "Stone", "linked": False, "max_res": 0, "fingerprint": "OTHER"},
    ]
    report, plan = build_dedup_plan(items)
    assert len(plan) == 1
    group = plan[0]
    assert group["canonical"] == "WoodB"  # higher res
    assert group["victims"] == ["WoodA"]
    summary = next(f for f in report.findings if f.category == "summary")
    assert summary.data["groups"] == 1
    assert summary.data["victims"] == 1


def test_build_plan_flags_linked_victims():
    items = [
        _m("WoodLocal", "Wood", linked=False, max_res=2048),
        _m("WoodLib", "Wood", linked=True, max_res=2048),
    ]
    report, plan = build_dedup_plan(items)
    assert plan[0]["canonical"] == "WoodLocal"
    assert plan[0]["linked_victims"] == ["WoodLib"]
    assert any(f.category == "linked_victim" for f in report.findings)


def test_no_duplicates_empty_plan():
    items = [_m("A", "A"), {"id": "B", "name": "B", "linked": False, "max_res": 0,
                            "fingerprint": "ZZZ"}]
    # distinct fingerprints
    items[0]["fingerprint"] = "AAA"
    report, plan = build_dedup_plan(items)
    assert plan == []
