from __future__ import annotations

from typing import Any, TypedDict


class PluginUpdateOutcome(TypedDict, total=False):
    name: str
    success: bool
    old_version: str
    new_version: str
    error: str


def build_update_outcome(name: str, success: bool, **kwargs: Any) -> PluginUpdateOutcome:
    return {"name": name, "success": success, **kwargs}
