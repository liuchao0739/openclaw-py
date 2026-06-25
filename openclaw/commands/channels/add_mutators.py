"""Small channel config mutators used by guided and non-interactive channel add flows."""

from __future__ import annotations

from typing import Any


def _normalize_account_id(account_id: str) -> str:
    return (account_id or "default").strip() or "default"


def _get_channel_plugin(channel: str) -> Any | None:
    try:
        from openclaw.channels.plugins.registry import get_channel_plugin

        return get_channel_plugin(channel)
    except Exception:
        return None


def _get_setup(plugin: Any) -> Any | None:
    if plugin is None:
        return None
    if isinstance(plugin, dict):
        return plugin.get("setup")
    return getattr(plugin, "setup", None)


def apply_account_name(
    cfg: dict[str, Any],
    channel: str,
    account_id: str,
    name: str | None = None,
    plugin: Any | None = None,
) -> dict[str, Any]:
    """Apply a display name to a channel account when the plugin supports account naming."""
    normalized_id = _normalize_account_id(account_id)
    resolved_plugin = plugin or _get_channel_plugin(channel)
    setup = _get_setup(resolved_plugin)

    if setup:
        apply_fn = setup.get("applyAccountName") if isinstance(setup, dict) else getattr(setup, "applyAccountName", None)
        if callable(apply_fn):
            return apply_fn({"cfg": cfg, "accountId": normalized_id, "name": name})

    return cfg


def apply_channel_account_config(
    cfg: dict[str, Any],
    channel: str,
    account_id: str,
    input_data: dict[str, Any],
    plugin: Any | None = None,
) -> dict[str, Any]:
    """Delegate account config mutation to the channel plugin setup contract."""
    normalized_id = _normalize_account_id(account_id)
    resolved_plugin = plugin or _get_channel_plugin(channel)
    setup = _get_setup(resolved_plugin)

    if setup:
        apply_fn = setup.get("applyAccountConfig") if isinstance(setup, dict) else getattr(setup, "applyAccountConfig", None)
        if callable(apply_fn):
            return apply_fn({"cfg": cfg, "accountId": normalized_id, "input": input_data})

    return cfg
