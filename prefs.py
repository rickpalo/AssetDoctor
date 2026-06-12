"""Addon preferences for AssetDoctor.

Holds user-tunable settings that the operators read: scan root, backup
directory, the resolution-token regex used for near-duplicate material
matching, and feature toggles. Defaults are chosen to be safe (report-first,
backups on).
"""

import bpy


class AssetDoctorPreferences(bpy.types.AddonPreferences):
    # Must match the extension id / package name.
    bl_idname = __package__

    backup_dir: bpy.props.StringProperty(
        name="Backup Folder",
        description="Where to write timestamped .blend backups before any mutating op. "
        "Leave empty to back up next to the current file",
        subtype="DIR_PATH",
        default="",
    )  # type: ignore[valid-type]

    auto_backup: bpy.props.BoolProperty(
        name="Auto-backup before mutating",
        description="Save a timestamped .blend copy before make-local / remap / purge",
        default=True,
    )  # type: ignore[valid-type]

    # Tokens stripped from image/material names when deciding multi-res near-duplicates.
    # Pipe-separated regex fragments; see core.fingerprint.strip_resolution_tokens.
    resolution_token_regex: bpy.props.StringProperty(
        name="Resolution Tokens",
        description="Regex of resolution/dup suffixes to ignore when matching textures "
        r"(e.g. _1k, _2k, -2048, Blender's .001 dup suffix)",
        default=r"[._-]?\d{1,2}k|[._-]\d{3,4}|\.\d{3}$",
    )  # type: ignore[valid-type]

    material_whitelist: bpy.props.StringProperty(
        name="Material Whitelist",
        description="Names/globs to always KEEP as the canonical material when duplicates "
        "are found (comma/newline separated; * wildcards allowed)",
        default="",
    )  # type: ignore[valid-type]

    material_blacklist: bpy.props.StringProperty(
        name="Material Blacklist",
        description="Names/globs to always REPLACE when an identical duplicate exists",
        default="",
    )  # type: ignore[valid-type]

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "auto_backup")
        col.prop(self, "backup_dir")
        col.separator()
        col.prop(self, "resolution_token_regex")
        col.label(text="Material dedup (F3):")
        col.prop(self, "material_whitelist")
        col.prop(self, "material_blacklist")


def get_prefs(context=None):
    """Return the AssetDoctorPreferences instance, or None if unavailable."""
    context = context or bpy.context
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None
