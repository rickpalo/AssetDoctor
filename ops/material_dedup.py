"""F3 - find duplicate / multi-resolution materials and remap them to one source.

Report-first by default; on Apply (after auto-backup) every duplicate's users
are remapped onto the chosen canonical via ``ID.user_remap`` and local victims
are removed. Linked victims keep existing in their library (we only repoint
their local users).
"""

import bpy

from ..core.f3_materials import build_dedup_plan, parse_name_list
from ..prefs import get_prefs


def _material_id(mat) -> str:
    """Unique, human-readable key (handles a local + linked same-named pair)."""
    if mat.library is not None:
        return f"{mat.name} [{bpy.path.basename(mat.library.filepath) or 'linked'}]"
    return mat.name


def _max_texture_res(mat) -> int:
    if not mat.use_nodes or mat.node_tree is None:
        return 0
    best = 0
    for node in mat.node_tree.nodes:
        img = getattr(node, "image", None)
        if img is not None and len(img.size) >= 1:
            best = max(best, max(img.size))
    return best


def _gather(context):
    from .extract import extract_material
    from ..core.fingerprint import fingerprint_material

    prefs = get_prefs(context)
    res_pattern = prefs.resolution_token_regex if prefs else None

    items, id_to_mat = [], {}
    for mat in bpy.data.materials:
        mid = _material_id(mat)
        id_to_mat[mid] = mat
        try:
            fp = fingerprint_material(extract_material(mat, res_pattern))
        except Exception:
            fp = None
        items.append({
            "id": mid,
            "name": mat.name,
            "fingerprint": fp,
            "linked": mat.library is not None,
            "max_res": _max_texture_res(mat),
        })
    return items, id_to_mat


class ASSETDOCTOR_OT_material_dedup(bpy.types.Operator):
    bl_idname = "assetdoctor.material_dedup"
    bl_label = "Find Duplicate Materials"
    bl_description = "Find duplicate / multi-resolution materials and remap them to a single source"
    bl_options = {"REGISTER", "UNDO"}

    apply: bpy.props.BoolProperty(
        name="Apply (remap & purge)",
        description="Remap duplicates onto the canonical material and remove local victims. "
        "Takes a backup first. Leave off for a report-only dry run",
        default=False,
    )  # type: ignore[valid-type]

    @classmethod
    def description(cls, context, properties):
        if properties.apply:
            return ("Remap duplicate/near-duplicate (incl. 1K/2K) materials onto a single "
                    "canonical and remove local duplicates. Takes a backup first; supports Undo")
        return ("Find duplicate / multi-resolution materials and report which would be merged "
                "(no changes). Canonical chosen via the white/black lists in Preferences")

    def execute(self, context):
        from ..log import get_logger

        log = get_logger()
        prefs = get_prefs(context)
        whitelist = parse_name_list(prefs.material_whitelist if prefs else "")
        blacklist = parse_name_list(prefs.material_blacklist if prefs else "")

        items, id_to_mat = _gather(context)
        report, plan = build_dedup_plan(items, whitelist, blacklist)

        from .report_store import stash_report
        stash_report(context, report, "f3")
        for f in report.findings:
            log.info("F3 [%s] %s: %s", f.severity, f.category, f.message)

        summary = next((f for f in report.findings if f.category == "summary"), None)
        msg = summary.message if summary else "scan complete"

        if not self.apply or not plan:
            level = "WARNING" if report.count("warning") else "INFO"
            self.report({level}, msg + (" (dry run)" if not self.apply else ""))
            return {"FINISHED"}

        from .safety import auto_backup

        backup = auto_backup(context)
        remapped, removed = 0, 0
        for group in plan:
            canonical = id_to_mat.get(group["canonical"])
            if canonical is None:
                continue
            for vid in group["victims"]:
                victim = id_to_mat.get(vid)
                if victim is None or victim == canonical:
                    continue
                victim.user_remap(canonical)
                log.debug("F3 remap %s -> %s", vid, group["canonical"])
                remapped += 1
                # Remove now-unused local victims; linked ones stay in their library.
                if victim.library is None and victim.users == 0:
                    bpy.data.materials.remove(victim)
                    removed += 1

        tail = f"Remapped {remapped}, removed {removed} local duplicate(s)."
        tail += f" Backup: {backup}" if backup else " (no backup written)"
        self.report({"INFO"}, f"{msg}. {tail}")
        return {"FINISHED"}
