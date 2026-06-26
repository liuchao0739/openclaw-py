"""Hook install record helpers read and write installed hook metadata.

Mirrors src/hooks/installs.ts.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping, TypedDict


class HookInstallRecord(TypedDict, total=False):
    installedAt: str
    version: str
    source: str


class HookInstallUpdate(TypedDict, total=False):
    hookId: str
    installedAt: str
    version: str
    source: str


def record_hook_install(
    cfg: dict[str, Any],
    update: Mapping[str, Any],
) -> dict[str, Any]:
    """Return config with one hook install record merged into hooks.internal.installs."""
    result = copy.deepcopy(cfg)
    hook_id = update.get("hookId", "")
    record = {k: v for k, v in update.items() if k != "hookId"}

    hooks = result.setdefault("hooks", {})
    internal = hooks.setdefault("internal", {})
    installs = internal.setdefault("installs", {})

    existing = installs.get(hook_id, {})
    merged = {**existing, **record}
    if "installedAt" not in merged or not merged["installedAt"]:
        merged["installedAt"] = datetime.now(timezone.utc).isoformat()
    installs[hook_id] = merged

    return result
