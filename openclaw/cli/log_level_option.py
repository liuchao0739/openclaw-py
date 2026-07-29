from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_lowercase_string

VALID_LOG_LEVELS = {"trace", "debug", "info", "warn", "warning", "error", "fatal", "silent", "off"}


def normalize_log_level(value: Any) -> str | None:
    normalized = normalize_optional_lowercase_string(value)
    if not normalized:
        return None
    if normalized in VALID_LOG_LEVELS:
        if normalized == "warning":
            return "warn"
        return normalized
    return None


def parse_log_level_option(raw: Any) -> str | None:
    return normalize_log_level(raw)


def has_log_level_flag(argv: list[str]) -> bool:
    args = argv[2:]
    for arg in args:
        if arg == "--":
            break
        if arg == "--log-level" or arg.startswith("--log-level="):
            return True
    return False


def get_log_level_flag_value(argv: list[str]) -> str | None:
    args = argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        if arg == "--log-level":
            next_val = args[i + 1] if i + 1 < len(args) else None
            if next_val and not next_val.startswith("-"):
                return normalize_log_level(next_val)
            return None
        if arg.startswith("--log-level="):
            return normalize_log_level(arg[len("--log-level=") :])
        i += 1
    return None
