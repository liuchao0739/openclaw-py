"""Legacy hook config helpers convert older hook records into current config shape.

Mirrors src/hooks/legacy-config.ts.
"""

from __future__ import annotations

from typing import Any, Mapping, TypedDict


class LegacyInternalHookHandler(TypedDict, total=False):
    event: str
    module: str
    export: str


def get_legacy_internal_hook_handlers(
    config: Any,
) -> list[dict[str, Any]]:
    """Read legacy hooks.internal.handlers entries for backward-compatible config detection."""
    if not isinstance(config, Mapping):
        return []
    hooks = config.get("hooks")
    if not isinstance(hooks, Mapping):
        return []
    internal = hooks.get("internal")
    if not isinstance(internal, Mapping):
        return []
    handlers = internal.get("handlers")
    return list(handlers) if isinstance(handlers, list) else []
