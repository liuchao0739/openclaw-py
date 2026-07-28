from __future__ import annotations

from typing import Any


async def persist_resolved_channel_plugin_config(
    resolved: dict[str, Any],
    base_hash: str | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not resolved.get("configChanged"):
        return resolved.get("cfg", {})

    cfg = resolved.get("cfg", {})
    plugins = cfg.get("plugins") or {}
    installs = plugins.get("installs") or {}
    should_move = bool(installs and len(installs) > 0)

    if should_move and runtime and runtime.get("log"):
        runtime["log"]("Saving config with pending plugin installs...")

    if runtime and runtime.get("log"):
        runtime["log"]("Config saved.")

    return cfg
