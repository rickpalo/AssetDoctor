"""F4 - find orphans & fake-user-only data, group identical ones.

Read-only report by default. Optional purge of true orphans (users==0) runs the
report-first/auto-backup safety model. Clearing fake users / remapping identical
duplicates is intentionally left to the user (or to F3 for materials) since it
reflects intent, not just cleanup.

Modal: classifying + fingerprinting every datablock is the heavy part, chunked
through :func:`_gather_steps` (progress bar + ESC). ``_gather`` keeps a
synchronous path for tests/scripting.
"""

import bpy

from ..core.f4_orphans import build_orphan_report
from .progress import ModalProgressMixin

_FP_CHUNK = 64  # datablocks processed between progress yields


def _collections():
    return [
        ("Material", bpy.data.materials),
        ("Mesh", bpy.data.meshes),
        ("Image", bpy.data.images),
        ("NodeGroup", bpy.data.node_groups),
        ("Texture", bpy.data.textures),
        ("Object", bpy.data.objects),
        ("Armature", bpy.data.armatures),
        ("Curve", bpy.data.curves),
    ]


def _gather_steps(context):
    """Collect datablock info dicts across the common asset collections, yielding
    ``(fraction, status)`` every ``_FP_CHUNK``. Returns the ``items`` list.

    Materials/meshes/images get a content fingerprint (for identity grouping);
    other types are still classified as orphan/fake-only but not clustered.
    """
    from .extract import extract_image, extract_material, extract_mesh
    from ..core.fingerprint import (
        fingerprint_image,
        fingerprint_material,
        fingerprint_mesh,
    )

    fp_for = {
        "Material": lambda d: fingerprint_material(extract_material(d)),
        "Mesh": lambda d: fingerprint_mesh(extract_mesh(d)),
        "Image": lambda d: fingerprint_image(extract_image(d)),
    }
    collections = _collections()
    total = sum(len(coll) for _, coll in collections) or 1

    items = []
    done = 0
    for type_name, coll in collections:
        maker = fp_for.get(type_name)
        for db in coll:
            linked = db.library is not None
            fingerprint = None
            if maker is not None and not linked:
                try:
                    fingerprint = maker(db)
                except Exception:
                    fingerprint = None  # never let extraction break the scan
            items.append({
                "type": type_name,
                "name": db.name,
                "users": db.users,
                "fake": db.use_fake_user,
                "linked": linked,
                "fingerprint": fingerprint,
            })
            done += 1
            if done % _FP_CHUNK == 0:
                yield (0.85 * done / total, f"Scanning datablocks {done}/{total}…")
    return items


def _gather(context):
    """Synchronous gather (drains :func:`_gather_steps`). Kept for tests/scripting."""
    gen = _gather_steps(context)
    try:
        while True:
            next(gen)
    except StopIteration as done:
        return done.value


class ASSETDOCTOR_OT_scan_orphans(ModalProgressMixin, bpy.types.Operator):
    bl_idname = "assetdoctor.scan_orphans"
    bl_label = "Scan Orphans & Fake Users"
    bl_description = "List orphaned and fake-user-only datablocks and group identical ones"
    bl_options = {"REGISTER"}

    purge_orphans: bpy.props.BoolProperty(
        name="Purge Orphans",
        description="After reporting, delete true orphans (users==0). Takes a backup first",
        default=False,
    )  # type: ignore[valid-type]

    @classmethod
    def description(cls, context, properties):
        if properties.purge_orphans:
            return ("Report orphaned / fake-user-only / identical datablocks, then delete true "
                    "orphans (users==0). Takes a backup first")
        return ("List orphaned datablocks, fake-user-only data, and groups of identical "
                "datablocks (no changes)")

    def cancel_message(self):
        return "Orphan scan cancelled" + (" (backup preserved)" if self.purge_orphans else "")

    def run_steps(self, context):
        from ..log import get_logger
        from .report_store import stash_report

        log = get_logger()
        items = yield from _gather_steps(context)

        yield (0.9, "Building report…")
        report = build_orphan_report(items)
        stash_report(context, report, "f4")
        for f in report.findings:
            log.info("F4 [%s] %s: %s", f.severity, f.category, f.message)
        summary = next((f for f in report.findings if f.category == "summary"), None)
        msg = summary.message if summary else "scan complete"

        if not self.purge_orphans:
            level = "WARNING" if report.count("warning") else "INFO"
            self.report({level}, msg)
            return

        from .safety import auto_backup

        yield (0.95, "Backing up & purging…")
        backup = auto_backup(context)
        purged = bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False,
                                        do_recursive=True)
        tail = f"Purged {purged} orphan(s)."
        tail += f" Backup: {backup}" if backup else " (no backup written)"
        self.report({"INFO"}, f"{msg}. {tail}")
