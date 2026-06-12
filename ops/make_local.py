"""F2 - recursively make all linked assets in the current file fully local.

Default mode writes a separate fully-local .blend and leaves the working file's
linked setup untouched (copy + revert). In-place mode flattens the current file
(auto-backup preserves the original first). Both resolve library overrides
(make_local(clear_liboverride=True)) and iterate until no linked IDs remain,
then purge the emptied libraries.
"""

import os

import bpy

from ..core.f2_makelocal import build_makelocal_report


def _id_collections():
    """All bpy.data ID collections (generic, version-proof)."""
    for prop in bpy.data.bl_rna.properties:
        if prop.type != "COLLECTION":
            continue
        coll = getattr(bpy.data, prop.identifier, None)
        if coll is None or len(coll) == 0:
            continue
        first = next(iter(coll), None)
        if first is not None and hasattr(first, "library"):
            yield coll


def _gather_linked():
    items = []
    for coll in _id_collections():
        for db in coll:
            if db.library is None:
                continue
            items.append({
                "type": type(db).__name__,
                "name": db.name,
                "library": db.library.filepath,
                "indirect": db.library.parent is not None,
            })
    return items


def _localize_all(max_passes: int = 12) -> int:
    """Make every linked / overridden datablock local. Returns passes used."""
    for n in range(1, max_passes + 1):
        remaining = [
            db
            for coll in _id_collections()
            for db in coll
            if db.library is not None or db.override_library is not None
        ]
        if not remaining:
            return n - 1
        for db in remaining:
            try:
                db.make_local(clear_liboverride=True)
            except (RuntimeError, ReferenceError):
                pass
    return max_passes


def _purge_libraries():
    # Purge orphaned datablocks until stable (make_local can leave copies behind).
    while bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True):
        pass
    # Remove now-unused libraries. Library.users can report a phantom count after
    # make_local, so user_map() is the authority on what truly references a library.
    user_map = bpy.data.user_map()
    for lib in list(bpy.data.libraries):
        if not any(lib in used for used in user_map.values()):
            try:
                bpy.data.libraries.remove(lib)
            except RuntimeError:
                pass
    while bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True):
        pass


class ASSETDOCTOR_OT_make_local(bpy.types.Operator):
    bl_idname = "assetdoctor.make_local"
    bl_label = "Make All Local"
    bl_description = "Recursively make every linked asset local (report first, then apply)"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ("NEW_FILE", "New File", "Write a separate fully-local copy; leave this file untouched"),
            ("IN_PLACE", "In Place", "Flatten this file to local (a backup is taken first)"),
        ],
        default="NEW_FILE",
    )  # type: ignore[valid-type]

    filepath: bpy.props.StringProperty(
        name="Output",
        description="Destination for the local copy (New File mode). Defaults to "
        "<name>_local.blend next to the current file",
        subtype="FILE_PATH",
        default="",
    )  # type: ignore[valid-type]

    apply: bpy.props.BoolProperty(
        name="Apply",
        description="Perform the make-local. Leave off for a report-only dry run",
        default=False,
    )  # type: ignore[valid-type]

    @classmethod
    def description(cls, context, properties):
        if not properties.apply:
            return "List everything linked into this file, grouped by library (no changes)"
        if properties.mode == "NEW_FILE":
            return ("Write a fully-local copy beside this file (<name>_local.blend) and leave "
                    "this file's links untouched. Save the file first")
        return ("Make every linked asset in THIS file local. Takes a timestamped backup "
                "first; supports Undo")

    def execute(self, context):
        from ..log import get_logger

        log = get_logger()
        items = _gather_linked()
        report = build_makelocal_report(items)
        from .report_store import stash_report
        stash_report(context, report, "f2")
        for f in report.findings:
            log.info("F2 [%s] %s: %s", f.severity, f.category, f.message)
        summary = next((f for f in report.findings if f.category == "summary"), None)
        msg = summary.message if summary else "scan complete"

        if not self.apply:
            self.report({"INFO"}, msg + " (dry run)")
            return {"FINISHED"}
        if not items:
            self.report({"INFO"}, "Nothing linked — already fully local")
            return {"FINISHED"}

        src = bpy.data.filepath
        if self.mode == "NEW_FILE":
            if not src:
                self.report({"ERROR"}, "Save the file first (New File mode reverts the session)")
                return {"CANCELLED"}
            out = bpy.path.abspath(self.filepath) if self.filepath else \
                os.path.splitext(src)[0] + "_local.blend"
            passes = _localize_all()
            _purge_libraries()
            log.debug("F2 NEW_FILE: %d localize pass(es), out=%s", passes, out)
            bpy.ops.wm.save_as_mainfile(filepath=out, copy=True)
            bpy.ops.wm.revert_mainfile()  # restore the original linked session
            self.report(
                {"INFO"},
                f"Wrote fully-local copy: {out} ({len(items)} datablock(s) localized). "
                "This file left unchanged.",
            )
        else:  # IN_PLACE
            from .safety import auto_backup

            backup = auto_backup(context)
            _localize_all()
            _purge_libraries()
            tail = f"Backup: {backup}" if backup else "(no backup written — save the file to enable backups)"
            self.report(
                {"WARNING"},
                f"Localized {len(items)} datablock(s); {len(bpy.data.libraries)} librar(ies) "
                f"remain. {tail}",
            )
        return {"FINISHED"}
