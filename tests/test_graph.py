"""Unit tests for core.graph — the F1 dependency-graph model."""

from core.graph import DepGraph


def _g():
    g = DepGraph()
    # scene.blend links from chars.blend and props.blend; chars links from rigs.blend
    g.add_edge("scene.blend", "chars.blend", "Object/Hero")
    g.add_edge("scene.blend", "props.blend", "Object/Chair")
    g.add_edge("chars.blend", "rigs.blend", "Armature/HeroRig")
    return g


def test_targets_and_sources():
    g = _g()
    assert g.targets_of("scene.blend") == {"chars.blend", "props.blend"}
    assert g.sources_of("rigs.blend") == {"chars.blend"}


def test_roots_and_leaves():
    g = _g()
    assert g.roots() == {"scene.blend"}
    assert g.leaves() == {"props.blend", "rigs.blend"}


def test_acyclic_has_no_cycles():
    assert _g().find_cycles() == []


def test_detects_cycle():
    g = DepGraph()
    g.add_edge("a.blend", "b.blend")
    g.add_edge("b.blend", "c.blend")
    g.add_edge("c.blend", "a.blend")
    cycles = g.find_cycles()
    assert cycles, "expected at least one cycle"
    # Each reported cycle starts and ends on the same node.
    assert all(cyc[0] == cyc[-1] for cyc in cycles)


def test_isolated_node_is_root_and_leaf():
    g = DepGraph()
    g.add_node("lonely.blend")
    assert "lonely.blend" in g.roots()
    assert "lonely.blend" in g.leaves()
