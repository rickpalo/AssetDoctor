# AssetDoctor

A Blender **5+** extension to **map, diagnose, and clean** linked/appended assets,
materials, and orphaned data across a multi-file project.

## Features

| # | What it does | Mode |
|---|--------------|------|
| **F1** | Recursively map which `.blend` files link which across a folder, and take a **census of objects duplicated across files** (matched by characteristics, not append-origin) | Offline, read-only |
| **F2** | Recursively make every linked asset in the current file **fully local** | In-session, mutating |
| **F3** | Find **duplicate / multi-resolution near-duplicate materials** and remap them to a single source (white/black list driven) | In-session, mutating |
| **F4** | Find **orphans** and **fake-user-only** data, and group **identical** ones | In-session, read-only + optional purge |

Every mutating operation is **report-first → explicit Apply**, with a timestamped
`.blend` auto-backup taken before any change.

## Architecture (short version)

- `core/` — pure-Python, **bpy-free**, unit-tested (graph, fingerprint, report, blendscan).
- `ops/` — thin `bpy` operators; gather data → call `core` → report → apply.
- `ui/` — the N-panel.
- Offline `.blend` parsing (F1) uses **Blender Asset Tracer (BAT)**, bundled as a wheel.

Full design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Development

```pwsh
# bpy-free core tests run with plain pytest (no Blender needed)
pip install pytest
pytest
```

Status: **M0 scaffold complete.** See [CHANGELOG.md](CHANGELOG.md) and the milestone
roadmap in the architecture doc.

## Install (once built)

Blender → Edit → Preferences → Get Extensions → Install from Disk → pick the built `.zip`.
Targets Blender 5.0+.
