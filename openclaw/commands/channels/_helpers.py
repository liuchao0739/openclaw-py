from __future__ import annotations

import json
import os
import time
from typing import Any, Callable


ChannelsAddOptions = dict[str, Any]
ChannelsListOptions = dict[str, Any]
ChannelsStatusOptions = dict[str, Any]
ChannelsRemoveOptions = dict[str, Any]
ChannelsResolveOptions = dict[str, Any]
ChannelsLogsOptions = dict[str, Any]
ChannelsCapabilitiesOptions = dict[str, Any]


def _normalize_optional_lowercase_string(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str) and len(value) > 0:
        return value
    return None


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _parse_strict_non_negative_integer(value: Any) -> int | None:
    if value is None:
        return None
    try:
        n = int(value)
        if n >= 0:
            return n
    except (ValueError, TypeError):
        pass
    return None


def _parse_strict_positive_integer(value: Any) -> int | None:
    if value is None:
        return None
    try:
        n = int(value)
        if n > 0:
            return n
    except (ValueError, TypeError):
        pass
    return None


def _parse_optional_delimited_entries(value: Any) -> list[str] | None:
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, str)]
    if isinstance(value, str):
        return [e.strip() for e in value.split(",") if e.strip()]
    return None


def _normalize_account_id(value: Any) -> str:
    if value is None:
        return "default"
    s = str(value).strip()
    return s if s else "default"


def _normalize_channel_id(raw: str) -> str | None:
    if not raw:
        return None
    return raw.strip().lower()


def _channel_label(channel: str) -> str:
    return channel.replace("-", " ").title()


def _format_cli_command(cmd: str) -> str:
    return f"`{cmd}`"


def _format_unknown_channel_message(channel: str) -> str:
    return f"Unknown channel: {channel}. Run {_format_cli_command('openclaw channels list --all')} to see available channels."


def _format_unsupported_channel_action_message(channel: str, action: str) -> str:
    return f"Channel '{channel}' does not support {action}."


def _format_docs_link(path: str, label: str) -> str:
    return f"https://docs.openclaw.ai{path}"
