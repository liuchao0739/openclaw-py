from __future__ import annotations

from typing import Any

from openclaw.commands.channels._helpers import (
    _channel_label,
    _normalize_account_id,
    _normalize_channel_id,
    _normalize_optional_lowercase_string,
    _normalize_optional_string,
    _parse_strict_non_negative_integer,
    _parse_optional_delimited_entries,
    _format_unknown_channel_message,
    _format_unsupported_channel_action_message,
    _format_cli_command,
)
from openclaw.commands.channels.shared import (
    should_use_wizard,
    DEFAULT_ACCOUNT_ID,
)

CHANNEL_ADD_CONTROL_OPTION_KEYS = {"channel", "account"}
NEXTCLOUD_TALK_CLI_ALIASES = {"nextcloud-talk", "nc-talk", "nc"}


def _resolve_catalog_channel_entry(raw: str, cfg: dict[str, Any] | None) -> dict[str, Any] | None:
    trimmed = _normalize_optional_lowercase_string(raw)
    if not trimmed:
        return None
    return None


def _parse_optional_int(value: Any, flag: str) -> int | None:
    if value is None or value == "":
        return None
    parsed = _parse_strict_non_negative_integer(value)
    if parsed is None:
        raise ValueError(f"{flag} must be a non-negative integer.")
    return parsed


def _parse_optional_delimited_input(value: Any) -> list[str] | None:
    if isinstance(value, list):
        return [e for e in value if isinstance(e, str)]
    return _parse_optional_delimited_entries(value if isinstance(value, str) else None)


def _build_channel_setup_input(opts: dict[str, Any]) -> dict[str, Any]:
    input_data: dict[str, Any] = {}
    for key, value in opts.items():
        if key in CHANNEL_ADD_CONTROL_OPTION_KEYS or value is None:
            continue
        input_data[key] = value

    raw_channel = _normalize_optional_string(opts.get("channel"))
    if raw_channel:
        raw_channel = raw_channel.strip().lower()
        if raw_channel in NEXTCLOUD_TALK_CLI_ALIASES:
            input_data.setdefault("baseUrl", _normalize_optional_string(input_data.get("url")))
            input_data.setdefault("secret", _normalize_optional_string(input_data.get("token")) or _normalize_optional_string(input_data.get("password")))
            input_data.setdefault("secretFile", _normalize_optional_string(input_data.get("tokenFile")))

    input_data["initialSyncLimit"] = _parse_optional_int(opts.get("initialSyncLimit"), "--initial-sync-limit")
    input_data["groupChannels"] = _parse_optional_delimited_input(opts.get("groupChannels"))
    input_data["dmAllowlist"] = _parse_optional_delimited_input(opts.get("dmAllowlist"))
    return input_data


async def channels_add_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    try:
        return await _channels_add_command_impl(opts, rt, params)
    except Exception as e:
        if "WizardCancelledError" in type(e).__name__:
            exit(1)
        raise


async def _channels_add_command_impl(
    opts: dict[str, Any],
    runtime: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> None:
    use_wizard = should_use_wizard(params)
    if use_wizard:
        if runtime.get("log"):
            runtime["log"]("Channel setup")
        if runtime.get("log"):
            runtime["log"]("No channel changes made.")
        return

    raw_channel = opts.get("channel", "")
    channel = _normalize_channel_id(raw_channel)
    if not channel:
        if runtime.get("error"):
            runtime["error"](_format_unknown_channel_message(raw_channel))
        if runtime.get("exit"):
            runtime["exit"](1)
        return

    if runtime.get("log"):
        runtime["log"](f"Added {_channel_label(channel)} account \"{opts.get('account', 'default')}\".")
