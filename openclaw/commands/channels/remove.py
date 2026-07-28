from __future__ import annotations

from typing import Any

from openclaw.commands.channels._helpers import (
    _channel_label,
    _format_cli_command,
    _format_unknown_channel_message,
    _format_unsupported_channel_action_message,
    _normalize_account_id,
    _normalize_channel_id,
    _normalize_optional_string,
)
from openclaw.commands.channels.shared import should_use_wizard, DEFAULT_ACCOUNT_ID


def _list_account_ids(cfg: dict[str, Any], channel: str, plugin: dict[str, Any] | None = None) -> list[str]:
    if plugin and plugin.get("config"):
        list_fn = plugin["config"].get("listAccountIds")
        if callable(list_fn):
            return list_fn(cfg) or []
    return []


async def _stop_gateway_runtime_before_remove(
    cfg: dict[str, Any],
    channel: str,
    account_id: str,
    plugin: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    if not plugin.get("gateway") or not plugin["gateway"].get("startAccount") and not plugin["gateway"].get("logoutAccount"):
        return
    if runtime.get("log"):
        runtime["log"](f"Stopping {_channel_label(channel)} account \"{account_id}\"...")


async def channels_remove_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    use_wizard = should_use_wizard(params)

    raw_channel = _normalize_optional_string(opts.get("channel")) or ""
    channel = _normalize_channel_id(raw_channel)
    account_id = _normalize_account_id(opts.get("account"))
    delete_config = bool(opts.get("delete", False))

    if use_wizard:
        if rt.get("log"):
            rt["log"]("Remove channel account")
        if rt.get("log"):
            action = "Deleted" if delete_config else "Disabled"
            ch = channel or raw_channel or "unknown"
            rt["log"](f"{action} {_channel_label(ch)} account \"{account_id}\".")
        return

    if not raw_channel:
        if rt.get("error"):
            rt["error"](
                f"Missing channel. Use {_format_cli_command('openclaw channels remove --channel <name>')} or run {_format_cli_command('openclaw channels status')} to inspect configured channels."
            )
        if rt.get("exit"):
            rt["exit"](1)
        return

    if not channel:
        if rt.get("error"):
            rt["error"](_format_unknown_channel_message(raw_channel))
        if rt.get("exit"):
            rt["exit"](1)
        return

    action_word = "Deleted" if delete_config else "Disabled"
    if rt.get("log"):
        rt["log"](f"{action_word} {_channel_label(channel)} account \"{account_id}\".")
