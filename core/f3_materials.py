"""F3 analysis: cluster duplicate / multi-res materials and decide a canonical
survivor per white/black list. bpy-free; ops supplies material info dicts and
executes the resulting plan with ``user_remap`` + purge.

material info dict contract (from ops):
    { "id": "Wood [libA]",   # unique, human-readable key (name + library)
      "name": "Wood",        # the bare datablock name, matched against the lists
      "fingerprint": str | None,
      "linked": bool,
      "max_res": int }       # largest texture dimension, for the tie-break

Canonical selection order:
    1. a whitelisted member (always keep)        -> never a blacklisted one
    2. else any non-blacklisted member
    3. else (all blacklisted) keep the best available, with a note
    Within the chosen pool: prefer local over linked, then highest max_res,
    then name (stable).
"""

from __future__ import annotations

import fnmatch

from .cluster import group_identical
from .report import Finding, Report


def parse_name_list(text: str) -> list[str]:
    """Split a comma/semicolon/newline separated list of names/globs."""
    if not text:
        return []
    norm = text.replace(";", ",").replace("\n", ",")
    return [c.strip() for c in norm.split(",") if c.strip()]


def _matches(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def _rank_key(m: dict):
    # local before linked (False<True), higher res first, then stable by name.
    return (m["linked"], -m.get("max_res", 0), m["name"])


def choose_canonical(members: list[dict], whitelist: list[str], blacklist: list[str]):
    """Pick the canonical member of a duplicate cluster. Returns (member, reason)."""
    whitelisted = [m for m in members if _matches(m["name"], whitelist)]
    non_black = [m for m in members if not _matches(m["name"], blacklist)]

    if whitelisted:
        pool, reason = whitelisted, "whitelisted"
    elif non_black:
        pool, reason = non_black, None
    else:
        pool, reason = members, "all blacklisted — kept best available"

    best = sorted(pool, key=_rank_key)[0]
    if reason is None:
        reason = (
            f"highest resolution ({best['max_res']})" if best.get("max_res") else "first by name"
        )
    return best, reason


def build_dedup_plan(items: list[dict], whitelist=(), blacklist=()):
    """Return (Report, plan). plan is a list of
    {fingerprint, canonical: id, victims: [id], linked_victims: [id]}."""
    report = Report(title="Material duplicates", feature="F3")
    by_id = {it["id"]: it for it in items}
    clusters = group_identical(
        sorted((it["id"], it["fingerprint"]) for it in items if it["fingerprint"])
    )

    plan = []
    total_victims = 0
    for fp, ids in sorted(clusters.items(), key=lambda kv: sorted(kv[1])[0]):
        members = [by_id[i] for i in sorted(ids)]
        canonical, reason = choose_canonical(members, list(whitelist), list(blacklist))
        victims = [m for m in members if m["id"] != canonical["id"]]
        linked_victims = [v["id"] for v in victims if v["linked"]]
        total_victims += len(victims)
        plan.append({
            "fingerprint": fp,
            "canonical": canonical["id"],
            "victims": [v["id"] for v in victims],
            "linked_victims": linked_victims,
        })
        report.add(Finding(
            category="duplicate_group",
            message=(
                f"{len(members)} identical materials → keep '{canonical['id']}' "
                f"({reason}); remap {len(victims)}"
            ),
            severity="warning",
            items=[canonical["id"]] + [v["id"] for v in victims],
            data={
                "canonical": canonical["id"],
                "victims": [v["id"] for v in victims],
                "reason": reason,
                "linked_victims": linked_victims,
            },
        ))
        if linked_victims:
            report.add(Finding(
                category="linked_victim",
                message=(
                    f"{len(linked_victims)} duplicate(s) are linked: local users will be "
                    "remapped, but the linked datablock stays in its library — "
                    + ", ".join(linked_victims)
                ),
                severity="info",
                items=linked_victims,
            ))

    report.add(Finding(
        category="summary",
        message=f"{len(clusters)} duplicate group(s); {total_victims} material(s) can be remapped",
        severity="info",
        data={"groups": len(clusters), "victims": total_victims},
    ))
    return report, plan
