"""Unit tests for core.cluster.group_identical."""

from core.cluster import group_identical


def test_groups_only_duplicates():
    items = [("a", "h1"), ("b", "h1"), ("c", "h2"), ("d", "h3"), ("e", "h3")]
    groups = group_identical(items)
    assert groups == {"h1": ["a", "b"], "h3": ["d", "e"]}
    assert "h2" not in groups  # singletons dropped


def test_empty_input():
    assert group_identical([]) == {}


def test_all_unique():
    assert group_identical([("a", "1"), ("b", "2")]) == {}


def test_preserves_name_order():
    items = [("z", "h"), ("a", "h"), ("m", "h")]
    assert group_identical(items) == {"h": ["z", "a", "m"]}
