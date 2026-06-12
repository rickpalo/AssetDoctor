"""Probe which BAT wheels are actually needed for dependency tracing.

Run under Blender's Python with ONLY the BAT wheel on sys.path (no requests):

    blender --background --factory-startup --python tests/probe_bat_imports.py

Wheels are zip files, so we can import straight from the .whl path. If the
trace/blendfile modules import without `requests`, we only need to bundle BAT
itself (its requests dep is for upload/pack features we don't use).
"""

import glob
import os
import sys

WHEELS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wheels")
bat = glob.glob(os.path.join(WHEELS, "blender_asset_tracer-*.whl"))
assert bat, f"no BAT wheel in {WHEELS}"
sys.path.insert(0, bat[0])

# Block requests so we learn whether dependency tracing truly needs it.
import importlib.abc
import importlib.machinery


class _Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name == "requests" or name.startswith("requests."):
            raise ImportError("requests blocked by probe")
        return None


sys.meta_path.insert(0, _Blocker())
sys.modules.pop("requests", None)

for mod in ("blender_asset_tracer.blendfile", "blender_asset_tracer.trace"):
    try:
        __import__(mod)
        print(f"IMPORT_OK {mod}")
    except Exception as exc:
        print(f"IMPORT_FAIL {mod}: {type(exc).__name__}: {exc}")

# Is requests reachable in this stripped environment? (Expect NO.)
try:
    import requests  # noqa: F401

    print("REQUESTS_PRESENT")
except Exception:
    print("REQUESTS_ABSENT")
