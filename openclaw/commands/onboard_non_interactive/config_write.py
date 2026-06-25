"""Config write commit helper for non-interactive onboarding.

Preserves pending plugin install records before replacing the user config.
"""

from __future__ import annotations

from typing import Any


def _has_pending_plugin_install_records(config: dict[str, Any]) -> bool:
    """Check if config has pending plugin install records."""
    try:
        from openclaw.cli.plugins_install_record_commit import (
            has_pending_plugin_install_records,
        )

        return has_pending_plugin_install_records(config)
    except Exception:
        return False


async def _replace_config_file(
    next_config: dict[str, Any],
    base_hash: str | None = None,
) -> dict[str, Any]:
    """Replace the config file. Deferred to config module."""
    try:
        from openclaw.config.config import replace_config_file

        return await replace_config_file(
            {"nextConfig": next_config, **({"baseHash": base_hash} if base_hash else {})}
        )
    except Exception:
        return {"config": next_config, "hash": None}


async def commit_non_interactive_onboard_config(
    next_config: dict[str, Any],
    base_config: dict[str, Any],
    base_hash: str | None = None,
    reset: bool = False,
) -> dict[str, Any]:
    """Commit a non-interactive onboard config update with pending plugin records handled first."""
    allow_config_size_drop = reset
    write_base_hash = base_hash
    current_next = next_config

    if not allow_config_size_drop and _has_pending_plugin_install_records(base_config):
        # Commit pending records against old config first
        committed = await _replace_config_file(base_config, write_base_hash)
        write_base_hash = committed.get("hash") or write_base_hash

    # Commit the new config
    result = await _replace_config_file(current_next, write_base_hash)
    return result.get("config", current_next)
