"""Unit tests for core.report — the serialization layer shared by F1-F4.

Per project testing philosophy: every function gets a test, and any bug found
later gets a regression test added here in the same commit.
"""

import csv
import io
import json

import pytest

from core.report import Finding, Report, SEVERITIES


def test_finding_defaults():
    f = Finding(category="broken_link", message="missing lib")
    assert f.severity == "info"
    assert f.items == []
    assert f.data == {}


def test_finding_rejects_bad_severity():
    with pytest.raises(ValueError):
        Finding(category="x", message="y", severity="critical")


def test_report_add_and_count():
    r = Report(title="Orphans", feature="F4")
    r.add(Finding("orphan", "m1", severity="warning"))
    r.add(Finding("orphan", "m2", severity="error"))
    r.add(Finding("info", "scan done"))
    assert r.count() == 3
    assert r.count("warning") == 1
    assert r.count("error") == 1
    assert r.count("info") == 1


def test_report_count_rejects_unknown_severity():
    r = Report(title="x", feature="F1")
    with pytest.raises(ValueError):
        r.count("nope")


def test_max_severity_empty_is_info():
    assert Report(title="x", feature="F1").max_severity == "info"


def test_max_severity_picks_highest():
    r = Report(title="x", feature="F1")
    r.add(Finding("a", "m", severity="info"))
    r.add(Finding("b", "m", severity="warning"))
    assert r.max_severity == "warning"
    r.add(Finding("c", "m", severity="error"))
    assert r.max_severity == "error"


def test_to_json_roundtrips():
    r = Report(title="Materials", feature="F3")
    r.add(Finding("dup", "wood", severity="warning", items=["wood_1k", "wood_2k"],
                  data={"canonical": "wood_2k"}))
    parsed = json.loads(r.to_json())
    assert parsed["feature"] == "F3"
    assert parsed["findings"][0]["items"] == ["wood_1k", "wood_2k"]
    assert parsed["findings"][0]["data"]["canonical"] == "wood_2k"


def test_to_csv_has_header_and_rows():
    r = Report(title="Materials", feature="F3")
    r.add(Finding("dup", "near-dup wood", severity="warning",
                  items=["wood_1k", "wood_2k"], data={"canonical": "wood_2k"}))
    rows = list(csv.reader(io.StringIO(r.to_csv())))
    assert rows[0] == ["category", "severity", "message", "items", "data"]
    assert rows[1][0] == "dup"
    assert rows[1][3] == "wood_1k;wood_2k"
    assert json.loads(rows[1][4])["canonical"] == "wood_2k"


def test_severities_ordering_constant():
    # Order is relied on by max_severity; guard against accidental reordering.
    assert SEVERITIES == ("info", "warning", "error")
