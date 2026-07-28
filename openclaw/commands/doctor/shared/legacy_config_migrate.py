from __future__ import annotations

from typing import Any


async def _migrate_legacy_config(
    legacy_config: dict[str, Any],
    target_version: str,
) -> dict[str, Any]:
    result = dict(legacy_config)
    result["version"] = target_version
    return result


async def migrate_legacy_config(
    legacy_config: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    version = legacy_config.get("version", "0")
    if version == "0":
        return await _migrate_legacy_config(legacy_config, "1")
    return legacy_config
