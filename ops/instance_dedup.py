"""Instance duplicate geometry: collapse identical-but-separate mesh datablocks
onto one shared datablock so the objects become instances (saving memory).

Report-first by default; on Apply (after auto-backup) each duplicate's users are
remapped onto the canonical via ``ID.user_remap`` and the now-unused local
datablocks are removed. Currently covers meshes; the engine is kind-agnostic so
curves/others can be added by extending the gather + a fingerprint.
"""

import bpy

from ..core.geometry_dedup import build_instance_plan


def _mesh_id(me) -> str:
    if me.library is not None:
        return f"{me.name} [{bpy.path.basename(me.library.filepath) or 'linked'}]"
    return me.name


def _gather(context):
    from .extract import extract_mesh
    from ..core.fingerprint import fingerprint_mesh

    items, id_to_db = [], {}
    for me in bpy.data.meshes:
        mid = _mesh_id(me)
        id_to_db[mid] = me
        try:
            fp = fingerprint_mesh(extract_mesh(me))
        except Exception:
            fp = None
        items.append({
            "id": mid,
            "name": me.name,
            "kind": "Mesh",
            "fingerprint": fp,
            "linked": me.library is not None,
            "users": me.users,
        })
    return items, id_to_db


class ASSETDOCTOR_OT_instance_geometry(bpy.types.Operator):
    bl_idname = "assetdoctor.instance_geometry"
    bl_label = "Instance Duplicate Geometry"
    bl_description = "Find identical separate meshes and make their objects share one (instancing)"
    bl_options = {"REGISTER", "UNDO"}

    apply: bpy.props.BoolProperty(
        name="Apply",
        description="Remap duplicate meshes onto one shared datablock and remove the copies. "
        "Takes a backup first. Leave off for a report-only dry run",
        default=False,
    )  # type: ignore[valid-type]

    @classmethod
    def description(cls, context, properties):
        if properties.apply:
            return ("Collapse identical separate meshes onto one shared datablock so the objects "
                    "become instances (saves memory). Takes a backup first; supports Undo")
        return "Report identical separate meshes that could be instanced to save memory (no changes)"

    def execute(self, context):
        from ..log import get_logger

        log = get_logger()
        items, id_to_db = _gather(context)
        report, plan = build_instance_plan(items)

        from .report_store import stash_report
        stash_report(context, report, "geo")
        for f in report.findings:
            log.info("GEO [%s] %s: %s", f.severity, f.category, f.message)

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
            canonical = id_to_db.get(group["canonical"])
            if canonical is None:
                continue
            for vid in group["victims"]:
                victim = id_to_db.get(vid)
                if victim is None or victim == canonical:
                    continue
                victim.user_remap(canonical)
                log.debug("GEO remap %s -> %s", vid, group["canonical"])
                remapped += 1
                if victim.library is None and victim.users == 0:
                    bpy.data.meshes.remove(victim)
                    removed += 1

        tail = f"Instanced {remapped}, removed {removed} duplicate mesh(es)."
        tail += f" Backup: {backup}" if backup else " (no backup written)"
        self.report({"INFO"}, f"{msg}. {tail}")
        return {"FINISHED"}
