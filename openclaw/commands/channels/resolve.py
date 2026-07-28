from __future__ import annotations

import re
from typing import Any

from openclaw.commands.channels._helpers import (
    _format_cli_command,
    _format_unsupported_channel_action_message,
    _normalize_lowercase_string_or_empty,
    _normalize_optional_lowercase_string,
    _normalize_optional_string,
)
from openclaw.commands.channels.shared import format_channel_account_label


def _resolve_preferred_kind(kind: str | None) -> str | None:
    if not kind or kind == "auto":
        return None
    if kind == "user":
        return "user"
    return "group"


def _detect_auto_kind(input_str: str) -> str:
    trimmed = input_str.strip()
    if not trimmed:
        return "group"
    if trimmed.startswith("@"):
        return "user"
    if re.match(r"^<@!?", trimmed):
        return "user"
    if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", trimmed):
        return "user"
    if re.match(r"^user:", trimmed, re.IGNORECASE):
        return "user"
    return "group"


def _detect_auto_kind_for_plugin(input_str: str, plugin: dict[str, Any] | None) -> str:
    generic = _detect_auto_kind(input_str)
    if generic == "user" or not plugin:
        return generic
    trimmed = input_str.strip()
    lowered = _normalize_lowercase_string_or_empty(trimmed)
    prefixes = [plugin.get("id", "")]
    meta = plugin.get("meta") or {}
    for alias in meta.get("aliases", []) or []:
        normalized = _normalize_optional_lowercase_string(alias)
        if normalized:
            prefixes.append(normalized)
    for prefix in prefixes:
        if not lowered.startswith(f"{prefix}:"):
            continue
        remainder = lowered[len(prefix) + 1:]
        if any(remainder.startswith(p) for p in ["group:", "channel:", "room:", "conversation:", "spaces/", "channels/"]):
            return "group"
        return "user"
    return generic


def _format_resolve_result(result: dict[str, Any]) -> str:
    if not result.get("resolved") or not result.get("id"):
        return f"{result.get('input', '')} -> unresolved"
    name = f" ({result['name']})" if result.get("name") else ""
    note = f" [{result['note']}]" if result.get("note") else ""
    return f"{result['input']} -> {result['id']}{name}{note}"


async def channels_resolve_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    channel = _normalize_optional_string(opts.get("channel"))
    entries = opts.get("entries", [])
    if isinstance(entries, str):
        entries = [e.strip() for e in entries.split(",") if e.strip()]
    elif not isinstance(entries, list):
        entries = []

    if not entries:
        msg = f"At least one entry is required. Example: {_format_cli_command('openclaw channels resolve --channel discord <name-or-id>')}."
        if rt.get("error"):
            rt["error"](msg)
        return

    json_output = opts.get("json", False)
    if json_output:
        if rt.get("writeJson"):
            rt["writeJson"](rt, [])
        return

    for entry in entries:
        if rt.get("log"):
            rt["log"](f"{entry} -> unresolved")
