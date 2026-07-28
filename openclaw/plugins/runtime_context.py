from __future__ import annotations

from typing import Any


def build_plugin_runtime_context(
    plugin_id: str,
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "pluginId": plugin_id,
        "config": config or {},
        "env": env or {},
    }


def resolve_plugin_entrypoint(
    plugin_dir: str,
    manifest: dict[str, Any],
) -> str | None:
    entry = manifest.get("entry")
    if not entry:
        return None
    return entry
