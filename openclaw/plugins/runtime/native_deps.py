"""Inputs used to format native dependency install/rebuild guidance.

Mirrors src/plugins/runtime/native-deps.ts.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class NativeDependencyHintParams(TypedDict, total=False):
    packageName: str
    manager: str  # "pnpm" | "npm" | "yarn"
    rebuildCommand: str
    approveBuildsCommand: str
    downloadCommand: str


def format_native_dependency_hint(params: dict[str, str]) -> str:
    """Format concise guidance for installing and rebuilding a native dependency."""
    package_name = params.get("packageName", "")
    manager = params.get("manager", "pnpm")
    rebuild_command = params.get("rebuildCommand")
    if not rebuild_command:
        if manager == "npm":
            rebuild_command = f"npm rebuild {package_name}"
        elif manager == "yarn":
            rebuild_command = f"yarn rebuild {package_name}"
        else:
            rebuild_command = f"pnpm rebuild {package_name}"

    approve_builds_command = params.get("approveBuildsCommand")
    if not approve_builds_command and manager == "pnpm":
        approve_builds_command = f"pnpm approve-builds (select {package_name})"

    download_command = params.get("downloadCommand")

    steps = [s for s in [approve_builds_command, rebuild_command, download_command] if s]
    if not steps:
        return f"Install {package_name} and rebuild its native module."
    return f"Install {package_name} and rebuild its native module ({'; '.join(steps)})."
