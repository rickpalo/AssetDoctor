"""Group items that share a fingerprint. bpy-free; used by F3, F4 and the M6
cross-file duplication census.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Iterable


def group_identical(items: Iterable[tuple[str, Hashable]]) -> dict[Hashable, list[str]]:
    """Map fingerprint -> [names], keeping only groups with 2+ members.

    ``items`` is an iterable of ``(name, fingerprint)`` pairs. Insertion order of
    names within each group is preserved (callers can pass pre-sorted input for
    determinism).
    """
    groups: dict[Hashable, list[str]] = defaultdict(list)
    for name, fp in items:
        groups[fp].append(name)
    return {fp: names for fp, names in groups.items() if len(names) > 1}
