"""Build the F5 'by datablock type' resource tree. bpy-free.

Input: per-datablock estimate dicts from the ops layer:
    { "type": "Image", "name": "wood", "ram": int, "vram": int, "disk": int,
      "users": int }
Output: TreeNodes (type → datablock), each datablock counted ONCE, sorted
biggest-first by RAM, with rolled-up per-type totals and a grand total.
"""

from __future__ import annotations

from .resource import human_bytes
from .tree import TreeNode


def _detail(ram: int, vram: int, disk: int, users: int | None = None) -> str:
    parts = [f"{human_bytes(ram)} RAM", f"{human_bytes(vram)} VRAM"]
    if disk:
        parts.append(f"{human_bytes(disk)} disk")
    if users is not None:
        parts.append(f"{users}u")
    return "  ·  ".join(parts)


def build_resource_tree(items: list[dict]) -> tuple[list[TreeNode], dict]:
    """Return (type nodes sorted by total RAM desc, grand totals dict)."""
    by_type: dict[str, list[dict]] = {}
    for it in items:
        by_type.setdefault(it["type"], []).append(it)

    typed_nodes: list[tuple[int, TreeNode]] = []
    g_ram = g_vram = g_disk = 0
    for type_name, members in by_type.items():
        t_ram = sum(m.get("ram", 0) for m in members)
        t_vram = sum(m.get("vram", 0) for m in members)
        t_disk = sum(m.get("disk", 0) for m in members)
        g_ram += t_ram
        g_vram += t_vram
        g_disk += t_disk

        type_node = TreeNode(
            key=f"type:{type_name}",
            label=f"{type_name} ({len(members)})",
            detail=_detail(t_ram, t_vram, t_disk),
        )
        for m in sorted(members, key=lambda d: d.get("ram", 0), reverse=True):
            type_node.children.append(TreeNode(
                key=f"type:{type_name}:{m['name']}",
                label=m["name"],
                detail=_detail(m.get("ram", 0), m.get("vram", 0), m.get("disk", 0),
                               m.get("users", 0)),
                ref={"type": type_name, "name": m["name"]},
            ))
        typed_nodes.append((t_ram, type_node))

    typed_nodes.sort(key=lambda pair: pair[0], reverse=True)
    nodes = [node for _ram, node in typed_nodes]
    totals = {"ram": g_ram, "vram": g_vram, "disk": g_disk}
    return nodes, totals
