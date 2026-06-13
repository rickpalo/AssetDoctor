# Releasing & auto-updates

## For users — add the auto-updating repository in Blender

1. Edit → Preferences → **Get Extensions** → the dropdown (top-right) → **Repositories** →
   **＋ Add Remote Repository**.
2. URL: `https://rickpalo.github.io/AssetDoctor/index.json`
3. Tick **Check for Updates on Startup** (and **Enabled**).
4. Back in **Get Extensions**, search "AssetDoctor" and **Install** it *from the repository*
   (if you previously installed the zip from disk, install the repo copy — same `id`, so
   it takes over; remove the disk one if both show).

Blender then offers updates automatically whenever a newer version is published here.
Installing from a local `.zip` (Install from Disk) never auto-updates — that's expected.

## For the maintainer — cutting a release

Repo: https://github.com/rickpalo/AssetDoctor  ·  Pages repo served from branch `gh-pages`.

1. **Bump** `version` in `blender_manifest.toml` (3rd digit per step; see CHANGELOG).
2. **Build** the zip:
   ```
   blender --command extension build --source-dir . --output-dir dist
   ```
3. **Commit, tag, push:**
   ```
   git add -A && git commit -m "…"
   git tag -a vX.Y.Z -m "AssetDoctor vX.Y.Z — …"
   git push origin main vX.Y.Z
   ```
4. **GitHub Release** (with the zip asset):
   ```
   gh release create vX.Y.Z dist/assetdoctor-X.Y.Z.zip --title "AssetDoctor vX.Y.Z" --notes "…"
   ```
5. **Refresh the Pages repo index** (this is what drives auto-update). Keep older version
   zips alongside the new one so the index offers version history:
   ```
   # stage zips + regenerate the index
   Copy-Item dist\*.zip .pages\
   blender --command extension server-generate --repo-dir .pages

   # publish to gh-pages via a throwaway worktree
   git worktree add -b _ghpages_tmp ..\ad_ghpages origin/gh-pages
   Copy-Item .pages\* ..\ad_ghpages\ -Force      # zips + index.json
   git -C ..\ad_ghpages add -A
   git -C ..\ad_ghpages commit -m "gh-pages: index vX.Y.Z"
   git -C ..\ad_ghpages push origin HEAD:gh-pages
   git worktree remove ..\ad_ghpages --force
   git branch -D _ghpages_tmp
   ```
6. **Verify:** `https://rickpalo.github.io/AssetDoctor/index.json` shows the new `version`
   and its zip returns HTTP 200.

Notes:
- `.pages/` is the local staging dir (git-ignored on `main`); the real content lives on the
  `gh-pages` branch.
- The `index.json` uses relative `archive_url`s, so `index.json` and the zips must sit in the
  same directory (they do, at the Pages root).
