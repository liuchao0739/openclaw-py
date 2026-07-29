"""Console logging helpers format and write messages to console streams.

Mirrors src/logging/console.ts.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from typing import Any, Literal

from openclaw.logging.config import read_logging_config, should_skip_mutating_logging_config_read
from openclaw.logging.env_log_level import resolve_env_log_level_override
from openclaw.logging.levels import LogLevel, normalize_log_level
from openclaw.logging.redact import redact_sensitive_text
from openclaw.logging.state import logging_state
from openclaw.logging.timestamps import format_local_iso_with_offset, format_timestamp
from openclaw.logging.types import ConsoleStyle

ConsoleSettings = dict[str, Any]

_load_config_fallback: Any = None


def set_console_config_loader_for_tests(loader: Any = None) -> None:
    global _load_config_fallback
    _load_config_fallback = loader


def _is_verbose() -> bool:
    return False


def _normalize_console_level(level: str | None = None) -> LogLevel:
    if _is_verbose():
        return "debug"
    if not level and os.environ.get("VITEST") == "true" and os.environ.get("OPENCLAW_TEST_CONSOLE") != "1":
        return "silent"
    return normalize_log_level(level, "info")


def _normalize_console_style(style: str | None = None) -> ConsoleStyle:
    if style in ("compact", "json", "pretty"):
        return style
    if not sys.stdout.isatty():
        return "compact"
    return "pretty"


def _resolve_console_settings() -> ConsoleSettings:
    env_level = resolve_env_log_level_override()
    if (
        os.environ.get("VITEST") == "true"
        and os.environ.get("OPENCLAW_TEST_CONSOLE") != "1"
        and not _is_verbose()
        and not env_level
        and not logging_state.override_settings
    ):
        return {"level": "silent", "style": _normalize_console_style()}
    cfg = logging_state.override_settings or read_logging_config()
    if not cfg and not should_skip_mutating_logging_config_read():
        if not logging_state.resolving_console_settings:
            logging_state.resolving_console_settings = True
            try:
                cfg = _load_config_fallback() if _load_config_fallback else None
            finally:
                logging_state.resolving_console_settings = False
    level = env_level or _normalize_console_level(cfg.get("consoleLevel") if cfg else None)
    style = _normalize_console_style(cfg.get("consoleStyle") if cfg else None)
    return {"level": level, "style": style}


def _console_settings_changed(a: ConsoleSettings | None, b: ConsoleSettings) -> bool:
    if not a:
        return True
    return a.get("level") != b.get("level") or a.get("style") != b.get("style")


def get_console_settings() -> ConsoleSettings:
    settings = _resolve_console_settings()
    cached = logging_state.cached_console_settings
    if not cached or _console_settings_changed(cached, settings):
        logging_state.cached_console_settings = settings
    return logging_state.cached_console_settings


def get_resolved_console_settings() -> ConsoleSettings:
    return get_console_settings()


def route_logs_to_stderr() -> None:
    logging_state.force_console_to_stderr = True


def set_console_subsystem_filter(filters: list[str] | None = None) -> None:
    if not filters or len(filters) == 0:
        logging_state.console_subsystem_filter = None
        return
    normalized = [f.strip() for f in filters if f.strip()]
    logging_state.console_subsystem_filter = normalized if normalized else None


def set_console_timestamp_prefix(enabled: bool) -> None:
    logging_state.console_timestamp_prefix = enabled


def _normalize_console_subsystem(subsystem: str | None = None) -> str | None:
    if not isinstance(subsystem, str):
        return None
    normalized = subsystem.strip()
    return normalized if normalized else None


def should_log_subsystem_to_console(subsystem: str | None = None) -> bool:
    filter_list = logging_state.console_subsystem_filter
    if not filter_list or len(filter_list) == 0:
        return True
    normalized_subsystem = _normalize_console_subsystem(subsystem)
    if not normalized_subsystem:
        return False
    return any(
        normalized_subsystem == prefix or normalized_subsystem.startswith(f"{prefix}/")
        for prefix in filter_list
    )


_SUPPRESSED_CONSOLE_PREFIXES = (
    "Closing session:",
    "Opening session:",
    "Removing old closed session:",
    "Session already closed",
    "Session already open",
)


def _should_suppress_console_message(message: str) -> bool:
    return any(message.startswith(prefix) for prefix in _SUPPRESSED_CONSOLE_PREFIXES)


def format_console_timestamp(style: ConsoleStyle) -> str:
    now = datetime.now()
    if style == "pretty":
        return re.sub(r"[+-]\d{2}:\d{2}$", "", format_timestamp(now, {"style": "short"}))
    return format_local_iso_with_offset(now)


def enable_console_capture() -> None:
    if logging_state.console_patched:
        return
    logging_state.console_patched = True


__all__ = [
    "set_console_config_loader_for_tests",
    "get_console_settings",
    "get_resolved_console_settings",
    "route_logs_to_stderr",
    "set_console_subsystem_filter",
    "set_console_timestamp_prefix",
    "should_log_subsystem_to_console",
    "format_console_timestamp",
    "enable_console_capture",
]
