"""Subsystem logger helpers create scoped loggers with subsystem-specific filters.

Mirrors src/logging/subsystem.ts.
"""

from __future__ import annotations

import json
import os
from typing import Any

from openclaw.logging.console import (
    format_console_timestamp,
    get_console_settings,
    should_log_subsystem_to_console,
)
from openclaw.logging.levels import LogLevel, level_to_min_level
from openclaw.logging.redact import redact_sensitive_text
from openclaw.logging.state import logging_state


_SUBSYSTEM_PREFIXES_TO_DROP = ("gateway", "channels", "providers")
_SUBSYSTEM_MAX_SEGMENTS = 2

_CHANNEL_SUBSYSTEM_PREFIXES = {
    "clickclack", "discord", "feishu", "googlechat", "imessage", "irc",
    "line", "matrix", "mattermost", "msteams", "nextcloud-talk", "nostr",
    "openclaw-weixin", "qqbot", "signal", "slack", "synology-chat",
    "telegram", "tlon", "twitch", "webchat", "wecom", "whatsapp",
    "yuanbao", "zalo", "zalouser",
}


def _normalize_subsystem_label(subsystem: str | None = None) -> str:
    if not isinstance(subsystem, str):
        return "unknown"
    normalized = subsystem.strip()
    return normalized if normalized else "unknown"


def _should_log_to_console(level: LogLevel, settings: dict[str, Any]) -> bool:
    if level == "silent" or settings.get("level") == "silent":
        return False
    return level_to_min_level(level) >= level_to_min_level(settings["level"])


def _format_subsystem_for_console(subsystem: str) -> str:
    parts = [p for p in subsystem.split("/") if p]
    original = "/".join(parts) or subsystem
    while parts and parts[0] in _SUBSYSTEM_PREFIXES_TO_DROP:
        parts.pop(0)
    if not parts:
        return original
    if parts[0].lower() in _CHANNEL_SUBSYSTEM_PREFIXES:
        return parts[0]
    if len(parts) > _SUBSYSTEM_MAX_SEGMENTS:
        return "/".join(parts[-_SUBSYSTEM_MAX_SEGMENTS:])
    return "/".join(parts)


def strip_redundant_subsystem_prefix_for_console(
    message: str, display_subsystem: str
) -> str:
    if not display_subsystem:
        return message
    if message.startswith("["):
        close_idx = message.find("]")
        if close_idx > 1:
            bracket_tag = message[1:close_idx]
            if bracket_tag.lower() == display_subsystem.lower():
                i = close_idx + 1
                while i < len(message) and message[i] == " ":
                    i += 1
                return message[i:]
    prefix = message[: len(display_subsystem)]
    if prefix.lower() != display_subsystem.lower():
        return message
    next_char = message[len(display_subsystem) : len(display_subsystem) + 1]
    if next_char not in (":", " "):
        return message
    i = len(display_subsystem)
    while i < len(message) and message[i] == " ":
        i += 1
    if i < len(message) and message[i] == ":":
        i += 1
    while i < len(message) and message[i] == " ":
        i += 1
    return message[i:]


def create_subsystem_logger(subsystem: str) -> dict[str, Any]:
    resolved_subsystem = _normalize_subsystem_label(subsystem)

    def emit_log(level: LogLevel, message: str, meta: dict[str, Any] | None = None) -> None:
        console_settings = get_console_settings()
        console_enabled = _should_log_to_console(level, console_settings) and should_log_subsystem_to_console(resolved_subsystem)
        if not console_enabled:
            return
        display_subsystem = resolved_subsystem if console_settings.get("style") == "json" else _format_subsystem_for_console(resolved_subsystem)
        if console_settings.get("style") == "json":
            line = redact_sensitive_text(json.dumps({
                "time": format_console_timestamp("json"),
                "level": level,
                "subsystem": display_subsystem,
                "message": message,
                **(meta or {}),
            }))
        else:
            redacted = redact_sensitive_text(message)
            display_message = strip_redundant_subsystem_prefix_for_console(redacted, display_subsystem)
            time_str = ""
            if logging_state.console_timestamp_prefix:
                time_str = format_console_timestamp(console_settings.get("style"))
            prefix = f"[{display_subsystem}]"
            parts = [p for p in [time_str, prefix] if p]
            line = f"{' '.join(parts)} {display_message}"
        if logging_state.force_console_to_stderr or level in ("error", "fatal"):
            import sys
            sys.stderr.write(line + "\n")
        elif level == "warn":
            import sys
            sys.stderr.write(line + "\n")
        else:
            import sys
            sys.stdout.write(line + "\n")

    def is_enabled(level: LogLevel, target: str = "any") -> bool:
        console_enabled = _should_log_to_console(level, get_console_settings()) and should_log_subsystem_to_console(resolved_subsystem)
        if target == "console":
            return console_enabled
        if target == "file":
            return False
        return console_enabled

    def child(name: str) -> dict[str, Any]:
        return create_subsystem_logger(f"{resolved_subsystem}/{name}")

    return {
        "subsystem": resolved_subsystem,
        "isEnabled": is_enabled,
        "trace": lambda msg, meta=None: emit_log("trace", msg, meta),
        "debug": lambda msg, meta=None: emit_log("debug", msg, meta),
        "info": lambda msg, meta=None: emit_log("info", msg, meta),
        "warn": lambda msg, meta=None: emit_log("warn", msg, meta),
        "error": lambda msg, meta=None: emit_log("error", msg, meta),
        "fatal": lambda msg, meta=None: emit_log("fatal", msg, meta),
        "raw": lambda msg: emit_log("info", msg),
        "child": child,
    }


__all__ = ["create_subsystem_logger", "strip_redundant_subsystem_prefix_for_console"]
