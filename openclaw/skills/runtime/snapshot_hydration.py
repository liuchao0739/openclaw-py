"""Snapshot hydration helpers merge saved runtime skill snapshots into live state.

Mirrors src/skills/runtime/snapshot-hydration.ts.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping


def hydrate_resolved_skills(
    snapshot: Mapping[str, Any],
    rebuild: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    """Hydrate resolved skills from a rebuild if not already present.

    ``resolvedSkills`` is runtime-only: session persistence keeps the lightweight
    catalog/prompt, while consumers that need concrete SKILL.md paths hydrate it
    from a fresh workspace scan.
    """
    if snapshot.get("resolvedSkills") is not None:
        return dict(snapshot)
    rebuilt = rebuild()
    return {**snapshot, "resolvedSkills": rebuilt.get("resolvedSkills")}
