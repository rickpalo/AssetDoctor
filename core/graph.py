"""Dependency-graph model for the folder-wide link map (F1).

Nodes are .blend files (identified by normalized path string); edges mean
"source links one or more datablocks from target". This is a thin directed
multigraph with just the queries F1 needs: roots/leaves, transitive closure,
and cycle detection. bpy-free and unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LinkEdge:
    source: str  # file that contains the link reference
    target: str  # library file being linked from
    datablock: str = ""  # e.g. "Object/Tree" (optional detail)


@dataclass
class DepGraph:
    edges: list[LinkEdge] = field(default_factory=list)
    nodes: set[str] = field(default_factory=set)

    def add_edge(self, source: str, target: str, datablock: str = "") -> None:
        self.nodes.add(source)
        self.nodes.add(target)
        self.edges.append(LinkEdge(source, target, datablock))

    def add_node(self, path: str) -> None:
        self.nodes.add(path)

    def targets_of(self, source: str) -> set[str]:
        """Files directly linked *by* ``source``."""
        return {e.target for e in self.edges if e.source == source}

    def sources_of(self, target: str) -> set[str]:
        """Files that directly link *from* ``target``."""
        return {e.source for e in self.edges if e.target == target}

    def roots(self) -> set[str]:
        """Files nothing links from (top-level scenes)."""
        linked = {e.target for e in self.edges}
        return self.nodes - linked

    def leaves(self) -> set[str]:
        """Files that link nothing (pure asset libraries)."""
        linkers = {e.source for e in self.edges}
        return self.nodes - linkers

    def to_dot(self, label_fn=None) -> str:
        """Render the graph as Graphviz DOT. ``label_fn`` maps a node path to a
        display label (defaults to the file's basename)."""
        import ntpath
        import posixpath

        def default_label(path: str) -> str:
            return ntpath.basename(path) or posixpath.basename(path) or path

        label = label_fn or default_label
        lines = ["digraph deps {", "  rankdir=LR;", '  node [shape=box];']
        for node in sorted(self.nodes):
            lines.append(f'  "{node}" [label="{label(node)}"];')
        for e in self.edges:
            attr = f' [label="{e.datablock}"]' if e.datablock else ""
            lines.append(f'  "{e.source}" -> "{e.target}"{attr};')
        lines.append("}")
        return "\n".join(lines)

    def find_cycles(self) -> list[list[str]]:
        """Return simple cycles as lists of file paths. Empty if acyclic."""
        adjacency: dict[str, set[str]] = {n: set() for n in self.nodes}
        for e in self.edges:
            adjacency[e.source].add(e.target)

        cycles: list[list[str]] = []
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.nodes}
        stack: list[str] = []

        def visit(node: str) -> None:
            color[node] = GRAY
            stack.append(node)
            for nxt in adjacency[node]:
                if color[nxt] == GRAY:
                    # Found a back-edge; record the cycle slice.
                    idx = stack.index(nxt)
                    cycles.append(stack[idx:] + [nxt])
                elif color[nxt] == WHITE:
                    visit(nxt)
            stack.pop()
            color[node] = BLACK

        for node in self.nodes:
            if color[node] == WHITE:
                visit(node)
        return cycles
